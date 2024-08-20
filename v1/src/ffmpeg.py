import requests
from tqdm import *
from os.path import exists
from os import getcwd, mkdir
from bs4 import BeautifulSoup
import zipfile


class ffmpeg:

    def __init__(self):
        self.url = "https://www.gyan.dev/ffmpeg/builds/"

    def download_ffmpeg(self):
        global link_download
        # Download Lastest ffmpeg
        request_to_server = requests.get(self.url)

        parse = BeautifulSoup(request_to_server.text, 'html.parser')
        for i in parse.find('code', {'class': 'link'}):
            if "ffmpeg-git-essentials.7z" in i.text:
                link_download = i.get('href')
                break

        r = requests.get(
            url=link_download,
            stream=True
        )
        r.raise_for_status()
        with open(getcwd() + '\\ffmpeg.7z', 'wb') as f:
            pbar = tqdm(total=int(r.headers['Content-Length']))
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

        # Unzip ffmpeg
        with zipfile.ZipFile(getcwd() + '\\ffmpeg.7z', 'r') as zip_ref:
            zip_ref.extractall(getcwd() + '\\ffmpeg')


if __name__ == '__main__':
    ffmpeg().download_ffmpeg()
