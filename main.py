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
import py7zr
import shutil
import datetime
from os.path import exists
from colorama import Fore, init
from InquirerPy import inquirer
from pyfiglet import figlet_format
from src.IdlixDownloader import IdlixDownloader


def main():
    init(autoreset=True)

    print(Fore.GREEN +
          figlet_format("Idlix", font="Standard")
          + "Video Downloader - Make with ❤️️ by @sandro.putraa"
          )
    try:
        os.system("title Idlix Video Downloader - Make with ❤️️by @sandro.putraa")
        video_url = input('Enter video url : ')

        idlix = IdlixDownloader(
            url=video_url,
            worker=10,

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


def download_ffmpeg():
    print(Fore.GREEN + "[" + datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S") + "] " + Fore.WHITE + "Downloading " + Fore.LIGHTYELLOW_EX + " [ " + "ffmpeg.exe" + " ] " + Fore.GREEN + " Please Wait")

    # requests download file with progress bar
    # https://stackoverflow.com/questions/56795227/how-do-i-make-progress-bar-while-downloading-file-in-python


    # pyunpack extract file

    if exists(os.getcwd() + '\\ffmpeg'):
        shutil.rmtree(os.getcwd() + '\\ffmpeg')
    else:
        os.mkdir(os.getcwd() + "\\ffmpeg")

    with py7zr.SevenZipFile('ffmpeg.7z', mode='r') as z:
        z.extractall(os.getcwd() + '\\ffmpeg')

    print(Fore.GREEN + "[" + datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S") + "] " + Fore.WHITE + "Download " + Fore.LIGHTYELLOW_EX + " [ " + "ffmpeg.exe" + " ] " + Fore.GREEN + " Success")
    print(Fore.GREEN + "[" + datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S") + "] " + Fore.WHITE + "Please Restart The Program")
    exit()


if __name__ == '__main__':
    # # set path environment variable
    # download_ffmpeg()
    # exit()
    #
    # temp_path = []
    # for k, v in os.environ.items():
    #     temp_path.append(v)
    #
    # if os.path.dirname(os.path.realpath(__file__)) in temp_path:
    #     print("[!] [INFO] Path FFMPEG already set ")
    # else:
    #     subprocess.call(["setx", "PATH", "%PATH%;" + os.path.dirname(os.path.abspath(__file__)) + ""])
    #
    # if exists(os.path.dirname(os.path.realpath(__file__)) + "/ffmpeg.exe"):
    #     print("[!] [INFO] FFMPEG already installed ")
    # else:
    #     print("[!] [INFO] FFMPEG not installed ")
    #     print("[!] [INFO] Copying FFMPEG ")
    #     if exists(os.path.dirname(os.path.abspath(__file__)) + "\\ffmpeg.exe"):
    #         os.system("copy ffmpeg.exe " + os.path.dirname(os.path.abspath(__file__)) + "\\output\\ffmpeg.exe")

    try:
        main()
    except KeyboardInterrupt:
        print('\nExit')
        exit()
