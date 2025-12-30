from src.idlixHelper import IdlixHelper, logger
from prettytable import PrettyTable
import inquirer
import threading
import time

RETRY_LIMIT = 3


def retry(func, *args, **kwargs):
    last_result = {"status": False, "message": "Unknown error"}
    for _ in range(RETRY_LIMIT):
        try:
            result = func(*args, **kwargs)
            if result and result.get("status"):
                return result
            last_result = result
        except Exception as e:
            last_result = {"status": False, "message": str(e)}
        time.sleep(1)
    if not last_result.get("message"):
        last_result["message"] = "Maximum retry reached"
    return last_result


def play_m3u8_thread(idlix_helper):
    result = idlix_helper.play_m3u8()
    if result.get("status"):
        logger.success("Playing Success")
    else:
        logger.error(f"Error playing m3u8: {result.get('message')}")


def process_movie(idlix_helper, url: str, mode: str):
    video_data = retry(idlix_helper.get_video_data, url)
    if not video_data.get("status"):
        logger.error("Error getting video data")
        return

    logger.info(
        f"Getting video data | Video ID: {video_data['video_id']} | Video Name: {video_data['video_name']}"
    )

    embed = retry(idlix_helper.get_embed_url)
    if not embed.get("status"):
        logger.error("Error getting embed URL")
        return

    logger.success(f"Getting embed URL: {embed['embed_url']}")

    m3u8 = retry(idlix_helper.get_m3u8_url)
    if not m3u8.get("status"):
        logger.error("Error getting M3U8 URL")
        return

    logger.success(f"Getting m3u8 URL | {m3u8['m3u8_url']}")

    if m3u8.get("is_variant_playlist"):
        logger.warning("This video has a variant playlist")

        choices = [
            f"{v['id']} - {v['resolution']}" for v in m3u8["variant_playlist"]
        ]

        question = [
            inquirer.List(
                "variant",
                message="Select variant",
                choices=choices,
                carousel=True
            )
        ]
        answer = inquirer.prompt(question)

        selected_id = answer["variant"].split(" - ")[0]

        for v in m3u8["variant_playlist"]:
            if str(v["id"]) == selected_id:
                idlix_helper.set_m3u8_url(v["uri"])
                logger.success(f"Selected variant: {v['resolution']}")
                break
    else:
        logger.warning("This video has no variant playlist")

    # 5. If play → download subtitle
    if mode == "play":
        subtitle = idlix_helper.get_subtitle()
        if subtitle.get("status"):
            logger.success("Subtitle downloaded")
        else:
            logger.error("Subtitle unavailable")

        logger.info(f"Playing {video_data['video_name']} ...")

        th = threading.Thread(target=play_m3u8_thread, args=(idlix_helper,))
        th.daemon = True
        th.start()

        # avoid hang forever
        th.join(timeout=5)

    # 6. If download
    else:
        result = idlix_helper.download_m3u8()
        if result.get("status"):
            logger.success(f"Downloading {video_data['video_name']} success")
        else:
            logger.error("Error downloading m3u8")


def show_featured_table(featured):
    table = PrettyTable()
    table.align = "l"
    table.title = "Featured Movie List"
    table.field_names = ["No", "Title", "Year", "Type", "URL"]

    for i, movie in enumerate(featured):
        table.add_row([
            i + 1,
            movie["title"],
            movie["year"],
            movie["type"],
            movie["url"]
        ])

    print(table)


def main():
    status_exit = False

    while not status_exit:
        idlix = IdlixHelper()
        home = retry(idlix.get_home)

        if not home.get("status") or len(home.get("featured_movie", [])) == 0:
            logger.error(f"Error fetching home: {home.get('message')}")
            break

        featured = home["featured_movie"]
        show_featured_table(featured)

        # Main Menu
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
        action = answer["action"]
        if action in ["Download Featured Movie", "Play Featured Movie"]:
            # Select movie
            movie_question = [
                inquirer.List(
                    "movie",
                    message="Select movie",
                    choices=[i["title"] for i in featured],
                    carousel=True
                )
            ]
            choice = inquirer.prompt(movie_question)

            selected = next(
                (m for m in featured if m["title"] == choice["movie"]),
                None
            )

            if not selected:
                logger.error("Movie not found")
                continue

            mode = "download" if "Download" in action else "play"
            process_movie(idlix, selected["url"], mode)


        elif action == "Download Movie by URL":
            url = input("Enter movie URL: ").strip()
            process_movie(idlix, url, "download")

        elif action == "Play Movie by URL":
            url = input("Enter movie URL: ").strip()
            process_movie(idlix, url, "play")

        # Exit
        else:
            logger.info("Exiting...")
            status_exit = True


if __name__ == "__main__":
    main()
