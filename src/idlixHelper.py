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
        self.content_type = None  # 'movie' or 'episode'
        self.series_info = None  # Series metadata
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
                                episodes.append({
                                    'url': ep_link.get('href'),
                                    'number': ep_num,
                                    'title': ep_title,
                                    'full_title': f"{ep_num} - {ep_title}" if ep_title else ep_num
                                })
                    
                    seasons.append({
                        'season': season_num,
                        'episodes': episodes
                    })
            
            self.series_info = {
                'title': series_title,
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
                
                return {
                    'status': True,
                    'video_id': self.video_id,
                    'video_name': self.video_name,
                    'poster': self.poster,
                    'content_type': 'episode'
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
            if not self.m3u8_url:
                return {
                    'status': False,
                    'message': 'M3U8 URL is required'
                }
            
            # Create tmp directory if not exists
            if not os.path.exists(os.getcwd() + '/tmp/'):
                os.makedirs(os.getcwd() + '/tmp/', exist_ok=True)

            # --- Automatic Subtitle Download ---
            logger.info("Checking for subtitles...")
            sub_res = self.get_subtitle(download=True)
            if sub_res.get('status'):
                logger.success(f"Subtitle downloaded: {sub_res.get('subtitle')}")
                # The get_subtitle already names it as safe_title.srt
            else:
                logger.warning(f"No subtitle found or failed to download: {sub_res.get('message')}")
            # ------------------------------------

            logger.info(f"Starting download for {self.video_name}...")
            m3u8_To_MP4.multithread_download(
                m3u8_uri=self.m3u8_url,
                max_num_workers=10,
                mp4_file_name=self.video_name,
                mp4_file_dir=os.getcwd() + '/',
                tmpdir=os.getcwd() + '/tmp/'
            )
            
            # Cleanup tmp folder
            shutil.rmtree(os.getcwd() + '/tmp/', ignore_errors=True)
            
            final_path = os.getcwd() + '/' + self.video_name + '.mp4'
            return {
                'status': True,
                'message': 'Download success',
                'path': final_path
            }
        except Exception as error_download_m3u8:
            return {
                'status': False,
                'message': str(error_download_m3u8)
            }

    def get_safe_title(self):
        return re.sub(r'[\\/*?:"<>|&]', "", self.video_name).replace(" ", "_")

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
            self.is_subtitle = True
            
            return {
                'status': True,
                'subtitle': srt_file,
                'label': selected['label']
            }
        except Exception as e:
            return {'status': False, 'message': str(e)}

    def get_subtitle(self, download=True):
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
            safe_title = self.get_safe_title()
            
            if regex_subtitle:
                if download:
                    subtitle_request = requests.get(
                        url="https://" + regex_subtitle.group(1).split("https://")[1],
                    )
                    with open(safe_title + '.vtt', 'wb') as subtitle_file:
                        subtitle_file.write(subtitle_request.content)
                    self.convert_vtt_to_srt(safe_title + '.vtt')
                    self.is_subtitle = True
                    return {
                        'status': True,
                        'subtitle': safe_title + '.srt',
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

    def play_m3u8(self):
        try:
            if not self.m3u8_url:
                return {
                    'status': False,
                    'message': 'M3U8 URL is required'
                }
            
            # Construct Headers (Checking logic for both players)
            user_agent = self.request.headers.get("User-Agent", "Mozilla/5.0")
            
            # --- Try VLC Player (GUI) first ---
            try:
                from src.vlc_player import play_video_standalone
                
                safe_title = self.get_safe_title()
                subtitle_file = safe_title + ".srt" if (self.is_subtitle and os.path.exists(safe_title + ".srt")) else None
                
                logger.info("DeepMind: Attempting to launch VLC Player...")
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
            
            safe_title = self.get_safe_title()

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

            if self.is_subtitle:
                 command.extend(["-vf", "subtitles=" + safe_title + ".srt"])

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

            if self.is_subtitle and os.path.exists(safe_title + '.srt'):
                os.remove(safe_title + '.srt')
                os.remove(safe_title + '.vtt')

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
        convert_file = ConvertFile(vtt_file, "utf-8")
        convert_file.convert()

    def set_m3u8_url(self, m3u8_url):
        if "https://jeniusplay.com" not in m3u8_url:
            self.m3u8_url = "https://jeniusplay.com" + m3u8_url
        else:
            self.m3u8_url = m3u8_url
