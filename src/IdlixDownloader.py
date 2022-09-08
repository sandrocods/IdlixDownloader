##
# Author  : Sandroputraa
# Name    : Idlix Downloader
# Build   : 12-08-2022
# Update  : 08-09-2022
#
# If you are a reliable programmer or the best developer, please don't change anything.
# If you want to be appreciated by others, then don't change anything in this script.
# Please respect me for making this tool from the beginning.
##
import os
import m3u8
import shutil
import requests
import m3u8_To_MP4
from os.path import exists
from bs4 import BeautifulSoup
from urllib.parse import urlparse

API = {
    'v1': 'https://94.103.82.88/',
    'v1_update' : 'https://195.2.92.213/',
    'v2': 'https://jeniusplay.com/'
}


class IdlixDownloader:

    def __init__(self, url):
        self.url = url
        self.name_video = urlparse(url).path.split('/')[2]

    def get_video_data(self):
        request = requests.get(
            url=self.url,
            headers={
                "Host": "94.103.82.88",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Referer": "https://94.103.82.88/",
            }
        )
        if request.status_code == 200:
            self.video_id = BeautifulSoup(request.text, 'html.parser').find('li',
                                                                            {'class': 'dooplay_player_option'}).get(
                'data-post')
            self.video_type = BeautifulSoup(request.text, 'html.parser').find('li',
                                                                              {'class': 'dooplay_player_option'}).get(
                'data-type')
            return {
                'status': True,
                'video_id': self.video_id,
                'video_type': self.video_type
            }
        else:
            return {
                'status': False,
            }

    def get_m3u8(self):
        try:
            playlist = m3u8.load(
                uri=self.uri,
                headers={
                    "Host": "jeniusplay.com",
                    "Connection": "keep-alive",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
                }
            )
            data_video = []
            for playlist in playlist.playlists:
                data_video.append({
                    'uri': playlist.uri,
                    'resolution': playlist.stream_info.resolution.__str__(),
                })
            return {
                'status': True,
                'data': data_video
            }
        except Exception as e:
            return {
                'status': False,
            }

    def get_embed_url(self):
        request = requests.post(
            url=API['v1_update'] + 'wp-admin/admin-ajax.php',
            data="action=doo_player_ajax&post=" + str(self.video_id) + "&nume=1&type=" + str(self.video_type),
            headers={
                "Host": "94.103.82.88",
                "Connection": "keep-alive",
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0",
                "Accept-Language": "en-US,en;q=0.9,id;q=0.8"
            }
        )
        if request.json()['embed_url']:
            self.data = urlparse(request.json()['embed_url']).path.split('/')[-1]
            return {
                'status': True,
                'embed_url': request.json()['embed_url'],
                'video_id': urlparse(request.json()['embed_url']).path.split('/')[-1]
            }
        else:
            return {
                'status': False,
            }

    def get_video(self):
        request = requests.post(
            url=API['v2'] + 'player/index.php?data=' + str(self.data) + '&do=getVideo',
            data="hash=" + str(self.data) + "&r=https%3A%2F%2F94.103.82.88%2F",
            headers={
                "Host": "jeniusplay.com",
                "Connection": "keep-alive",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
            }
        )
        if request.json()['hls']:
            self.uri = request.json()['videoSource']

            return {
                'status': True,
                'videoSource': request.json()['videoSource']
            }
        else:
            return {
                'status': False,
            }

    def download_video(self, uri):

        if exists(os.getcwd() + '/tmp/'):
            pass
        else:
            os.mkdir(os.getcwd() + '/tmp/')

        m3u8_To_MP4.multithread_download(
            m3u8_uri=uri,
            max_num_workers=10,
            mp4_file_name=self.name_video,
            mp4_file_dir=os.getcwd() + '/',
            tmpdir=os.getcwd() + '/tmp/'
        )

        shutil.rmtree(os.getcwd() + '/tmp/', ignore_errors=True)
