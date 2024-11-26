"""
Helper Class for IDLIX Downloader & IDLIX Player CLI

Update  :   27-11-2024
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
from curl_cffi import requests as cffi_requests
from src.CryptoJsAesHelper import CryptoJsAes, dec


class IdlixHelper:
    BASE_WEB_URL = "https://tv2.idlix.asia/"
    BASE_STATIC_HEADERS = {
        "Host": "tv2.idlix.asia",
        "Connection": "keep-alive",
        "sec-ch-ua": "Not)A;Brand;v=99, Google Chrome;v=127, Chromium;v=127",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "Windows",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Referer": BASE_WEB_URL,
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8"
    }

    def __init__(self):
        self.poster = None
        self.m3u8_url = None
        self.video_id = None
        self.embed_url = None
        self.video_name = None
        self.is_subtitle = None
        self.variant_playlist = None
        self.request = cffi_requests.Session(
            impersonate=random.choice(["chrome124", "chrome119", "chrome104"]),
            headers=self.BASE_STATIC_HEADERS,
            debug=False
        )

        # FFMPEG
        if os.name == 'nt':
            for _ in os.environ.get('path').split(';'):
                if 'ffmpeg' in _:
                    logger.info(f'FFMPEG Found: {_}')
                    break
            else:
                if not os.path.exists('ffmpeg-release-essentials.zip'):
                    self.download_ffmpeg()
                logger.warning('FFMPEG not set in PATH, Trying set PATH')
                try:
                    with zipfile.ZipFile('ffmpeg-release-essentials.zip', 'r') as zip_ref:
                        zip_ref.extractall(
                            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')
                        )
                    logger.success('Success Extracting ffmpeg')
                    path = ""
                    for _ in os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')):
                        if 'ffmpeg' in _:
                            logger.info(f'Found: {os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", _, "bin")}')
                            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ffmpeg", _, "bin")
                            break
                    else:
                        logger.error('FFMPEG not found, please install ffmpeg first before running this script')
                    subprocess.call(["setx", "PATH", "%PATH%;" + path])
                    logger.success('FFMPEG PATH set successfully, Please restart the program')
                    exit()
                except Exception as e:
                    print(f'Error: {e}')
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
                url=self.BASE_WEB_URL
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
                        "type": featured.find('a').get('href').split('/')[3]
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
            request = cffi_requests.post(
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
                impersonate="chrome",
            )

            if request.status_code == 200 and request.json().get('videoSource'):
                self.m3u8_url = request.json().get('videoSource')
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
            if not os.path.exists(os.getcwd() + '/tmp/'):
                os.mkdir(os.getcwd() + '/tmp/')

            m3u8_To_MP4.multithread_download(
                m3u8_uri=self.m3u8_url,
                max_num_workers=10,
                mp4_file_name=self.video_name,
                mp4_file_dir=os.getcwd() + '/',
                tmpdir=os.getcwd() + '/tmp/'
            )
            shutil.rmtree(os.getcwd() + '/tmp/', ignore_errors=True)
            return {
                'status': True,
                'message': 'Download success',
                'path': os.getcwd() + '/' + self.video_name + '.mp4'
            }
        except Exception as error_download_m3u8:
            return {
                'status': False,
                'message': str(error_download_m3u8)
            }

    def get_subtitle(self, download=True):
        try:
            if not self.embed_url:
                return {
                    'status': False,
                    'message': 'Embed URL is required'
                }

            request = cffi_requests.post(
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
                impersonate="chrome",

            )
            regex_subtitle = re.search(r"var playerjsSubtitle = \"(.*)\";", request.text)
            if regex_subtitle:
                if download:
                    subtitle_request = requests.get(
                        url="https://" + regex_subtitle.group(1).split("https://")[1],
                    )
                    with open(self.video_name.replace(" ", "_") + '.vtt', 'wb') as subtitle_file:
                        subtitle_file.write(subtitle_request.content)
                    self.convert_vtt_to_srt(self.video_name.replace(" ", "_") + '.vtt')
                    self.is_subtitle = True
                    return {
                        'status': True,
                        'subtitle': self.video_name.replace(" ", "_") + '.srt',
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

            if self.is_subtitle:
                subprocess.call([
                    "ffplay",
                    "-i",
                    self.m3u8_url,
                    "-window_title",
                    self.video_name,
                    "-vf",
                    "subtitles=" + self.video_name.replace(" ", "_") + ".srt",
                    "-hide_banner",
                    "-loglevel",
                    "panic"
                ])

            subprocess.call([
                "ffplay",
                "-i",
                self.m3u8_url,
                "-window_title",
                self.video_name,
                "-hide_banner",
                "-loglevel",
                "panic"
            ])

            if self.is_subtitle and os.path.exists(self.video_name.replace(" ", "_") + '.srt'):
                os.remove(self.video_name.replace(" ", "_") + '.srt')
                os.remove(self.video_name.replace(" ", "_") + '.vtt')

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
        self.m3u8_url = m3u8_url
