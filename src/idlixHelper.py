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
