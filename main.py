from src.idlixHelper import IdlixHelper, logger
from prettytable import PrettyTable
import inquirer
import os

status_exit = False
while not status_exit:
    if os.name == 'nt':
        os.system("cls")
    else:
        os.system("clear")
    table = PrettyTable()
    idlix_helper = IdlixHelper()
    get_home = idlix_helper.get_home()
    if get_home['status'] and len(get_home['featured_movie']) > 0:
        table.align = "l"
        table.title = "Featured Movie List"
        table.field_names = ["No", "Title", "Year", "Type", "URL"]
        for i, movie in enumerate(get_home['featured_movie']):
            table.add_row(
                [
                    i + 1,
                    movie['title'],
                    movie['year'],
                    movie['type'],
                    movie['url']
                ]
            )
        print(table)

        question = [
            inquirer.List(
                "action",
                message="Select action",
                choices=[
                    "Download Featured Movie",
                    "Play Featured Movie",
                    "Download Movie by URL",
                    "Play Movie by URL",
                    "Exit"
                ],
                carousel=True
            )
        ]
        answer = inquirer.prompt(question)
        if answer['action'] == "Download Featured Movie":
            question = [
                inquirer.List(
                    "movie",
                    message="Select movie",
                    choices=[str(i.get('title')) for i in get_home['featured_movie']],
                    carousel=True
                )
            ]
            answer = inquirer.prompt(question)
            get_video_data = idlix_helper.get_video_data(get_home['featured_movie'][get_home['featured_movie'].index(next((i for i in get_home['featured_movie'] if i['title'] == answer['movie']), None))]['url'])
            if get_video_data['status']:
                logger.info("Getting video data | Video ID : " + get_video_data['video_id'] + " | Video Name : " + get_video_data['video_name'])
                get_embed_url = idlix_helper.get_embed_url()
                if get_embed_url['status']:
                    logger.info("Getting embed url | Embed URL : " + get_embed_url['embed_url'])
                    get_m3u8_url = idlix_helper.get_m3u8_url()
                    if get_m3u8_url['status']:
                        logger.info("Getting m3u8 url | M3U8 URL : " + get_m3u8_url['m3u8_url'])

                        download_m3u8 = idlix_helper.download_m3u8()
                        if download_m3u8['status']:
                            logger.success("Downloading {} Success".format(get_video_data['video_name']))
                        else:
                            logger.error("Error downloading m3u8")
                    else:
                        logger.error("Error getting m3u8 url")
                else:
                    logger.error("Error getting embed url")
            else:
                logger.error("Error getting video data")

        elif answer['action'] == "Download Movie by URL":
            url = input("Enter movie URL ( Ex : https://vip.idlixofficialx.net/movie/kung-fu-panda-4-2024/) : ")
            get_video_data = idlix_helper.get_video_data(url)
            if get_video_data['status']:
                logger.info("Getting video data | Video ID : " + get_video_data['video_id'] + " | Video Name : " + get_video_data['video_name'])

                get_embed_url = idlix_helper.get_embed_url()
                if get_embed_url['status']:
                    logger.info("Getting embed url | Embed URL : " + get_embed_url['embed_url'])

                    get_m3u8_url = idlix_helper.get_m3u8_url()
                    if get_m3u8_url['status']:
                        logger.info("Getting m3u8 url | M3U8 URL : " + get_m3u8_url['m3u8_url'])

                        download_m3u8 = idlix_helper.download_m3u8()
                        if download_m3u8['status']:
                            logger.success("Downloading {} Success".format(get_video_data['video_name']))
                        else:
                            logger.error("Error downloading m3u8")
                    else:
                        logger.error("Error getting m3u8 url")
                else:
                    logger.error("Error getting embed url")
            else:
                logger.error("Error getting video data")

        elif answer['action'] == "Play Featured Movie":
            question = [
                inquirer.List(
                    "movie",
                    message="Select movie",
                    choices=[str(i.get('title')) for i in get_home['featured_movie']],
                    carousel=True
                )
            ]
            answer = inquirer.prompt(question)
            get_video_data = idlix_helper.get_video_data(get_home['featured_movie'][get_home['featured_movie'].index(next((i for i in get_home['featured_movie'] if i['title'] == answer['movie']), None))]['url'])
            if get_video_data['status']:
                logger.info("Getting video data | Video ID : " + get_video_data['video_id'] + " | Video Name : " + get_video_data['video_name'])

                get_embed_url = idlix_helper.get_embed_url()
                if get_embed_url['status']:
                    logger.info("Getting embed url | Embed URL : " + get_embed_url['embed_url'])

                    get_m3u8_url = idlix_helper.get_m3u8_url()
                    if get_m3u8_url['status']:
                        logger.info("Getting m3u8 url | M3U8 URL : " + get_m3u8_url['m3u8_url'])
                        play_m3u8 = idlix_helper.play_m3u8()
                        if play_m3u8['status']:
                            logger.success("Playing {} Success".format(get_video_data['video_name']))
                        else:
                            logger.error("Error playing m3u8")
                    else:
                        logger.error("Error getting m3u8 url")
                else:
                    logger.error("Error getting embed url")
            else:
                logger.error("Error getting video data")

        elif answer['action'] == "Play Movie by URL":
            url = input("Enter movie URL ( Ex : https://vip.idlixofficialx.net/movie/kung-fu-panda-4-2024/) : ")
            get_video_data = idlix_helper.get_video_data(url)
            if get_video_data['status']:
                logger.info("Getting video data | Video ID : " + get_video_data['video_id'] + " | Video Name : " + get_video_data['video_name'])

                get_embed_url = idlix_helper.get_embed_url()
                if get_embed_url['status']:
                    logger.info("Getting embed url | Embed URL : " + get_embed_url['embed_url'])

                    get_m3u8_url = idlix_helper.get_m3u8_url()
                    if get_m3u8_url['status']:
                        logger.info("Getting m3u8 url | M3U8 URL : " + get_m3u8_url['m3u8_url'])
                        play_m3u8 = idlix_helper.play_m3u8()
                        if play_m3u8['status']:
                            logger.success("Playing {} Success".format(get_video_data['video_name']))
                        else:
                            logger.error("Error playing m3u8")
                    else:
                        logger.error("Error getting m3u8 url")
                else:
                    logger.error("Error getting embed url")
            else:
                logger.error("Error getting video data")
        else:
            logger.info("Exiting")
            status_exit = True
