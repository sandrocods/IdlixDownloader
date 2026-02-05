"""
Helper Class for IDLIX Downloader & IDLIX Player CLI

Update  :   28-11-2025
Author  :   sandroputraa
"""

import os
import random
import re
import json
import m3u8
import shutil
import zipfile
import requests
import subprocess
import m3u8_To_MP4
from loguru import logger
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse
from vtt_to_srt.vtt_to_srt import ConvertFile
import cloudscraper
from src.CryptoJsAesHelper import CryptoJsAes, dec


class IdlixHelper:
    BASE_WEB_URL = "https://tv12.idlixku.com/"
    BASE_STATIC_HEADERS = {
        "Referer": BASE_WEB_URL,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    }

    def __init__(self):
        self.poster = None
        self.m3u8_url = None
        self.video_id = None
        self.embed_url = None
        self.video_name = None
        self.is_subtitle = None
        self.variant_playlist = None
        self.subtitles = []  # Multi-subtitle support
        self.selected_subtitle = None
        self.skip_subtitle = False  # Flag when user explicitly chooses "No Subtitle"
        self.content_type = None  # 'movie' or 'episode'
        self.series_info = None  # Series metadata
        self.episode_meta = None  # Episode metadata for organized downloads
        self.progress_callback = None  # Callback for GUI progress updates
        self.cancel_flag = False  # Flag to cancel download
        self.request = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.request.headers.update(self.BASE_STATIC_HEADERS)

        # Proxy Example
        # self.request.proxies = {
        #    'https': ''
        # }

        # FFMPEG
        # FFMPEG
        if os.name == 'nt':
            if not shutil.which('ffplay'):
                # Check Local
                local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')
                bin_path = None
                
                if os.path.exists(local_ffmpeg):
                    for root, dirs, files in os.walk(local_ffmpeg):
                        if 'ffplay.exe' in files:
                            bin_path = root
                            break
                            
                if bin_path:
                    logger.info(f'FFMPEG Found Locally: {bin_path}')
                    os.environ["PATH"] += os.pathsep + bin_path
                else:
                    if not os.path.exists('ffmpeg-release-essentials.zip'):
                        self.download_ffmpeg()
                    
                    logger.warning('Extracting ffmpeg...')
                    try:
                        with zipfile.ZipFile('ffmpeg-release-essentials.zip', 'r') as zip_ref:
                            zip_ref.extractall(local_ffmpeg)
                        
                        # Find bin again
                        for root, dirs, files in os.walk(local_ffmpeg):
                            if 'ffplay.exe' in files:
                                bin_path = root
                                break
                                
                        if bin_path:
                            logger.success(f'FFMPEG Extracted to: {bin_path}')
                            os.environ["PATH"] += os.pathsep + bin_path
                        else:
                            logger.error('Failed to find ffplay.exe after extraction')
                            
                    except Exception as e:
                        logger.error(f'Error extracting ffmpeg: {e}')
        else:
            if not shutil.which('ffmpeg'):
                logger.error('FFMPEG not found, please install ffmpeg first before running this script')
                exit()

    @staticmethod
    def download_ffmpeg():
        try:
            logger.info('Downloading ffmpeg')
            content = requests.get(
                url='https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip',
                stream=True
            )
            with open("ffmpeg-release-essentials.zip", mode="wb") as file:
                for chunk in content.iter_content(chunk_size=1024):
                    print(
                        '\rDownloading: {} MB of {} MB'.format(
                            round(os.path.getsize('ffmpeg-release-essentials.zip') / 1024 / 1024, 2),
                            round(int(content.headers.get('Content-Length', 0)) / 1024 / 1024, 2)
                        ),
                        end=''
                    )
                    file.write(chunk)
            print()
            logger.success('Downloaded ffmpeg')
        except Exception as e:
            print(f'Error: {e}')

    def get_home(self):
        try:
            request = self.request.get(
                url=self.BASE_WEB_URL,
                timeout=10
            )
            if request.status_code == 200:
                bs = BeautifulSoup(request.text, 'html.parser')
                tmp_featured = []
                for featured in bs.find('div', {'class': 'items featured'}).find_all('article'):

                    if featured.find('a').get('href').split('/')[3] == 'tvseries':
                        continue

                    tmp_featured.append({
                        "url": featured.find('a').get('href'),
                        "title": featured.find('h3').text,
                        "year": featured.find('span').text,
                        "type": featured.find('a').get('href').split('/')[3],
                        "poster": featured.find('img').get('src'),
                    })
                return {
                    'status': True,
                    'featured_movie': tmp_featured
                }
            else:
                return {
                    'status': False,
                    'message': 'Failed to get home page'
                }
        except Exception as error_get_home:
            return {
                'status': False,
                'message': str(error_get_home)
            }

    def get_featured_series(self):
        """Get featured TV series from homepage"""
        try:
            request = self.request.get(
                url=self.BASE_WEB_URL,
                timeout=10
            )
            if request.status_code == 200:
                bs = BeautifulSoup(request.text, 'html.parser')
                tmp_featured = []
                for featured in bs.find('div', {'class': 'items featured'}).find_all('article'):
                    href = featured.find('a').get('href')
                    if '/tvseries/' in href:
                        tmp_featured.append({
                            "url": href,
                            "title": featured.find('h3').text,
                            "year": featured.find('span').text,
                            "type": "tvseries",
                            "poster": featured.find('img').get('src'),
                        })
                return {
                    'status': True,
                    'featured_series': tmp_featured
                }
            else:
                return {
                    'status': False,
                    'message': 'Failed to get featured series'
                }
        except Exception as e:
            return {
                'status': False,
                'message': str(e)
            }

    def get_series_info(self, url):
        """Get series info including seasons and episodes"""
        try:
            request = self.request.get(url=url, timeout=10)
            if request.status_code != 200:
                return {'status': False, 'message': 'Failed to fetch series page'}
            
            bs = BeautifulSoup(request.text, 'html.parser')
            
            # Get series title
            series_title = bs.find('h1').text.strip() if bs.find('h1') else "Unknown Series"
            poster = bs.find('img', {'itemprop': 'image'})
            poster_url = poster.get('src') if poster else None
            
            # Get year from page (try multiple selectors)
            year_span = bs.find('span', {'class': 'date'}) or bs.find('span', text=re.compile(r'\d{4}'))
            series_year = year_span.text.strip() if year_span else "2025"
            # Extract just the year if it's embedded in other text
            year_match = re.search(r'(\d{4})', series_year)
            series_year = year_match.group(1) if year_match else "2025"
            
            # Get seasons
            seasons = []
            season_tabs = bs.find('div', {'id': 'seasons'})
            if season_tabs:
                for season_div in season_tabs.find_all('div', {'class': 'se-c'}):
                    season_title = season_div.find('span', {'class': 'se-t'})
                    season_num = season_title.text.strip() if season_title else "1"
                    
                    episodes = []
                    episode_list = season_div.find('ul', {'class': 'episodios'})
                    if episode_list:
                        for ep in episode_list.find_all('li'):
                            ep_link = ep.find('a')
                            ep_num_div = ep.find('div', {'class': 'numerando'})
                            ep_title_div = ep.find('div', {'class': 'episodiotitle'})
                            
                            if ep_link:
                                ep_num = ep_num_div.text.strip() if ep_num_div else ""
                                ep_title = ep_title_div.find('a').text.strip() if ep_title_div and ep_title_div.find('a') else ""
                                # Parse season and episode numbers from 'number' field (format: "S - E")
                                season_ep = ep_num.split(' - ') if ' - ' in ep_num else [season_num, '1']
                                ep_number = season_ep[1] if len(season_ep) > 1 else '1'
                                episodes.append({
                                    'url': ep_link.get('href'),
                                    'number': ep_num,
                                    'title': ep_title,
                                    'full_title': f"{ep_num} - {ep_title}" if ep_title else ep_num,
                                    'season_num': season_num,
                                    'episode_num': ep_number
                                })
                    
                    seasons.append({
                        'season': season_num,
                        'episodes': episodes
                    })
            
            self.series_info = {
                'title': series_title,
                'year': series_year,
                'poster': poster_url,
                'seasons': seasons,
                'url': url
            }
            
            return {
                'status': True,
                'series_info': self.series_info
            }
        except Exception as e:
            return {
                'status': False,
                'message': str(e)
            }

    def set_episode_meta(self, series_title, series_year, season_num, episode_num):
        """Set episode metadata for organized folder structure"""
        # Remove year from title if already present (e.g., "Zootopia+ (2022)" -> "Zootopia+")
        clean_title = re.sub(r'\s*\(\d{4}\)\s*$', '', series_title).strip()
        clean_title = re.sub(r'[\\/*?:"<>|]', '', clean_title)  # Clean invalid chars
        
        self.episode_meta = {
            'series_title': clean_title,
            'series_year': series_year,
            'season_num': int(season_num) if str(season_num).isdigit() else 1,
            'episode_num': int(episode_num) if str(episode_num).isdigit() else 1
        }

    def get_episode_data(self, url):
        """Get episode data - similar to get_video_data but for episodes"""
        if not url:
            return {'status': False, 'message': 'URL is required'}
        
        try:
            self.content_type = 'episode'
            request = self.request.get(url=url, timeout=10)
            
            if request.status_code == 200:
                bs = BeautifulSoup(request.text, 'html.parser')
                
                # Get video ID
                meta_counter = bs.find('meta', {'id': 'dooplay-ajax-counter'})
                if meta_counter:
                    self.video_id = meta_counter.get('data-postid')
                
                # Get episode title
                title_tag = bs.find('h1') or bs.find('meta', {'itemprop': 'name'})
                if title_tag:
                    self.video_name = title_tag.text.strip() if hasattr(title_tag, 'text') else title_tag.get('content', 'Unknown Episode')
                else:
                    self.video_name = "Unknown Episode"
                
                # Get poster
                poster_img = bs.find('img', {'itemprop': 'image'})
                self.poster = poster_img.get('src') if poster_img else None
                
                # Extract series info from episode page (for organized folder)
                series_title = None
                series_year = None
                
                # Try to get series title from breadcrumb or link
                breadcrumb = bs.find('div', {'class': 'sgeneros'})
                if breadcrumb:
                    series_link = breadcrumb.find('a', href=re.compile(r'/tvseries/'))
                    if series_link:
                        series_title = series_link.text.strip()
                
                # If not found, try alternative: parse from page title
                if not series_title:
                    # Episode title format: "Series Name: Season X Episode Y" or "Series Name (Year): Season X Episode Y"
                    match = re.match(r'^(.+?)(?:\s*\(\d{4}\))?\s*:\s*\d+x\d+', self.video_name)
                    if match:
                        series_title = match.group(1).strip()
                
                # Get year from page (try multiple methods)
                # Method 1: From date meta tag
                date_meta = bs.find('meta', {'property': 'og:updated_time'}) or bs.find('span', {'class': 'date'})
                if date_meta:
                    year_text = date_meta.get('content') if date_meta.name == 'meta' else date_meta.text
                    year_match = re.search(r'(\d{4})', year_text)
                    if year_match:
                        series_year = year_match.group(1)
                
                # Method 2: From episode title (if format has year)
                if not series_year:
                    year_match = re.search(r'\((\d{4})\)', self.video_name)
                    if year_match:
                        series_year = year_match.group(1)
                
                # Store series metadata for potential use
                self.episode_series_info = {
                    'series_title': series_title,
                    'series_year': series_year or '2025'  # Fallback to current year
                }
                
                return {
                    'status': True,
                    'video_id': self.video_id,
                    'video_name': self.video_name,
                    'poster': self.poster,
                    'content_type': 'episode',
                    'series_info': self.episode_series_info
                }
            else:
                return {'status': False, 'message': 'Failed to get episode data'}
        except Exception as e:
            return {'status': False, 'message': str(e)}

    def get_embed_url_episode(self):
        """Get embed URL for episode (type=tv instead of movie)"""
        if not self.video_id:
            return {'status': False, 'message': 'Video ID is required'}
        
        try:
            request = self.request.post(
                url=self.BASE_WEB_URL + "wp-admin/admin-ajax.php",
                data={
                    "action": "doo_player_ajax",
                    "post": self.video_id,
                    "nume": "1",
                    "type": "tv",  # Different from movie
                }
            )
            if request.status_code == 200 and request.json().get('embed_url'):
                self.embed_url = CryptoJsAes.decrypt(
                    request.json().get('embed_url'),
                    dec(
                        request.json().get('key'),
                        json.loads(request.json().get('embed_url')).get('m')
                    )
                )
                return {
                    'status': True,
                    'embed_url': self.embed_url
                }
            else:
                return {'status': False, 'message': 'Failed to get embed URL'}
        except Exception as e:
            return {'status': False, 'message': str(e)}

    def get_video_data(self, url):
        if not url:
            return {
                'status': False,
                'message': 'URL is required'
            }
        if url.startswith(self.BASE_WEB_URL):
            request = self.request.get(
                url=url,
            )
            if request.status_code == 200:
                bs = BeautifulSoup(request.text, 'html.parser')
                self.video_id = bs.find('meta', {'id': 'dooplay-ajax-counter'}).get('data-postid')
                self.video_name = unquote(bs.find('meta', {'itemprop': 'name'}).get('content'))
                self.poster = bs.find('img', {'itemprop': 'image'}).get('src')
                return {
                    'status': True,
                    'video_id': self.video_id,
                    'video_name': self.video_name,
                    'poster': self.poster
                }
            else:
                return {
                    'status': False,
                    'message': 'Failed to get video data'
                }
        else:
            return {
                'status': False,
                'message': 'Invalid URL'
            }

    def get_embed_url(self):
        if not self.video_id:
            return {
                'status': False,
                'message': 'Video ID is required'
            }
        try:
            request = self.request.post(
                url=self.BASE_WEB_URL + "wp-admin/admin-ajax.php",
                data={
                    "action": "doo_player_ajax",
                    "post": self.video_id,
                    "nume": "1",
                    "type": "movie",
                }
            )
            if request.status_code == 200 and request.json().get('embed_url'):
                self.embed_url = CryptoJsAes.decrypt(
                    request.json().get('embed_url'),
                    dec(
                        request.json().get('key'),
                        json.loads(request.json().get('embed_url')).get('m')
                    )
                )
                return {
                    'status': True,
                    'embed_url': self.embed_url
                }
            else:
                return {
                    'status': False,
                    'message': 'Failed to get embed URL'
                }
        except Exception as error_get_embed_url:
            return {
                'status': False,
                'message': str(error_get_embed_url)
            }

    def get_m3u8_url(self):
        if not self.embed_url:
            return {
                'status': False,
                'message': 'Embed URL is required'
            }

        if '/video/' in urlparse(self.embed_url).path:
            self.embed_url = urlparse(self.embed_url).path.split('/')[2]
        elif urlparse(self.embed_url).query.split('=')[1]:
            self.embed_url = urlparse(self.embed_url).query.split('=')[1]

        try:
            request = self.request.post(
                url='https://jeniusplay.com/player/index.php',
                params={
                    "data": self.embed_url,
                    "do": "getVideo"
                },
                headers={
                    "Host": "jeniusplay.com",
                    "X-Requested-With": "XMLHttpRequest",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                data={
                    "hash": self.embed_url,
                    "r": self.BASE_WEB_URL,
                },
            )

            if request.status_code == 200 and request.json().get('videoSource'):
                self.m3u8_url = request.json().get('videoSource').rsplit(".", 1)[0] + ".m3u8"
                self.variant_playlist = m3u8.load(self.m3u8_url)
                tmp_variant_playlist = []
                id = 0
                for playlist in self.variant_playlist.playlists:
                    tmp_variant_playlist.append({
                        'bandwidth': playlist.stream_info.bandwidth,
                        'resolution': str(playlist.stream_info.resolution[0]) + 'x' + str(playlist.stream_info.resolution[1]),
                        'uri': playlist.uri,
                        'id': str(id)
                    })
                    id += 1
                is_variant_playlist = True if len(tmp_variant_playlist) > 1 else False
                return {
                    'status': True,
                    'm3u8_url': self.m3u8_url,
                    'variant_playlist': tmp_variant_playlist,
                    'is_variant_playlist': is_variant_playlist
                }
            else:
                return {
                    'status': False,
                    'message': 'Failed to get m3u8 URL'
                }
        except Exception as error_get_m3u8_url:
            return {
                'status': False,
                'message': str(error_get_m3u8_url)
            }

    def download_m3u8(self):
        try:
            # Check cancel flag
            if self.cancel_flag:
                return {
                    'status': False,
                    'message': 'Download cancelled by user'
                }
            
            if not self.m3u8_url:
                return {
                    'status': False,
                    'message': 'M3U8 URL is required'
                }
            
            # Determine output directory and filename
            if self.episode_meta:
                # Organized folder structure for series
                series_folder = f"{self.episode_meta['series_title']} ({self.episode_meta['series_year']})"
                season_folder = f"Season {self.episode_meta['season_num']:02d}"
                output_dir = os.path.join(os.getcwd(), series_folder, season_folder)
                # Filename without year: "Series Name - s01e01"
                output_name = f"{self.episode_meta['series_title']} - s{self.episode_meta['season_num']:02d}e{self.episode_meta['episode_num']:02d}"
                logger.info(f"📁 Output: {series_folder}/{season_folder}/{output_name}.mp4")
            else:
                # Default: current directory for movies
                output_dir = os.getcwd()
                output_name = self.get_safe_title()
            
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Create tmp directory if not exists
            tmp_dir = os.path.join(os.getcwd(), 'tmp')
            os.makedirs(tmp_dir, exist_ok=True)

            # --- Automatic Subtitle Download (only if not already downloaded) ---
            subtitle_path = None
            if not self.is_subtitle and not self.skip_subtitle:
                logger.info("Checking for subtitles...")
                sub_res = self.get_subtitle(download=True, output_dir=output_dir, output_name=output_name)
                if sub_res.get('status'):
                    subtitle_path = sub_res.get('subtitle')
                    logger.success(f"Subtitle downloaded: {subtitle_path}")
                else:
                    logger.warning(f"No subtitle found or failed to download: {sub_res.get('message')}")
            elif self.skip_subtitle:
                logger.info("Subtitle skipped (user choice)")
            else:
                # Subtitle already downloaded - find the file
                safe_title = self.get_safe_title()
                if self.selected_subtitle:
                    # Check in current directory first (where download_selected_subtitle saves it)
                    old_srt = f"{safe_title}_{self.selected_subtitle['label']}.srt"
                    if os.path.exists(old_srt):
                        if self.episode_meta:
                            # Move to output folder for series
                            new_srt = os.path.join(output_dir, f"{output_name}.srt")
                            shutil.move(old_srt, new_srt)
                            subtitle_path = new_srt
                            logger.info(f"Subtitle moved to: {new_srt}")
                        else:
                            subtitle_path = old_srt
                    else:
                        # Check in output_dir
                        new_srt = os.path.join(output_dir, f"{output_name}.srt")
                        if os.path.exists(new_srt):
                            subtitle_path = new_srt
                else:
                    # Default subtitle (no label)
                    default_srt = f"{safe_title}.srt"
                    if os.path.exists(default_srt):
                        subtitle_path = default_srt
                
                logger.info(f"Subtitle already downloaded: {subtitle_path}")
            # ------------------------------------

            # Check subtitle mode
            subtitle_mode = getattr(self, 'subtitle_mode', 'separate')
            logger.info(f"Subtitle mode: {subtitle_mode}")
            
            if subtitle_mode in ['hardcode', 'softcode'] and subtitle_path and os.path.exists(subtitle_path):
                # Use FFmpeg for subtitle embedding
                logger.info(f"Using FFmpeg for {subtitle_mode} subtitle...")
                logger.info(f"Subtitle file: {subtitle_path}")
                result = self._download_with_ffmpeg(output_dir, output_name, subtitle_path, subtitle_mode)
                if result.get('status'):
                    # Cleanup tmp and srt file (both hardcode and softcode embed subtitle)
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    if os.path.exists(subtitle_path):
                        os.remove(subtitle_path)
                        logger.info("Subtitle file cleaned up (embedded in video)")
                    return result
                else:
                    logger.warning(f"FFmpeg failed: {result.get('message')}. Falling back to standard download...")
            
            # Standard download with m3u8_To_MP4
            logger.info(f"Starting download for {self.video_name}...")
            
            # Redirect stdout/stderr to capture m3u8_To_MP4 logs with real-time progress
            import sys
            from io import StringIO
            
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            
            # Custom exception for cancellation
            class DownloadCancelled(Exception):
                pass
            
            # Reference to self for cancel flag check
            helper_self = self
            
            # Custom stream that parses progress in real-time
            class ProgressCapture:
                def __init__(self, original_stream, progress_callback=None):
                    self.original = original_stream
                    self.progress_callback = progress_callback
                    self.buffer = ""
                
                def write(self, data):
                    # Check cancel flag - raise exception to interrupt download
                    if helper_self.cancel_flag:
                        raise DownloadCancelled("Download cancelled by user")
                    
                    # Don't print to terminal for segment progress (too noisy)
                    if "segment set:" not in data:
                        self.original.write(data)
                        self.original.flush()
                    
                    # Buffer data for line-by-line parsing
                    self.buffer += data
                    
                    # Process complete lines (split on \r for real-time progress updates)
                    while '\n' in self.buffer or '\r' in self.buffer:
                        # Split on either \n or \r
                        if '\r' in self.buffer and ('\n' not in self.buffer or self.buffer.index('\r') < self.buffer.index('\n')):
                            line, self.buffer = self.buffer.split('\r', 1)
                        else:
                            line, self.buffer = self.buffer.split('\n', 1)
                        
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Parse progress from m3u8_To_MP4 format: "segment set: |###---| X.X% download"
                        if self.progress_callback and "segment set:" in line:
                            try:
                                match = re.search(r'([\d.]+)%', line)
                                if match:
                                    percent = float(match.group(1))
                                    self.progress_callback(percent, f"{percent:.1f}%")
                            except:
                                pass
                        # Log non-progress lines (skip segment set lines)
                        elif "segment set:" not in line:
                            if line:
                                logger.info(line)
                
                def flush(self):
                    self.original.flush()
            
            sys.stdout = ProgressCapture(old_stdout, self.progress_callback)
            sys.stderr = ProgressCapture(old_stderr, self.progress_callback)
            
            download_cancelled = False
            try:
                # Check cancel before starting download
                if self.cancel_flag:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    return {'status': False, 'message': 'Download cancelled by user'}
                
                m3u8_To_MP4.multithread_download(
                    m3u8_uri=self.m3u8_url,
                    max_num_workers=10,
                    mp4_file_name=output_name,
                    mp4_file_dir=output_dir + '/',
                    tmpdir=tmp_dir + '/'
                )
            except DownloadCancelled:
                download_cancelled = True
                logger.warning("Download cancelled by user")
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            # Cleanup tmp folder
            shutil.rmtree(tmp_dir, ignore_errors=True)
            
            # Check if cancelled
            if download_cancelled or self.cancel_flag:
                # Clean up partial file
                partial_file = os.path.join(output_dir, output_name + '.mp4')
                if os.path.exists(partial_file):
                    try:
                        os.remove(partial_file)
                        logger.info("Partial download file removed")
                    except:
                        pass
                return {'status': False, 'message': 'Download cancelled by user'}
            
            final_path = os.path.join(output_dir, output_name + '.mp4')
            return {
                'status': True,
                'message': 'Download success',
                'path': final_path
            }
        except Exception as error_download_m3u8:
            # Check if it was a cancellation
            if self.cancel_flag or 'cancelled' in str(error_download_m3u8).lower():
                return {'status': False, 'message': 'Download cancelled by user'}
            return {
                'status': False,
                'message': str(error_download_m3u8)
            }

    def _download_with_ffmpeg(self, output_dir, output_name, subtitle_path, mode='softcode'):
        """Download video with FFmpeg and embed/hardcode subtitle"""
        try:
            user_agent = self.request.headers.get("User-Agent", "Mozilla/5.0")
            referer = self.BASE_STATIC_HEADERS.get("Referer", "")
            
            # Build headers string for FFmpeg
            headers = f"Referer: {referer}\r\nUser-Agent: {user_agent}\r\n"
            
            # Add cookies if any
            cookies = self.request.cookies.get_dict()
            if cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                headers += f"Cookie: {cookie_str}\r\n"
            
            # Use absolute path for subtitle
            subtitle_abs = os.path.abspath(subtitle_path)
            
            # Determine subtitle language from selected_subtitle or filename
            sub_lang = "ind"  # Default Indonesian
            sub_title = "Indonesian"
            if self.selected_subtitle:
                label = self.selected_subtitle.get('label', 'Indonesian')
                sub_title = label
                # Map common languages to ISO 639-2 codes
                lang_map = {
                    'indonesian': 'ind', 'indonesia': 'ind', 'bahasa': 'ind',
                    'english': 'eng', 'inggris': 'eng',
                    'malay': 'msa', 'melayu': 'msa',
                    'chinese': 'chi', 'mandarin': 'chi',
                    'japanese': 'jpn', 'jepang': 'jpn',
                    'korean': 'kor', 'korea': 'kor',
                    'thai': 'tha',
                    'vietnamese': 'vie',
                    'arabic': 'ara',
                    'spanish': 'spa',
                    'french': 'fra',
                    'german': 'deu',
                    'portuguese': 'por',
                    'russian': 'rus',
                    'hindi': 'hin',
                }
                for key, code in lang_map.items():
                    if key in label.lower():
                        sub_lang = code
                        break
            
            if mode == 'hardcode':
                # Hardcode: burn subtitle into video (re-encode, slower)
                output_file = os.path.join(output_dir, output_name + '.mp4')
                
                # Escape subtitle path for FFmpeg filter (Windows path fix)
                sub_escaped = subtitle_abs.replace('\\', '/').replace(':', r'\:').replace("'", r"\'")
                
                command = [
                    'ffmpeg', '-y',
                    '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
                    '-headers', headers,
                    '-allowed_extensions', 'ALL',
                    '-allowed_segment_extensions', 'ALL',
                    '-extension_picky', '0',
                    '-f', 'hls',
                    '-i', self.m3u8_url,
                    '-vf', f"subtitles='{sub_escaped}'",
                    '-c:v', 'libx264',
                    '-preset', 'fast',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    output_file
                ]
            else:
                # Softcode: embed as subtitle track (fast, no re-encode)
                output_file = os.path.join(output_dir, output_name + '.mkv')
                
                command = [
                    'ffmpeg', '-y',
                    '-protocol_whitelist', 'file,http,https,tcp,tls,crypto',
                    '-headers', headers,
                    '-allowed_extensions', 'ALL',
                    '-allowed_segment_extensions', 'ALL',
                    '-extension_picky', '0',
                    '-f', 'hls',
                    '-i', self.m3u8_url,
                    '-i', subtitle_abs,
                    '-map', '0:v',
                    '-map', '0:a',
                    '-map', '1:0',
                    '-c:v', 'copy',
                    '-c:a', 'copy',
                    '-c:s', 'srt',
                    '-metadata:s:s:0', f'language={sub_lang}',
                    '-metadata:s:s:0', f'title={sub_title}',
                    '-disposition:s:0', 'default',  # Set as default subtitle
                    output_file
                ]

            logger.info(f"FFmpeg {'hardcoding' if mode == 'hardcode' else 'embedding'} subtitle...")
            logger.info(f"This may take a while for long videos...")
            
            # Run FFmpeg with progress tracking
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )
            
            # Parse FFmpeg output for progress with custom progress bar
            try:
                from tqdm import tqdm
                use_tqdm = True
            except ImportError:
                use_tqdm = False
            
            duration = None
            pbar = None
            
            for line in iter(process.stderr.readline, ''):
                # Check cancel flag periodically
                if self.cancel_flag:
                    process.terminate()
                    logger.warning("FFmpeg download cancelled")
                    break
                
                # Extract total duration
                if 'Duration:' in line and not duration:
                    import re
                    match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if match:
                        h, m, s, cs = map(int, match.groups())
                        duration = h * 3600 + m * 60 + s + cs / 100
                        
                        # Initialize progress bar with custom format
                        if use_tqdm and duration > 0:
                            pbar = tqdm(
                                total=100,
                                desc="FFmpeg Progress",
                                unit="%",
                                bar_format="{desc}: |{bar}| {n:.1f}% [{elapsed}<{remaining}]",
                                ncols=80,
                                ascii=" #"
                            )
                
                # Extract current time and calculate percentage
                if 'time=' in line and duration:
                    match = re.search(r'time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})', line)
                    if match:
                        h, m, s, cs = map(int, match.groups())
                        current_time = h * 3600 + m * 60 + s + cs / 100
                        percentage = min(100, (current_time / duration) * 100)
                        
                        # Callback for GUI
                        if self.progress_callback:
                            self.progress_callback(percentage, "FFmpeg encoding")
                        
                        if pbar:
                            # Update progress bar
                            pbar.n = percentage
                            pbar.refresh()
                        else:
                            # Fallback to simple progress bar
                            bar_length = 50
                            filled = int(bar_length * percentage / 100)
                            bar = '#' * filled + '-' * (bar_length - filled)
                            print(f'\rFFmpeg Progress: |{bar}| {percentage:.1f}%', end='', flush=True)
            
            if pbar:
                pbar.close()
            else:
                print()  # New line after progress
            
            process.wait()
            
            # Check if cancelled
            if self.cancel_flag:
                # Clean up partial file
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                        logger.info("Partial download file removed")
                    except:
                        pass
                return {
                    'status': False,
                    'message': 'Download cancelled by user'
                }
            
            if process.returncode == 0:
                logger.success(f"FFmpeg download complete: {output_file}")
                return {
                    'status': True,
                    'message': 'Download success with FFmpeg',
                    'path': output_file
                }
            else:
                # Read remaining stderr for error
                stderr = process.stderr.read()
                error_lines = stderr.strip().split('\n')[-5:]  # Last 5 lines
                error_msg = '\n'.join(error_lines)
                logger.error(f"FFmpeg error:\n{error_msg}")
                return {
                    'status': False,
                    'message': f"FFmpeg error: {error_msg[:300]}"
                }
                
        except Exception as e:
            return {
                'status': False,
                'message': str(e)
            }

    def set_subtitle_mode(self, mode):
        """Set subtitle mode: 'separate', 'softcode', or 'hardcode'"""
        self.subtitle_mode = mode

    def set_skip_subtitle(self, skip=True):
        """Set flag to skip subtitle download"""
        self.skip_subtitle = skip

    def get_safe_title(self):
        return re.sub(r'[\\/*?:"<>|&]', "", self.video_name)

    def get_available_subtitles(self):
        """Get list of available subtitles without downloading"""
        try:
            if not self.embed_url:
                return {'status': False, 'message': 'Embed URL is required'}

            request = self.request.post(
                url='https://jeniusplay.com/player/index.php',
                params={"data": self.embed_url, "do": "getVideo"},
                headers={
                    "Host": "jeniusplay.com",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                data={"hash": self.embed_url, "r": self.BASE_WEB_URL},
            )
            
            # Parse multiple subtitles: format can be "[Label]URL,[Label2]URL2" or just "URL"
            regex_subtitle = re.search(r'var playerjsSubtitle = "(.*)";', request.text)
            
            if not regex_subtitle:
                self.subtitles = []
                return {'status': False, 'message': 'No subtitles found'}
            
            subtitle_str = regex_subtitle.group(1)
            self.subtitles = []
            
            # Parse subtitle format: can be "[Indonesian]url,[English]url" or single URL
            if ',' in subtitle_str and '[' in subtitle_str:
                # Multiple subtitles with labels
                parts = subtitle_str.split(',')
                for i, part in enumerate(parts):
                    match = re.match(r'\[([^\]]+)\](.*)', part.strip())
                    if match:
                        label = match.group(1)
                        url = match.group(2)
                        if 'https://' in url:
                            url = "https://" + url.split("https://")[1]
                        self.subtitles.append({
                            'id': str(i),
                            'label': label,
                            'url': url
                        })
            elif '[' in subtitle_str:
                # Single subtitle with label
                match = re.match(r'\[([^\]]+)\](.*)', subtitle_str.strip())
                if match:
                    label = match.group(1)
                    url = match.group(2)
                    if 'https://' in url:
                        url = "https://" + url.split("https://")[1]
                    self.subtitles.append({
                        'id': '0',
                        'label': label,
                        'url': url
                    })
            else:
                # Single URL without label
                url = subtitle_str
                if 'https://' in url:
                    url = "https://" + url.split("https://")[1]
                self.subtitles.append({
                    'id': '0',
                    'label': 'Default',
                    'url': url
                })
            
            if self.subtitles:
                return {
                    'status': True,
                    'subtitles': self.subtitles,
                    'count': len(self.subtitles)
                }
            else:
                return {'status': False, 'message': 'No subtitles found'}
                
        except Exception as e:
            return {'status': False, 'message': str(e)}

    def download_selected_subtitle(self, subtitle_id=None):
        """Download a specific subtitle by ID, or first available if not specified"""
        try:
            if not self.subtitles:
                # Try to get subtitles first
                result = self.get_available_subtitles()
                if not result.get('status'):
                    return result
            
            if not self.subtitles:
                return {'status': False, 'message': 'No subtitles available'}
            
            # Select subtitle
            selected = None
            if subtitle_id is not None:
                for sub in self.subtitles:
                    if sub['id'] == str(subtitle_id):
                        selected = sub
                        break
            
            if not selected:
                selected = self.subtitles[0]  # Default to first
            
            self.selected_subtitle = selected
            safe_title = self.get_safe_title()
            
            # Download VTT
            subtitle_request = requests.get(url=selected['url'])
            vtt_file = f"{safe_title}_{selected['label']}.vtt"
            srt_file = f"{safe_title}_{selected['label']}.srt"
            
            with open(vtt_file, 'wb') as f:
                f.write(subtitle_request.content)
            
            self.convert_vtt_to_srt(vtt_file)
            
            # Delete VTT file after conversion (keep only SRT)
            try:
                os.remove(vtt_file)
            except:
                pass
            
            self.is_subtitle = True
            
            return {
                'status': True,
                'subtitle': srt_file,
                'label': selected['label']
            }
        except Exception as e:
            return {'status': False, 'message': str(e)}

    def get_subtitle(self, download=True, output_dir=None, output_name=None):
        try:
            if not self.embed_url:
                return {
                    'status': False,
                    'message': 'Embed URL is required'
                }

            request = self.request.post(
                url='https://jeniusplay.com/player/index.php',
                params={
                    "data": self.embed_url,
                    "do": "getVideo"
                },
                headers={
                    "Host": "jeniusplay.com",
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                data={
                    "hash": self.embed_url,
                    "r": self.BASE_WEB_URL
                },
            )
            regex_subtitle = re.search(r"var playerjsSubtitle = \"(.*)\";", request.text)
            
            # Use output_name if provided, otherwise use safe_title
            if output_name:
                base_name = output_name
            else:
                base_name = self.get_safe_title()
            
            # Use output_dir if provided, otherwise current directory
            if output_dir:
                vtt_path = os.path.join(output_dir, base_name + '.vtt')
                srt_path = os.path.join(output_dir, base_name + '.srt')
            else:
                vtt_path = base_name + '.vtt'
                srt_path = base_name + '.srt'
            
            if regex_subtitle:
                if download:
                    subtitle_request = requests.get(
                        url="https://" + regex_subtitle.group(1).split("https://")[1],
                    )
                    with open(vtt_path, 'wb') as subtitle_file:
                        subtitle_file.write(subtitle_request.content)
                    self.convert_vtt_to_srt(vtt_path)
                    
                    # Delete VTT file after conversion (keep only SRT)
                    try:
                        os.remove(vtt_path)
                    except:
                        pass
                    
                    self.is_subtitle = True
                    return {
                        'status': True,
                        'subtitle': srt_path,
                    }

                self.is_subtitle = True
                return {
                    'status': True,
                    'subtitle': "https://" + regex_subtitle.group(1).split("https://")[1]
                }
            else:
                self.is_subtitle = False
                return {
                    'status': False,
                    'message': 'Subtitle not found'
                }
        except Exception as error_get_subtitle:
            return {
                'status': False,
                'message': str(error_get_subtitle)
            }

    def _move_subtitle_to_output(self, output_dir, output_name):
        """Move downloaded subtitle to organized output folder"""
        if not self.selected_subtitle:
            return
        
        safe_title = self.get_safe_title()
        old_srt = f"{safe_title}_{self.selected_subtitle['label']}.srt"
        new_srt = os.path.join(output_dir, f"{output_name}.srt")
        
        try:
            if os.path.exists(old_srt):
                shutil.move(old_srt, new_srt)
                logger.info(f"Subtitle moved to: {new_srt}")
        except Exception as e:
            logger.warning(f"Failed to move subtitle: {e}")

    def play_m3u8(self, subtitle_file=None):
        try:
            if not self.m3u8_url:
                return {
                    'status': False,
                    'message': 'M3U8 URL is required'
                }
            
            # Construct Headers (Checking logic for both players)
            user_agent = self.request.headers.get("User-Agent", "Mozilla/5.0")
            
            # Determine subtitle file - check multiple possible locations
            safe_title = self.get_safe_title()
            if subtitle_file is None:
                # Check for various subtitle file patterns
                possible_subs = [
                    safe_title + ".srt",
                ]
                # Also check for labeled subtitles (from multi-subtitle selection)
                if self.selected_subtitle:
                    possible_subs.insert(0, f"{safe_title}_{self.selected_subtitle['label']}.srt")
                
                for sub_path in possible_subs:
                    if os.path.exists(sub_path):
                        subtitle_file = sub_path
                        break
            
            # --- Try VLC Player (GUI) first ---
            try:
                from src.vlc_player import play_video_standalone
                
                logger.info("Launching VLC Player...")
                if subtitle_file:
                    logger.info(f"Loading subtitle: {subtitle_file}")
                
                success = play_video_standalone(self, self.m3u8_url, subtitle_file, self.video_name)
                
                if success:
                    return {
                        'status': True,
                        'message': 'Playing on VLC'
                    }
                else:
                    logger.warning("VLC Player failed or not available. Falling back to FFplay.")
            
            except Exception as e:
                logger.error(f"Error launching VLC: {e}. Falling back to FFplay.")
            # ----------------------------------

            logger.info("Launching FFplay...")
            headers = ""
            for k, v in self.BASE_STATIC_HEADERS.items():
                headers += f"{k}: {v}\r\n"
            
            # Add Cookies
            cookies = self.request.cookies.get_dict()
            if cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                headers += f"Cookie: {cookie_str}\r\n"

            command = [
                "ffplay",
                "-allowed_extensions", "ALL",
                "-allowed_segment_extensions", "ALL",
                "-extension_picky", "0",
                "-i",
                self.m3u8_url,
                "-window_title",
                self.video_name,
                "-user_agent",
                user_agent,
                "-headers",
                headers,
                "-hide_banner",
                "-autoexit"
            ]

            if subtitle_file and os.path.exists(subtitle_file):
                 command.extend(["-vf", "subtitles=" + subtitle_file])

            logger.info(f"FFplay Command: {' '.join(command)}")

            try:
                # Capture output to keep the terminal clean for CLI menu
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False
                )

                if result.returncode != 0:
                    return {
                        'status': False,
                        # Include stderr in the error message for debugging
                        'message': f"FFplay exited with code {result.returncode}: {result.stderr}"
                    }

            except FileNotFoundError:
                 return {
                    'status': False,
                    'message': "FFplay not found. Please ensure ffmpeg is installed/downloaded correctly."
                }

            # Cleanup subtitle files after FFplay closes
            if subtitle_file and os.path.exists(subtitle_file):
                try:
                    os.remove(subtitle_file)
                    vtt_path = subtitle_file.rsplit('.', 1)[0] + '.vtt'
                    if os.path.exists(vtt_path):
                        os.remove(vtt_path)
                    logger.info("Temporary subtitle files cleaned up.")
                except Exception as e:
                    logger.warning(f"Failed to cleanup subtitles: {e}")

            return {
                'status': True,
                'message': 'Playing m3u8'
            }
        except Exception as error_play_m3u8:
            return {
                'status': False,
                'message': str(error_play_m3u8)
            }

    @staticmethod
    def convert_vtt_to_srt(vtt_file):
        """Convert VTT to SRT with proper timestamp handling and X-TIMESTAMP-MAP offset"""
        srt_file = vtt_file.rsplit('.', 1)[0] + '.srt'
        
        try:
            with open(vtt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            output_lines = []
            cue_count = 0
            i = 0
            offset_ms = 0  # Offset to subtract from timestamps
            
            # Parse X-TIMESTAMP-MAP if present
            # Format: X-TIMESTAMP-MAP=MPEGTS:900000,LOCAL:00:00:00.000
            # MPEGTS is in 90kHz clock units
            for line in lines[:10]:  # Check first 10 lines for header
                if 'X-TIMESTAMP-MAP' in line:
                    # Extract MPEGTS value
                    mpegts_match = re.search(r'MPEGTS[=:](\d+)', line)
                    local_match = re.search(r'LOCAL[=:](\d{2}):(\d{2}):(\d{2})\.?(\d{3})?', line)
                    
                    if mpegts_match:
                        mpegts = int(mpegts_match.group(1))
                        # Convert 90kHz to milliseconds
                        mpegts_ms = mpegts / 90  # 90kHz clock
                        
                        local_ms = 0
                        if local_match:
                            h, m, s = int(local_match.group(1)), int(local_match.group(2)), int(local_match.group(3))
                            ms = int(local_match.group(4)) if local_match.group(4) else 0
                            local_ms = (h * 3600 + m * 60 + s) * 1000 + ms
                        
                        # Offset = MPEGTS timestamp - LOCAL timestamp
                        offset_ms = mpegts_ms - local_ms
                        logger.debug(f"VTT X-TIMESTAMP-MAP: MPEGTS={mpegts} ({mpegts_ms}ms), LOCAL={local_ms}ms, Offset={offset_ms}ms")
                    break
            
            # Skip header lines
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('WEBVTT') or line.startswith('NOTE') or \
                   line.startswith('STYLE') or line.startswith('X-TIMESTAMP-MAP') or \
                   line.startswith('Kind:') or line.startswith('Language:') or \
                   line == '':
                    i += 1
                    continue
                break
            
            def parse_timestamp(ts):
                """Parse VTT timestamp to milliseconds"""
                # Format: HH:MM:SS.mmm or MM:SS.mmm
                parts = ts.replace(',', '.').split(':')
                if len(parts) == 3:
                    h, m, s = parts
                else:
                    h = 0
                    m, s = parts
                
                s_parts = str(s).split('.')
                sec = int(s_parts[0])
                ms = int(s_parts[1]) if len(s_parts) > 1 else 0
                
                return (int(h) * 3600 + int(m) * 60 + sec) * 1000 + ms
            
            def format_timestamp(ms):
                """Format milliseconds to SRT timestamp"""
                if ms < 0:
                    ms = 0
                h = ms // 3600000
                m = (ms % 3600000) // 60000
                s = (ms % 60000) // 1000
                ms_part = ms % 1000
                return f"{h:02d}:{m:02d}:{s:02d},{ms_part:03d}"
            
            # Process cues
            while i < len(lines):
                line = lines[i].strip()
                
                if not line:
                    i += 1
                    continue
                
                # Check for timestamp line
                if '-->' in line:
                    cue_count += 1
                    
                    # Parse timestamps
                    # Remove positioning info first
                    ts_line = line.split('-->') 
                    if len(ts_line) >= 2:
                        start_ts = ts_line[0].strip().split()[0] if ts_line[0].strip() else "00:00:00.000"
                        end_part = ts_line[1].strip().split()
                        end_ts = end_part[0] if end_part else "00:00:00.000"
                        
                        # Parse and adjust timestamps
                        start_ms = parse_timestamp(start_ts) - offset_ms
                        end_ms = parse_timestamp(end_ts) - offset_ms
                        
                        # Format for SRT
                        new_timestamp = f"{format_timestamp(start_ms)} --> {format_timestamp(end_ms)}"
                        
                        output_lines.append(str(cue_count))
                        output_lines.append(new_timestamp)
                    
                    i += 1
                    
                    # Get subtitle text
                    while i < len(lines) and lines[i].strip():
                        text = re.sub(r'<[^>]+>', '', lines[i])
                        output_lines.append(text)
                        i += 1
                    
                    output_lines.append('')
                else:
                    i += 1
            
            # Write SRT file
            with open(srt_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            
            if offset_ms > 0:
                logger.info(f"Subtitle adjusted by -{offset_ms/1000:.1f}s offset")
            logger.debug(f"Converted {vtt_file} to {srt_file} ({cue_count} cues)")
            
        except Exception as e:
            logger.warning(f"Manual VTT conversion failed, using library: {e}")
            # Fallback to library
            convert_file = ConvertFile(vtt_file, "utf-8")
            convert_file.convert()

    def set_m3u8_url(self, m3u8_url):
        if "https://jeniusplay.com" not in m3u8_url:
            self.m3u8_url = "https://jeniusplay.com" + m3u8_url
        else:
            self.m3u8_url = m3u8_url
