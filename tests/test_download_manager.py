"""
Unit Tests for DownloadManager
Tests: prepare methods, execute_download, auto-download subtitle, progress callback
"""
import unittest
from unittest.mock import MagicMock, patch, call
from src.download_manager import DownloadManager
from src.idlixHelper import IdlixHelper


class TestDownloadManager(unittest.TestCase):
    """Test DownloadManager business logic"""
    
    def setUp(self):
        """Setup common test fixtures"""
        self.mock_helper = MagicMock(spec=IdlixHelper)
        self.test_url = "https://tv12.idlixku.com/movie/test-movie/"
        
        # Mock successful video data
        self.video_data = {
            'status': True,
            'video_id': '12345',
            'video_name': 'Test Movie',
            'poster': 'http://example.com/poster.jpg'
        }
        
        # Mock successful embed URL
        self.embed_data = {
            'status': True,
            'embed_url': 'https://jeniusplay.com/player/index.php?data=hash123'
        }
        
        # Mock successful m3u8 data with variants
        self.m3u8_data = {
            'status': True,
            'm3u8_url': 'https://server.com/playlist.m3u8',
            'variant_playlist': [
                {'id': '0', 'resolution': '720x480', 'bandwidth': 1000000, 'uri': '/720p.m3u8'},
                {'id': '1', 'resolution': '1280x720', 'bandwidth': 2000000, 'uri': '/1080p.m3u8'}
            ],
            'is_variant_playlist': True
        }
        
        # Mock subtitle data
        self.subtitles_data = {
            'status': True,
            'subtitles': [
                {'id': '0', 'label': 'Indonesian', 'url': 'https://sub.com/id.vtt'},
                {'id': '1', 'label': 'English', 'url': 'https://sub.com/en.vtt'}
            ],
            'count': 2
        }
    
    def test_retry_operation_success_first_try(self):
        """Test _retry_operation succeeds on first attempt"""
        mock_func = MagicMock(return_value={'status': True, 'data': 'success'})
        
        result = DownloadManager._retry_operation(mock_func, 'arg1', kwarg1='value1')
        
        self.assertTrue(result['status'])
        self.assertEqual(result['data'], 'success')
        self.assertEqual(mock_func.call_count, 1)
        mock_func.assert_called_once_with('arg1', kwarg1='value1')
    
    def test_retry_operation_success_after_retries(self):
        """Test _retry_operation succeeds after multiple retries"""
        # First 2 calls fail, 3rd succeeds
        mock_func = MagicMock(side_effect=[
            {'status': False, 'message': 'fail1'},
            {'status': False, 'message': 'fail2'},
            {'status': True, 'data': 'success'}
        ])
        
        result = DownloadManager._retry_operation(mock_func)
        
        self.assertTrue(result['status'])
        self.assertEqual(mock_func.call_count, 3)
    
    def test_retry_operation_max_retries_exceeded(self):
        """Test _retry_operation fails after max retries"""
        mock_func = MagicMock(return_value={'status': False, 'message': 'always fail'})
        
        result = DownloadManager._retry_operation(mock_func)
        
        self.assertFalse(result['status'])
        self.assertIn('Maximum retry reached', result['message'])
        self.assertEqual(mock_func.call_count, 3)
    
    def test_prepare_movie_download_success(self):
        """Test prepare_movie_download returns all necessary data"""
        self.mock_helper.get_video_data.return_value = self.video_data
        self.mock_helper.get_embed_url.return_value = self.embed_data
        self.mock_helper.get_m3u8_url.return_value = self.m3u8_data
        
        result = DownloadManager.prepare_movie_download(self.mock_helper, self.test_url)
        
        self.assertIsNotNone(result)
        video_data, embed, m3u8 = result
        self.assertEqual(video_data['video_id'], '12345')
        self.assertEqual(embed['embed_url'], self.embed_data['embed_url'])
        self.assertEqual(m3u8['m3u8_url'], self.m3u8_data['m3u8_url'])
        
        # Verify call sequence
        self.mock_helper.get_video_data.assert_called_once_with(self.test_url)
        self.mock_helper.get_embed_url.assert_called_once()
        self.mock_helper.get_m3u8_url.assert_called_once()
    
    def test_prepare_movie_download_failure_at_video_data(self):
        """Test prepare_movie_download handles failure at video data step"""
        self.mock_helper.get_video_data.return_value = {'status': False, 'message': 'Not found'}
        
        result = DownloadManager.prepare_movie_download(self.mock_helper, self.test_url)
        
        self.assertIsNone(result)
        self.mock_helper.get_video_data.assert_called()
        self.mock_helper.get_embed_url.assert_not_called()
    
    def test_prepare_episode_download_success(self):
        """Test prepare_episode_download with episode metadata"""
        episode_url = "https://tv12.idlixku.com/episode/vikings-season-1-episode-1/"
        episode_info = {
            'series_title': 'Vikings',
            'series_year': '2020',
            'season_num': 1,
            'episode_num': 1
        }
        
        self.mock_helper.get_episode_data.return_value = self.video_data
        self.mock_helper.get_embed_url_episode.return_value = self.embed_data
        self.mock_helper.get_m3u8_url.return_value = self.m3u8_data
        
        result = DownloadManager.prepare_episode_download(self.mock_helper, episode_url, episode_info)
        
        self.assertIsNotNone(result)
        video_data, embed, m3u8 = result
        
        # Verify episode metadata was set
        self.mock_helper.set_episode_meta.assert_called_once_with(
            series_title='Vikings', series_year='2020', season_num=1, episode_num=1
        )
        self.mock_helper.get_episode_data.assert_called_once_with(episode_url)
        self.mock_helper.get_embed_url_episode.assert_called_once()
    
    def test_prepare_episode_download_without_metadata(self):
        """Test prepare_episode_download works without episode metadata"""
        episode_url = "https://tv12.idlixku.com/episode/test-ep/"
        
        self.mock_helper.get_episode_data.return_value = self.video_data
        self.mock_helper.get_embed_url_episode.return_value = self.embed_data
        self.mock_helper.get_m3u8_url.return_value = self.m3u8_data
        
        result = DownloadManager.prepare_episode_download(self.mock_helper, episode_url, episode_info=None)
        
        self.assertIsNotNone(result)
        self.mock_helper.set_episode_meta.assert_not_called()
    
    def test_execute_download_auto_subtitle_success(self):
        """Test execute_download auto-downloads subtitle when subtitle_id is None"""
        self.mock_helper.get_available_subtitles.return_value = self.subtitles_data
        self.mock_helper.download_selected_subtitle.return_value = {
            'status': True,
            'subtitle': 'test_movie_Indonesian.srt',
            'label': 'Indonesian'
        }
        self.mock_helper.download_m3u8.return_value = {
            'status': True,
            'path': 'test_movie.mp4'
        }
        
        result = DownloadManager.execute_download(
            self.mock_helper, 
            self.video_data, 
            subtitle_id=None,  # Auto-download
            subtitle_mode='separate'
        )
        
        self.assertTrue(result['status'])
        self.mock_helper.get_available_subtitles.assert_called_once()
        self.mock_helper.download_selected_subtitle.assert_called_once_with('0')  # First subtitle
        self.mock_helper.set_subtitle_mode.assert_called_once_with('separate')
    
    def test_execute_download_auto_subtitle_no_subtitles_available(self):
        """Test execute_download handles no subtitles available gracefully"""
        self.mock_helper.get_available_subtitles.return_value = {
            'status': False,
            'message': 'No subtitles found'
        }
        self.mock_helper.download_m3u8.return_value = {
            'status': True,
            'path': 'test_movie.mp4'
        }
        
        result = DownloadManager.execute_download(
            self.mock_helper,
            self.video_data,
            subtitle_id=None
        )
        
        self.assertTrue(result['status'])
        self.mock_helper.get_available_subtitles.assert_called_once()
        self.mock_helper.download_selected_subtitle.assert_not_called()
        self.mock_helper.download_m3u8.assert_called_once()
    
    def test_execute_download_skip_subtitle_explicit(self):
        """Test execute_download skips subtitle when subtitle_id is empty string"""
        self.mock_helper.download_m3u8.return_value = {
            'status': True,
            'path': 'test_movie.mp4'
        }
        
        result = DownloadManager.execute_download(
            self.mock_helper,
            self.video_data,
            subtitle_id=""  # Explicit skip
        )
        
        self.assertTrue(result['status'])
        self.mock_helper.set_skip_subtitle.assert_called_once_with(True)
        self.mock_helper.get_available_subtitles.assert_not_called()
        self.mock_helper.download_selected_subtitle.assert_not_called()
    
    def test_execute_download_specific_subtitle(self):
        """Test execute_download downloads specific subtitle by ID"""
        self.mock_helper.download_selected_subtitle.return_value = {
            'status': True,
            'subtitle': 'test_movie_English.srt',
            'label': 'English'
        }
        self.mock_helper.download_m3u8.return_value = {
            'status': True,
            'path': 'test_movie.mp4'
        }
        
        result = DownloadManager.execute_download(
            self.mock_helper,
            self.video_data,
            subtitle_id="1",  # Specific subtitle
            subtitle_mode='softcode'
        )
        
        self.assertTrue(result['status'])
        self.mock_helper.download_selected_subtitle.assert_called_once_with("1")
        self.mock_helper.set_subtitle_mode.assert_called_once_with('softcode')
    
    def test_execute_download_subtitle_modes(self):
        """Test execute_download sets correct subtitle mode"""
        self.mock_helper.download_selected_subtitle.return_value = {
            'status': True,
            'subtitle': 'test.srt',
            'label': 'Test'
        }
        self.mock_helper.download_m3u8.return_value = {'status': True, 'path': 'test.mp4'}
        
        # Test all three modes
        for mode in ['separate', 'softcode', 'hardcode']:
            self.mock_helper.reset_mock()
            
            result = DownloadManager.execute_download(
                self.mock_helper,
                self.video_data,
                subtitle_id="0",
                subtitle_mode=mode
            )
            
            self.assertTrue(result['status'])
            self.mock_helper.set_subtitle_mode.assert_called_once_with(mode)
    
    def test_execute_download_failure(self):
        """Test execute_download handles download failure"""
        self.mock_helper.download_m3u8.return_value = {
            'status': False,
            'message': 'Network error'
        }
        
        result = DownloadManager.execute_download(
            self.mock_helper,
            self.video_data,
            subtitle_id=""
        )
        
        self.assertFalse(result['status'])
        self.assertIn('Network error', result['message'])
    
    def test_execute_download_with_resolution_selection(self):
        """Test execute_download doesn't interfere with resolution (set before call)"""
        self.mock_helper.download_m3u8.return_value = {'status': True, 'path': 'test.mp4'}
        
        result = DownloadManager.execute_download(
            self.mock_helper,
            self.video_data,
            resolution_id="1",  # This is used before execute_download in actual code
            subtitle_id=""
        )
        
        self.assertTrue(result['status'])
        # Resolution is handled by caller (set_m3u8_url), not by execute_download


class TestDownloadManagerIntegration(unittest.TestCase):
    """Integration tests with real IdlixHelper behavior patterns"""
    
    def test_full_movie_workflow(self):
        """Test complete movie download workflow"""
        mock_helper = MagicMock(spec=IdlixHelper)
        
        # Setup complete workflow
        mock_helper.get_video_data.return_value = {'status': True, 'video_id': '123', 'video_name': 'Test'}
        mock_helper.get_embed_url.return_value = {'status': True, 'embed_url': 'https://embed.url'}
        mock_helper.get_m3u8_url.return_value = {'status': True, 'm3u8_url': 'https://m3u8.url'}
        mock_helper.get_available_subtitles.return_value = {
            'status': True,
            'subtitles': [{'id': '0', 'label': 'Indonesian', 'url': 'https://sub.url'}]
        }
        mock_helper.download_selected_subtitle.return_value = {'status': True, 'subtitle': 'test.srt', 'label': 'Indonesian'}
        mock_helper.download_m3u8.return_value = {'status': True, 'path': 'test.mp4'}
        
        # Execute workflow
        prepare_result = DownloadManager.prepare_movie_download(mock_helper, 'https://movie.url')
        self.assertIsNotNone(prepare_result)
        
        video_data, embed, m3u8 = prepare_result
        
        download_result = DownloadManager.execute_download(
            mock_helper, video_data, subtitle_id=None, subtitle_mode='separate'
        )
        
        self.assertTrue(download_result['status'])
        self.assertEqual(download_result['path'], 'test.mp4')
        
        # Verify complete call sequence
        mock_helper.get_video_data.assert_called_once()
        mock_helper.get_embed_url.assert_called_once()
        mock_helper.get_m3u8_url.assert_called_once()
        mock_helper.get_available_subtitles.assert_called_once()
        mock_helper.download_selected_subtitle.assert_called_once()
        mock_helper.download_m3u8.assert_called_once()
    
    def test_full_episode_workflow_with_metadata(self):
        """Test complete episode download workflow with organized folders"""
        mock_helper = MagicMock(spec=IdlixHelper)
        
        # Setup episode workflow
        mock_helper.get_episode_data.return_value = {'status': True, 'video_id': '456', 'video_name': 'Vikings S01E01'}
        mock_helper.get_embed_url_episode.return_value = {'status': True, 'embed_url': 'https://embed.url'}
        mock_helper.get_m3u8_url.return_value = {'status': True, 'm3u8_url': 'https://m3u8.url'}
        mock_helper.download_m3u8.return_value = {'status': True, 'path': 'Vikings (2020)/Season 01/Vikings - s01e01.mp4'}
        
        episode_info = {
            'series_title': 'Vikings',
            'series_year': '2020',
            'season_num': 1,
            'episode_num': 1
        }
        
        # Execute workflow
        prepare_result = DownloadManager.prepare_episode_download(
            mock_helper, 'https://episode.url', episode_info
        )
        self.assertIsNotNone(prepare_result)
        
        video_data, embed, m3u8 = prepare_result
        
        download_result = DownloadManager.execute_download(
            mock_helper, video_data, subtitle_id=""  # Skip subtitle
        )
        
        self.assertTrue(download_result['status'])
        
        # Verify episode metadata was set
        mock_helper.set_episode_meta.assert_called_once_with(
            series_title='Vikings', series_year='2020', season_num=1, episode_num=1
        )
        mock_helper.set_skip_subtitle.assert_called_once_with(True)


if __name__ == '__main__':
    unittest.main()
