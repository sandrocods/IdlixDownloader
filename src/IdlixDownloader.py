##
# Author  : Sandroputraa
# Name    : Idlix Downloader
# Build   : 12-08-2022
# Update  : 09-09-2022
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

# DEBUG
# from requests_toolbelt.utils import dump

API = {
    'v1': 'https://94.103.82.88/',
    'v2': 'https://jeniusplay.com/',
    'v1_update': 'https://195.2.92.213/'
}

STATIC_HEADER_1 = {
    "Host": "94.103.82.88",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Referer": "https://94.103.82.88/",
}

STATIC_HEADER_2 = {
    "Host": "jeniusplay.com",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
}


class IdlixDownloader:

    def __init__(self, url, worker = 10):
        self.uri = None
        self.data = None
        self.video_type = None
        self.video_id = None
        self.url = url
        self.worker = worker
        self.name_video = urlparse(url).path.split('/')[2]

    def get_video_data(self):
        """
        It gets the video id and type from the page's html
        :return: A dictionary with the status of the request, the video id, and the video type.
        """
        request = requests.get(
            url=self.url,
            headers=STATIC_HEADER_1
        )
        if request.status_code == 200:
            self.video_id = BeautifulSoup(request.text, 'html.parser') \
                .find('li', {'class': 'dooplay_player_option'}).get('data-post')
            self.video_type = BeautifulSoup(request.text, 'html.parser') \
                .find('li', {'class': 'dooplay_player_option'}).get('data-type')
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
        """
        It takes a URI, and returns a list of dictionaries containing the URI and resolution of each playlist
        :return: A dictionary with a key of status and a value of True.
        """
        try:
            playlist = m3u8.load(
                uri=self.uri,
                headers=STATIC_HEADER_2
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
                'msg_error': str(e),
                'status': False,
            }

    def get_embed_url(self):
        """
        It takes a video id and a video type, and returns a dictionary with the embed url and video id
        :return: A dictionary with the status of the request, the embed_url and the video_id.
        """
        STATIC_HEADER_1.update(
            {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
        )
        request = requests.post(
            url=API['v1_update'] + 'wp-admin/admin-ajax.php',
            data="action=doo_player_ajax&post=" + str(self.video_id) + "&nume=1&type=" + str(self.video_type),
            headers=STATIC_HEADER_1
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
        """
        It sends a POST request to the API endpoint with the hash of the video and the referer, and returns the video source
        if the video is available
        :return: A dictionary with a status key and a videoSource key.
        """
        STATIC_HEADER_2.update(
            {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest"
            }
        )
        request = requests.post(
            url=API['v2'] + 'player/index.php?data=' + str(self.data) + '&do=getVideo',
            data="hash=" + str(self.data) + "&r=https%3A%2F%2F94.103.82.88%2F",
            headers=STATIC_HEADER_2
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
        """
        It downloads a video from a given URI, and saves it in the current working directory

        :param uri: The URI of the m3u8 file
        """

        if exists(os.getcwd() + '/tmp/'):
            pass
        else:
            os.mkdir(os.getcwd() + '/tmp/')

        m3u8_To_MP4.multithread_download(
            m3u8_uri=uri,
            max_num_workers=self.worker,
            mp4_file_name=self.name_video,
            mp4_file_dir=os.getcwd() + '/',
            tmpdir=os.getcwd() + '/tmp/'
        )

        shutil.rmtree(os.getcwd() + '/tmp/', ignore_errors=True)
