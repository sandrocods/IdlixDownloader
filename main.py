##
# Author  : Sandroputraa
# Name    : Idlix Downloader
# Build   : 12-08-2022
# Update  : 17-08-2022
#
# If you are a reliable programmer or the best developer, please don't change anything.
# If you want to be appreciated by others, then don't change anything in this script.
# Please respect me for making this tool from the beginning.
##
import os
from os.path import exists
import datetime
import subprocess
from InquirerPy import inquirer
from src.IdlixDownloader import IdlixDownloader
from colorama import Fore, init


def main():
    init(autoreset=True)
    print(Fore.GREEN + """
      ___ ___  _    _____  __
     |_ _|   \| |  |_ _\ \/ /
      | || |) | |__ | | >  < 
     |___|___/|____|___/_/\_\ \n
    Video Downloader - Make with ❤️️ by @sandro.putraa
     """)
    try:
        os.system("title Idlix Video Downloader - Make with ❤️️by @sandro.putraa")
        video_url = input('Enter video url : ')

        idlix = IdlixDownloader(
            url=video_url,
            worker=10
        )

        if idlix.get_video_data()['status']:
            print(Fore.GREEN + "[" + datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S") + "] " + Fore.WHITE + "Get Video " + Fore.LIGHTYELLOW_EX + " [ " + idlix.name_video.replace(
                "-", " ") + " ] " + Fore.GREEN + " Success")
            print(Fore.GREEN + "[" + datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S") + "] " + Fore.WHITE + "Video Type" + Fore.LIGHTYELLOW_EX + " [ " + idlix.video_type + " ]")

            if idlix.get_embed_url()['status']:

                if idlix.get_video()['status']:

                    if idlix.get_m3u8()['status']:

                        data_video_tmp = []
                        for i, play in enumerate(idlix.get_m3u8()['data']):
                            data_video_tmp.append(play['resolution'])

                        qualityVideo = inquirer.select(
                            message="Select Quality Video : ",
                            choices=data_video_tmp,

                        ).execute()

                        for data in idlix.get_m3u8()['data']:
                            if data['resolution'] == qualityVideo:
                                os.system("title Downloading Video " + idlix.name_video.replace("-", " "))
                                idlix.download_video(data['uri'])
                                os.system("cls")
                                main()

                    else:
                        print("Error get m3u8")
                        exit()
                else:
                    print('Error getting video')
                    exit()
            else:
                print("Embed url not found")
                exit()
        else:
            print('Video not found')
            exit()

    except IndexError:
        print('Enter Valid Video Url')
        exit()


if __name__ == '__main__':
    # set path environment variable
    temp_path = []
    for k, v in os.environ.items():
        temp_path.append(v)

    for data_temp in temp_path:
        if data_temp in os.path.dirname(os.path.realpath(__file__)):
            print("[!] [INFO] Path FFMPEG already set in : " + data_temp)
            break
    else:
        subprocess.call(["setx", "PATH", "%PATH%;" + os.path.dirname(os.path.abspath(__file__)) + ""])

    if exists(os.path.dirname(os.path.abspath(__file__)) + "\\ffmpeg.exe"):
        os.system("copy ffmpeg.exe " + os.path.dirname(os.path.abspath(__file__)) + "\\output\\ffmpeg.exe")

    try:
        main()
    except KeyboardInterrupt:
        print('\nExit')
        exit()
