"""
Unit Tests for Progress Callback and Cancel Functionality
Tests: progress_callback system, cancel_flag handling
"""
import unittest
from unittest.mock import MagicMock, patch
from src.idlixHelper import IdlixHelper


class TestProgressCallback(unittest.TestCase):
    """Test progress callback system"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.helper = IdlixHelper()
        self.progress_updates = []
        
        def mock_callback(percent, status=""):
            self.progress_updates.append({'percent': percent, 'status': status})
        
        self.helper.progress_callback = mock_callback
    
    def test_progress_callback_is_called(self):
        """Test that progress_callback is invoked during download"""
        # This test simulates what happens during m3u8_To_MP4 download
        # We can't fully test download without network, but we can test the callback mechanism
        
        # Simulate progress updates
        if self.helper.progress_callback:
            self.helper.progress_callback(10.5, "1.5/15.0 MB")
            self.helper.progress_callback(50.0, "7.5/15.0 MB")
            self.helper.progress_callback(100.0, "15.0/15.0 MB")
        
        self.assertEqual(len(self.progress_updates), 3)
        self.assertEqual(self.progress_updates[0]['percent'], 10.5)
        self.assertEqual(self.progress_updates[1]['percent'], 50.0)
        self.assertEqual(self.progress_updates[2]['percent'], 100.0)
    
    def test_progress_callback_with_no_callback_set(self):
        """Test that code doesn't crash when no callback is set"""
        self.helper.progress_callback = None
        
        # This should not raise an error
        try:
            if self.helper.progress_callback:
                self.helper.progress_callback(50, "test")
            success = True
        except:
            success = False
        
        self.assertTrue(success)
    
    def test_cancel_flag_initial_state(self):
        """Test that cancel_flag starts as False"""
        self.assertFalse(self.helper.cancel_flag)
    
    def test_cancel_flag_can_be_set(self):
        """Test that cancel_flag can be set to True"""
        self.helper.cancel_flag = False
        self.helper.cancel_flag = True
        self.assertTrue(self.helper.cancel_flag)
    
    @patch('src.idlixHelper.m3u8_To_MP4.multithread_download')
    @patch('src.idlixHelper.os.makedirs')
    @patch('src.idlixHelper.shutil.rmtree')
    def test_download_respects_cancel_flag_before_start(self, mock_rmtree, mock_makedirs, mock_download):
        """Test that download checks cancel_flag before starting"""
        self.helper.m3u8_url = "https://example.com/video.m3u8"
        self.helper.video_name = "Test Video"
        self.helper.cancel_flag = True  # Set before download
        
        result = self.helper.download_m3u8()
        
        # Should return cancelled status
        self.assertFalse(result['status'])
        self.assertIn('cancelled', result['message'].lower())
        
        # download_m3u8 should not have been called
        mock_download.assert_not_called()


class TestSubtitleModeHandling(unittest.TestCase):
    """Test subtitle mode setting and behavior"""
    
    def setUp(self):
        """Setup test fixtures"""
        self.helper = IdlixHelper()
    
    def test_set_subtitle_mode_separate(self):
        """Test setting subtitle mode to 'separate'"""
        self.helper.set_subtitle_mode('separate')
        self.assertEqual(self.helper.subtitle_mode, 'separate')
    
    def test_set_subtitle_mode_softcode(self):
        """Test setting subtitle mode to 'softcode'"""
        self.helper.set_subtitle_mode('softcode')
        self.assertEqual(self.helper.subtitle_mode, 'softcode')
    
    def test_set_subtitle_mode_hardcode(self):
        """Test setting subtitle mode to 'hardcode'"""
        self.helper.set_subtitle_mode('hardcode')
        self.assertEqual(self.helper.subtitle_mode, 'hardcode')
    
    def test_default_subtitle_mode(self):
        """Test default subtitle mode is 'separate'"""
        mode = getattr(self.helper, 'subtitle_mode', 'separate')
        self.assertEqual(mode, 'separate')
    
    def test_set_skip_subtitle_true(self):
        """Test setting skip_subtitle flag"""
        self.helper.set_skip_subtitle(True)
        self.assertTrue(self.helper.skip_subtitle)
    
    def test_set_skip_subtitle_false(self):
        """Test clearing skip_subtitle flag"""
        self.helper.set_skip_subtitle(False)
        self.assertFalse(self.helper.skip_subtitle)
    
    def test_skip_subtitle_default_state(self):
        """Test skip_subtitle starts as False"""
        self.assertFalse(self.helper.skip_subtitle)


class TestMultiSubtitleSupport(unittest.TestCase):
    """Test multi-subtitle selection and download"""
    
    def test_subtitle_storage_structure(self):
        """Test that subtitle list is properly initialized"""
        helper = IdlixHelper()
        self.assertEqual(helper.subtitles, [])
        self.assertIsNone(helper.selected_subtitle)
        self.assertFalse(helper.skip_subtitle)
    
    def test_subtitle_selection_flow(self):
        """Test subtitle selection workflow"""
        helper = IdlixHelper()
        
        # Manually set subtitles (as if get_available_subtitles() was called)
        helper.subtitles = [
            {'id': '0', 'label': 'Indonesian', 'url': 'https://sub.com/id.vtt'},
            {'id': '1', 'label': 'English', 'url': 'https://sub.com/en.vtt'}
        ]
        
        # Select subtitle
        helper.selected_subtitle = helper.subtitles[1]
        
        self.assertEqual(helper.selected_subtitle['id'], '1')
        self.assertEqual(helper.selected_subtitle['label'], 'English')
    
    @patch('src.idlixHelper.os.remove')
    @patch('src.idlixHelper.IdlixHelper.convert_vtt_to_srt')
    @patch('src.idlixHelper.requests.get')
    def test_download_selected_subtitle_by_id(self, mock_get, mock_convert, mock_remove):
        """Test downloading specific subtitle by ID"""
        helper = IdlixHelper()
        helper.subtitles = [
            {'id': '0', 'label': 'Indonesian', 'url': 'https://sub.com/id.vtt'},
            {'id': '1', 'label': 'English', 'url': 'https://sub.com/en.vtt'}
        ]
        helper.video_name = "Test_Movie"
        
        mock_response = MagicMock()
        mock_response.content = b"VTT subtitle content"
        mock_get.return_value = mock_response
        
        result = helper.download_selected_subtitle('1')  # Select English
        
        self.assertTrue(result['status'])
        self.assertEqual(result['label'], 'English')
        self.assertIn('English', result['subtitle'])
        mock_get.assert_called_once_with(url='https://sub.com/en.vtt')
    
    @patch('src.idlixHelper.os.remove')
    @patch('src.idlixHelper.IdlixHelper.convert_vtt_to_srt')
    @patch('src.idlixHelper.requests.get')
    def test_download_selected_subtitle_default_first(self, mock_get, mock_convert, mock_remove):
        """Test downloading first subtitle when no ID specified"""
        helper = IdlixHelper()
        helper.subtitles = [
            {'id': '0', 'label': 'Indonesian', 'url': 'https://sub.com/id.vtt'}
        ]
        helper.video_name = "Test_Movie"
        
        mock_response = MagicMock()
        mock_response.content = b"VTT subtitle content"
        mock_get.return_value = mock_response
        
        result = helper.download_selected_subtitle(None)  # None = first available
        
        self.assertTrue(result['status'])
        self.assertEqual(result['label'], 'Indonesian')


if __name__ == '__main__':
    unittest.main()
