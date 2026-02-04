from src.idlixHelper import IdlixHelper, logger
from prettytable import PrettyTable
import inquirer
import time
import os

RETRY_LIMIT = 3


def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print app header"""
    print("\n" + "=" * 60)
    print("   🎬 IDLIX Downloader & Player CLI")
    print("   Support: Movies & TV Series")
    print("=" * 60 + "\n")


def retry(func, *args, **kwargs):
    last_result = {"status": False, "message": "Unknown error"}
    for attempt in range(RETRY_LIMIT):
        try:
            result = func(*args, **kwargs)
            if result and result.get("status"):
                return result
            last_result = result
        except Exception as e:
            last_result = {"status": False, "message": str(e)}
        if attempt < RETRY_LIMIT - 1:
            logger.warning(f"Retry {attempt + 1}/{RETRY_LIMIT}...")
            time.sleep(1)
    if not last_result.get("message"):
        last_result["message"] = "Maximum retry reached"
    return last_result


def select_subtitle(idlix_helper):
    """Let user select subtitle from available options"""
    subs_result = idlix_helper.get_available_subtitles()
    
    if not subs_result.get("status"):
        logger.warning("No subtitles available")
        return None
    
    subtitles = subs_result.get("subtitles", [])
    
    if len(subtitles) == 0:
        logger.warning("No subtitles found")
        return None
    
    if len(subtitles) == 1:
        logger.info(f"Found 1 subtitle: {subtitles[0]['label']}")
        return subtitles[0]['id']
    
    # Multiple subtitles - let user choose
    logger.info(f"Found {len(subtitles)} subtitles")
    
    choices = [f"{s['id']} - {s['label']}" for s in subtitles]
    choices.append("No Subtitle")
    
    question = [
        inquirer.List(
            "subtitle",
            message="🗣️  Select subtitle language",
            choices=choices,
            carousel=True
        )
    ]
    answer = inquirer.prompt(question)
    
    if answer["subtitle"] == "No Subtitle":
        return None
    
    return answer["subtitle"].split(" - ")[0]


def select_subtitle_mode():
    """Let user select how to handle subtitle during download"""
    question = [
        inquirer.List(
            "mode",
            message="📝 Subtitle mode",
            choices=[
                "Separate File (.srt) - Fast, file terpisah",
                "Softcode (Embed) - Fast, subtitle track di MKV",
                "Hardcode (Burn-in) - Slow, permanent di video"
            ],
            carousel=True
        )
    ]
    answer = inquirer.prompt(question)
    
    if "Separate" in answer["mode"]:
        return "separate"
    elif "Softcode" in answer["mode"]:
        return "softcode"
    else:
        return "hardcode"


def select_resolution(idlix_helper, m3u8):
    """Let user select video resolution"""
    if not m3u8.get("is_variant_playlist"):
        logger.info("Single resolution available")
        return
    
    logger.info("Multiple resolutions available")
    
    choices = [f"{v['id']} - {v['resolution']}" for v in m3u8["variant_playlist"]]
    
    question = [
        inquirer.List(
            "variant",
            message="📺 Select resolution",
            choices=choices,
            carousel=True
        )
    ]
    answer = inquirer.prompt(question)
    
    selected_id = answer["variant"].split(" - ")[0]
    
    for v in m3u8["variant_playlist"]:
        if str(v["id"]) == selected_id:
            idlix_helper.set_m3u8_url(v["uri"])
            logger.success(f"Selected: {v['resolution']}")
            break


def process_content(idlix_helper, url: str, mode: str, is_episode: bool = False, episode_info: dict = None, 
                    preset_resolution: str = None, preset_subtitle: str = None, preset_sub_mode: str = None):
    """Process movie or episode for play/download
    
    Args:
        episode_info: Optional dict with keys: series_title, series_year, season_num, episode_num
                      Used for organized folder structure when downloading series
        preset_resolution: Pre-selected resolution ID for batch downloads
        preset_subtitle: Pre-selected subtitle ID for batch downloads (empty string = no subtitle)
        preset_sub_mode: Pre-selected subtitle mode for batch downloads
    """
    
    # 1. Get video data
    if is_episode:
        video_data = retry(idlix_helper.get_episode_data, url)
    else:
        video_data = retry(idlix_helper.get_video_data, url)
    
    if not video_data.get("status"):
        logger.error("Error getting video data")
        return False

    logger.info(f"📽️  {video_data['video_name']}")
    
    # Set episode metadata for organized folder structure
    if episode_info and mode == "download":
        idlix_helper.set_episode_meta(
            series_title=episode_info.get('series_title', 'Unknown'),
            series_year=episode_info.get('series_year', '2025'),
            season_num=episode_info.get('season_num', 1),
            episode_num=episode_info.get('episode_num', 1)
        )

    # 2. Get embed URL
    if is_episode:
        embed = retry(idlix_helper.get_embed_url_episode)
    else:
        embed = retry(idlix_helper.get_embed_url)
    
    if not embed.get("status"):
        logger.error("Error getting embed URL")
        return False

    logger.success(f"Embed URL obtained")

    # 3. Get M3U8 URL
    m3u8 = retry(idlix_helper.get_m3u8_url)
    if not m3u8.get("status"):
        logger.error("Error getting M3U8 URL")
        return False

    logger.success(f"M3U8 URL obtained")

    # 4. Select resolution (use preset if provided)
    if preset_resolution and m3u8.get("is_variant_playlist"):
        for v in m3u8["variant_playlist"]:
            if str(v["id"]) == preset_resolution:
                idlix_helper.set_m3u8_url(v["uri"])
                logger.info(f"Using preset resolution: {v['resolution']}")
                break
    else:
        select_resolution(idlix_helper, m3u8)

    # 5. Handle subtitle selection (use preset if provided)
    if preset_subtitle is not None:
        subtitle_id = preset_subtitle if preset_subtitle != "" else None
        if subtitle_id:
            logger.info(f"Using preset subtitle")
        else:
            logger.info(f"Subtitle skipped (preset: no subtitle)")
            idlix_helper.set_skip_subtitle(True)
    else:
        subtitle_id = select_subtitle(idlix_helper)
        if subtitle_id is None:
            idlix_helper.set_skip_subtitle(True)
    
    # 6. Play or Download
    if mode == "play":
        if subtitle_id:
            sub_result = idlix_helper.download_selected_subtitle(subtitle_id)
            if sub_result.get("status"):
                logger.success(f"Subtitle loaded: {sub_result.get('label')}")
        
        logger.info(f"▶️  Playing {video_data['video_name']} ...")

        # Run VLC directly on main thread (Tkinter requirement)
        result = idlix_helper.play_m3u8()
        if result.get("status"):
            logger.success("Playback finished")
        else:
            logger.error(f"Error playing: {result.get('message')}")
    else:
        # Download mode - only ask for subtitle mode if subtitle selected
        if subtitle_id:
            # Use preset mode if provided, otherwise ask
            if preset_sub_mode:
                sub_mode = preset_sub_mode
                logger.info(f"Using preset subtitle mode: {sub_mode}")
            else:
                sub_mode = select_subtitle_mode()
            
            idlix_helper.set_subtitle_mode(sub_mode)
            
            # Only download subtitle now
            sub_result = idlix_helper.download_selected_subtitle(subtitle_id)
            if sub_result.get("status"):
                logger.success(f"Subtitle downloaded: {sub_result.get('label')}")
        
        result = idlix_helper.download_m3u8()
        if result.get("status"):
            logger.success(f"✅ Downloaded: {video_data['video_name']}")
        else:
            logger.error(f"Download failed: {result.get('message')}")
            return False
    
    return True


def process_series(idlix_helper, url: str, mode: str):
    """Process series - show seasons and episodes"""
    
    # Detect if URL is episode or series page
    if '/episode/' in url:
        # Direct episode URL
        logger.info("Processing single episode...")
        return process_content(idlix_helper, url, mode, is_episode=True)
    
    # Get series info
    logger.info("Loading series information...")
    series_result = retry(idlix_helper.get_series_info, url)
    
    if not series_result.get("status"):
        logger.error(f"Error getting series info: {series_result.get('message')}")
        return False
    
    series_info = series_result["series_info"]
    
    print(f"\n📺 Series: {series_info['title']}")
    print(f"   Seasons: {len(series_info['seasons'])}")
    
    if not series_info['seasons']:
        logger.error("No seasons found")
        return False
    
    # Select season
    season_choices = [f"Season {s['season']} ({len(s['episodes'])} episodes)" for s in series_info['seasons']]
    
    question = [
        inquirer.List(
            "season",
            message="📅 Select season",
            choices=season_choices,
            carousel=True
        )
    ]
    answer = inquirer.prompt(question)
    
    selected_season_idx = season_choices.index(answer["season"])
    selected_season = series_info['seasons'][selected_season_idx]
    
    if not selected_season['episodes']:
        logger.error("No episodes in this season")
        return False
    
    # Download mode options
    if mode == "download":
        download_choices = [
            "Download All Episodes (Full Season)",
            "Download Single Episode",
            "Back"
        ]
        
        question = [
            inquirer.List(
                "download_mode",
                message="📥 Download option",
                choices=download_choices,
                carousel=True
            )
        ]
        answer = inquirer.prompt(question)
        
        if answer["download_mode"] == "Back":
            return False
        
        if answer["download_mode"] == "Download All Episodes (Full Season)":
            # Download all episodes
            total = len(selected_season['episodes'])
            logger.info(f"Downloading {total} episodes from Season {selected_season['season']}...")
            
            # === Pre-select resolution and subtitle for first episode ===
            first_ep = selected_season['episodes'][0]
            logger.info("Setting up resolution and subtitle for all episodes...")
            
            # Get first episode data to determine available resolutions/subtitles
            first_helper = IdlixHelper()
            video_data = retry(first_helper.get_episode_data, first_ep['url'])
            if not video_data.get("status"):
                logger.error("Failed to get first episode data")
                return False
            
            embed = retry(first_helper.get_embed_url_episode)
            if not embed.get("status"):
                logger.error("Failed to get embed URL")
                return False
            
            m3u8 = retry(first_helper.get_m3u8_url)
            if not m3u8.get("status"):
                logger.error("Failed to get M3U8 URL")
                return False
            
            # Select resolution once
            preset_resolution = None
            if m3u8.get("is_variant_playlist"):
                logger.info("Select resolution for ALL episodes:")
                choices = [f"{v['id']} - {v['resolution']}" for v in m3u8["variant_playlist"]]
                question = [
                    inquirer.List(
                        "variant",
                        message="📺 Select resolution (applies to all episodes)",
                        choices=choices,
                        carousel=True
                    )
                ]
                answer = inquirer.prompt(question)
                preset_resolution = answer["variant"].split(" - ")[0]
                logger.success(f"Resolution {answer['variant'].split(' - ')[1]} will be used for all episodes")
            
            # Select subtitle once
            preset_subtitle = None
            preset_sub_mode = None
            subs_result = first_helper.get_available_subtitles()
            if subs_result.get("status"):
                subtitles = subs_result.get("subtitles", [])
                if subtitles:
                    logger.info("Select subtitle for ALL episodes:")
                    choices = [f"{s['id']} - {s['label']}" for s in subtitles]
                    choices.append("No Subtitle")
                    question = [
                        inquirer.List(
                            "subtitle",
                            message="🗣️  Select subtitle (applies to all episodes)",
                            choices=choices,
                            carousel=True
                        )
                    ]
                    answer = inquirer.prompt(question)
                    if answer["subtitle"] != "No Subtitle":
                        preset_subtitle = answer["subtitle"].split(" - ")[0]
                        logger.success(f"Subtitle {answer['subtitle'].split(' - ')[1]} will be used for all episodes")
                        
                        # Ask for subtitle mode ONCE (only if subtitle selected)
                        preset_sub_mode = select_subtitle_mode()
                        logger.success(f"Subtitle mode '{preset_sub_mode}' will be used for all episodes")
                    else:
                        preset_subtitle = ""  # Empty string means no subtitle
                        logger.info("No subtitle will be downloaded for all episodes")
            
            print(f"\n{'='*50}")
            logger.info("Starting batch download...")
            print(f"{'='*50}\n")
            
            # Now download all episodes with preset settings
            for i, ep in enumerate(selected_season['episodes']):
                print(f"\n{'='*50}")
                logger.info(f"Episode {i+1}/{total}: {ep['full_title']}")
                
                # Create new helper for each episode to avoid state issues
                ep_helper = IdlixHelper()
                
                # Build episode info for organized folder structure
                episode_info = {
                    'series_title': series_info['title'],
                    'series_year': series_info.get('year', '2025'),
                    'season_num': ep.get('season_num', selected_season['season']),
                    'episode_num': ep.get('episode_num', i + 1)
                }
                
                success = process_content(
                    ep_helper, ep['url'], "download", 
                    is_episode=True, 
                    episode_info=episode_info,
                    preset_resolution=preset_resolution,
                    preset_subtitle=preset_subtitle,
                    preset_sub_mode=preset_sub_mode
                )
                
                if not success:
                    logger.warning(f"Failed to download episode {ep['full_title']}")
                    
                    continue_q = [
                        inquirer.Confirm(
                            "continue",
                            message="Continue with remaining episodes?",
                            default=True
                        )
                    ]
                    if not inquirer.prompt(continue_q)["continue"]:
                        break
            
            logger.success(f"Season {selected_season['season']} download complete!")
            return True
    
    # Single episode selection (for both play and single download)
    episode_choices = [ep['full_title'] for ep in selected_season['episodes']]
    
    question = [
        inquirer.List(
            "episode",
            message="🎬 Select episode",
            choices=episode_choices,
            carousel=True
        )
    ]
    answer = inquirer.prompt(question)
    
    selected_ep_idx = episode_choices.index(answer["episode"])
    selected_episode = selected_season['episodes'][selected_ep_idx]
    
    logger.info(f"Selected: {selected_episode['full_title']}")
    
    # Build episode info for organized folder structure
    episode_info = None
    if mode == "download":
        episode_info = {
            'series_title': series_info['title'],
            'series_year': series_info.get('year', '2025'),
            'season_num': selected_episode.get('season_num', selected_season['season']),
            'episode_num': selected_episode.get('episode_num', selected_ep_idx + 1)
        }
    
    return process_content(idlix_helper, selected_episode['url'], mode, is_episode=True, episode_info=episode_info)


def show_featured_table(featured, title="Featured List"):
    """Display featured content in table format"""
    table = PrettyTable()
    table.align = "l"
    table.title = title
    table.field_names = ["No", "Title", "Year", "Type"]

    for i, item in enumerate(featured):
        table.add_row([
            i + 1,
            item["title"][:40] + "..." if len(item["title"]) > 40 else item["title"],
            item["year"],
            item["type"].upper()
        ])

    print(table)


def main():
    status_exit = False

    while not status_exit:
        clear_screen()
        print_header()
        
        idlix = IdlixHelper()
        
        # Main Menu
        main_menu = [
            inquirer.List(
                "action",
                message="🎯 What would you like to do?",
                choices=[
                    "🎬 Movies",
                    "📺 TV Series",
                    "🔗 Play/Download by URL",
                    "❌ Exit"
                ],
                carousel=True
            )
        ]
        main_answer = inquirer.prompt(main_menu)
        action = main_answer["action"]

        if "Movies" in action:
            # Movies submenu
            home = retry(idlix.get_home)
            
            if not home.get("status") or not home.get("featured_movie"):
                logger.error(f"Error fetching movies: {home.get('message')}")
                input("\nPress Enter to continue...")
                continue
            
            featured = home["featured_movie"]
            show_featured_table(featured, "🎬 Featured Movies")
            
            movie_menu = [
                inquirer.List(
                    "movie_action",
                    message="Select action",
                    choices=[
                        "▶️  Play Featured Movie",
                        "📥 Download Featured Movie",
                        "🔙 Back to Main Menu"
                    ],
                    carousel=True
                )
            ]
            movie_answer = inquirer.prompt(movie_menu)
            
            if "Back" in movie_answer["movie_action"]:
                continue
            
            # Select movie
            movie_choices = [f"{i+1}. {m['title']}" for i, m in enumerate(featured)]
            
            question = [
                inquirer.List(
                    "movie",
                    message="Select movie",
                    choices=movie_choices,
                    carousel=True
                )
            ]
            choice = inquirer.prompt(question)
            
            selected_idx = int(choice["movie"].split(".")[0]) - 1
            selected = featured[selected_idx]
            
            mode = "play" if "Play" in movie_answer["movie_action"] else "download"
            process_content(idlix, selected["url"], mode, is_episode=False)
            
            input("\nPress Enter to continue...")

        elif "TV Series" in action:
            # Series submenu
            series_menu = [
                inquirer.List(
                    "series_action",
                    message="TV Series options",
                    choices=[
                        "📺 Browse Featured Series",
                        "🔗 Enter Series/Episode URL",
                        "🔙 Back to Main Menu"
                    ],
                    carousel=True
                )
            ]
            series_answer = inquirer.prompt(series_menu)
            
            if "Back" in series_answer["series_action"]:
                continue
            
            if "Browse" in series_answer["series_action"]:
                featured_series = retry(idlix.get_featured_series)
                
                if not featured_series.get("status") or not featured_series.get("featured_series"):
                    logger.warning("No featured series found. Try entering URL manually.")
                    input("\nPress Enter to continue...")
                    continue
                
                series_list = featured_series["featured_series"]
                show_featured_table(series_list, "📺 Featured TV Series")
                
                play_download = [
                    inquirer.List(
                        "mode",
                        message="Select action",
                        choices=[
                            "▶️  Play Series",
                            "📥 Download Series",
                            "🔙 Back"
                        ],
                        carousel=True
                    )
                ]
                mode_answer = inquirer.prompt(play_download)
                
                if "Back" in mode_answer["mode"]:
                    continue
                
                # Select series
                series_choices = [f"{i+1}. {s['title']}" for i, s in enumerate(series_list)]
                
                question = [
                    inquirer.List(
                        "series",
                        message="Select series",
                        choices=series_choices,
                        carousel=True
                    )
                ]
                choice = inquirer.prompt(question)
                
                selected_idx = int(choice["series"].split(".")[0]) - 1
                selected = series_list[selected_idx]
                
                mode = "play" if "Play" in mode_answer["mode"] else "download"
                process_series(idlix, selected["url"], mode)
            else:
                # Enter URL manually
                print("\n📝 Supported URL formats:")
                print("   - Series:  https://tv12.idlixku.com/tvseries/series-name/")
                print("   - Episode: https://tv12.idlixku.com/episode/series-season-X-episode-Y/")
                
                url = input("\n🔗 Enter URL: ").strip()
                
                if not url:
                    continue
                
                mode_q = [
                    inquirer.List(
                        "mode",
                        message="Select action",
                        choices=["▶️  Play", "📥 Download"],
                        carousel=True
                    )
                ]
                mode = "play" if "Play" in inquirer.prompt(mode_q)["mode"] else "download"
                
                process_series(idlix, url, mode)
            
            input("\nPress Enter to continue...")

        elif "URL" in action:
            # Direct URL input
            print("\n📝 Enter any IDLIX URL (movie or episode):")
            url = input("🔗 URL: ").strip()
            
            if not url:
                continue
            
            mode_q = [
                inquirer.List(
                    "mode",
                    message="Select action",
                    choices=["▶️  Play", "📥 Download"],
                    carousel=True
                )
            ]
            mode = "play" if "Play" in inquirer.prompt(mode_q)["mode"] else "download"
            
            # Detect content type
            if '/episode/' in url:
                process_content(idlix, url, mode, is_episode=True)
            elif '/tvseries/' in url:
                process_series(idlix, url, mode)
            else:
                process_content(idlix, url, mode, is_episode=False)
            
            input("\nPress Enter to continue...")

        else:
            # Exit
            logger.info("👋 Goodbye!")
            status_exit = True


if __name__ == "__main__":
    main()
