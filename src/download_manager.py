"""
Unified Download Manager - Single source of truth for download logic
Digunakan oleh GUI dan CLI untuk konsistensi

Author: sandroputraa
"""

import time
from loguru import logger


class DownloadManager:
    """Manages the complete download workflow"""
    
    RETRY_LIMIT = 3
    
    @staticmethod
    def _retry_operation(func, *args, **kwargs):
        """Internal retry wrapper for operations that return dict with 'status' key"""
        for attempt in range(DownloadManager.RETRY_LIMIT):
            try:
                result = func(*args, **kwargs)
                if result and result.get("status"):
                    return result
            except Exception as e:
                logger.warning(f"Operation failed: {e}")
            
            if attempt < DownloadManager.RETRY_LIMIT - 1:
                logger.warning(f"Retry {attempt + 1}/{DownloadManager.RETRY_LIMIT}...")
                time.sleep(1)
        
        return {"status": False, "message": "Maximum retry reached"}
    
    @staticmethod
    def prepare_movie_download(idlix_helper, url):
        """
        Prepare movie for download - get all metadata
        Returns: (video_data, embed_url, m3u8_data) or None if error
        """
        # Get video data with retry
        video_data = DownloadManager._retry_operation(idlix_helper.get_video_data, url)
        if not video_data.get("status"):
            logger.error("Error getting video data")
            return None
        
        logger.info(f"📽️  {video_data['video_name']}")
        
        # Get embed URL with retry
        embed = DownloadManager._retry_operation(idlix_helper.get_embed_url)
        if not embed.get("status"):
            logger.error("Error getting embed URL")
            return None
        
        logger.success("Embed URL obtained")
        
        # Get M3U8 URL with retry
        m3u8 = DownloadManager._retry_operation(idlix_helper.get_m3u8_url)
        if not m3u8.get("status"):
            logger.error("Error getting M3U8 URL")
            return None
        
        logger.success("M3U8 URL obtained")
        
        return (video_data, embed, m3u8)
    
    @staticmethod
    def prepare_episode_download(idlix_helper, url, episode_info=None):
        """
        Prepare episode for download - get all metadata
        episode_info: dict with series_title, series_year, season_num, episode_num
        Returns: (video_data, embed_url, m3u8_data) or None if error
        """
        # Get episode data with retry
        video_data = DownloadManager._retry_operation(idlix_helper.get_episode_data, url)
        if not video_data.get("status"):
            logger.error("Error getting episode data")
            return None
        
        logger.info(f"📺 {video_data['video_name']}")
        
        # Set episode metadata for organized folder structure
        if episode_info:
            idlix_helper.set_episode_meta(
                series_title=episode_info.get('series_title', 'Unknown'),
                series_year=episode_info.get('series_year', '2025'),
                season_num=episode_info.get('season_num', 1),
                episode_num=episode_info.get('episode_num', 1)
            )
        
        # Get embed URL (type=tv for episodes) with retry
        embed = DownloadManager._retry_operation(idlix_helper.get_embed_url_episode)
        if not embed.get("status"):
            logger.error("Error getting embed URL")
            return None
        
        logger.success("Embed URL obtained")
        
        # Get M3U8 URL with retry
        m3u8 = DownloadManager._retry_operation(idlix_helper.get_m3u8_url)
        if not m3u8.get("status"):
            logger.error("Error getting M3U8 URL")
            return None
        
        logger.success("M3U8 URL obtained")
        
        return (video_data, embed, m3u8)
    
    @staticmethod
    def execute_download(idlix_helper, video_data, resolution_id=None, subtitle_id=None, subtitle_mode='separate'):
        """
        Execute download with selected options
        
        Args:
            idlix_helper: IdlixHelper instance
            video_data: Video metadata
            resolution_id: Selected resolution ID (None = use default)
            subtitle_id: Selected subtitle ID (None = no subtitle, "" = skip)
            subtitle_mode: 'separate', 'softcode', or 'hardcode'
        
        Returns:
            dict with status and message
        """
        # Handle subtitle
        subtitle_file = None
        if subtitle_id is None:
            # Auto-download subtitle (check if available)
            logger.info("Checking for subtitles...")
            subs_result = idlix_helper.get_available_subtitles()
            if subs_result.get("status") and subs_result.get("subtitles"):
                # Download first available subtitle
                first_sub = subs_result["subtitles"][0]
                sub_result = idlix_helper.download_selected_subtitle(first_sub["id"])
                if sub_result.get("status"):
                    subtitle_file = sub_result.get("subtitle")
                    logger.success(f"Subtitle auto-downloaded: {sub_result.get('label')}")
                    # Set subtitle mode
                    idlix_helper.set_subtitle_mode(subtitle_mode)
                    logger.info(f"Subtitle mode: {subtitle_mode}")
            else:
                logger.info("No subtitles available")
        elif subtitle_id == "":
            # User explicitly chose "No Subtitle"
            idlix_helper.set_skip_subtitle(True)
            logger.info("Subtitle skipped (user choice)")
        else:
            # Download selected subtitle
            sub_result = idlix_helper.download_selected_subtitle(subtitle_id)
            if sub_result.get("status"):
                subtitle_file = sub_result.get("subtitle")
                logger.success(f"Subtitle downloaded: {sub_result.get('label')}")
                
                # Set subtitle mode
                idlix_helper.set_subtitle_mode(subtitle_mode)
                logger.info(f"Subtitle mode: {subtitle_mode}")
        
        # Download
        logger.info("Starting download...")
        result = idlix_helper.download_m3u8()
        
        if result.get("status"):
            logger.success(f"✅ Downloaded: {video_data['video_name']}")
            return {'status': True, 'path': result.get('path')}
        else:
            logger.error(f"Download failed: {result.get('message')}")
            return {'status': False, 'message': result.get('message')}
