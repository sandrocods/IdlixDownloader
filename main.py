##
# Author  : Sandroputraa
# Name    : Idlix Downloader
# Build   : 12-08-2022
#
# If you are a reliable programmer or the best developer, please don't change anything.
# If you want to be appreciated by others, then don't change anything in this script.
# Please respect me for making this tool from the beginning.
##

import datetime
from prettytable import PrettyTable
from src.IdlixDownloader import IdlixDownloader
from colorama import Fore, init

init(autoreset=True)

print(Fore.GREEN + """
  ___ ___  _    _____  __
 |_ _|   \| |  |_ _\ \/ /
  | || |) | |__ | | >  < 
 |___|___/|____|___/_/\_\ \n
Video Downloader - Make with ❤️️ by @sandro.putraa
 """)

video_url = input('Enter video url : ')

idlix = IdlixDownloader(video_url)

if idlix.get_video_data()['status']:
    print(Fore.GREEN + "[" + datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S") + "] " + Fore.WHITE + "Get Video " + Fore.LIGHTYELLOW_EX + " [ " + idlix.name_video.replace(
        "-", " ") + " ] " + Fore.GREEN + " Success")
    print(Fore.GREEN + "[" + datetime.datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S") + "] " + Fore.WHITE + "Video Type " + Fore.LIGHTYELLOW_EX + " [ " + idlix.video_type + " ]")

    if idlix.get_embed_url()['status']:

        if idlix.get_video()['status']:

            if idlix.get_m3u8()['status']:
                t = PrettyTable(title="Select Video Quality", field_names=['No', 'Name Video', 'Resolution'])
                for i, play in enumerate(idlix.get_m3u8()['data']):
                    t.add_row([str(i), str(idlix.name_video), play['resolution']])
                print(t)
                while True:
                    try:
                        choice = int(input("Enter your choice : "))
                        if choice < len(idlix.get_m3u8()['data']):
                            break
                        else:
                            print("Invalid choice")
                    except Exception as e:
                        print(e)
                        print("Invalid choice")

                idlix.download_video(idlix.get_m3u8()['data'][choice]['uri'])

            else:
                print("Error get m3u8")
        else:
            print('Error getting video')
    else:
        print("Embed url not found")
else:
    print('Video not found')
    exit()
