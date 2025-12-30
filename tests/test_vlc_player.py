import unittest
from unittest.mock import MagicMock, patch
import tkinter as tk
import os

# We mock vlc before importing VLCPlayerWindow to avoid dependency issues during headless test
import sys
mock_vlc = MagicMock()
sys.modules['vlc'] = mock_vlc

from src.vlc_player import VLCPlayerWindow

class TestVLCPlayerLogic(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()
        
        # Mock idlix helper
        self.mock_idlix = MagicMock()
        self.mock_idlix.request.headers = {"User-Agent": "TestAgent"}
        self.mock_idlix.request.cookies.get_dict.return_value = {"session": "123"}
        self.mock_idlix.BASE_STATIC_HEADERS = {"Referer": "http://ref.com"}
        
        # Patching methods that interact with hardware/vlc instance directly
        with patch.object(VLCPlayerWindow, 'start_playback'), \
             patch.object(VLCPlayerWindow, 'update_ui'), \
             patch.object(VLCPlayerWindow, 'focus_force'):
            self.player = VLCPlayerWindow(self.root, self.mock_idlix, "http://stream.m3u8", title="Unit Test Player")

    def tearDown(self):
        self.root.destroy()

    def test_sync_subtitle_logic(self):
        """Test spu_delay calculation and label update"""
        # Initially 0
        self.assertEqual(self.player.spu_delay, 0)
        
        # Simulate pressing 'H' (+50ms = 50000us)
        self.player.sync_subtitle(50000)
        self.assertEqual(self.player.spu_delay, 50000)
        self.assertIn("50ms", self.player.sub_label.cget("text"))
        
        # Simulate pressing 'G' (-50ms)
        self.player.sync_subtitle(-50000)
        self.assertEqual(self.player.spu_delay, 0)
        self.assertIn("0ms", self.player.sub_label.cget("text"))

    def test_volume_relative(self):
        """Test relative volume bounds"""
        self.player.player.audio_get_volume.return_value = 50
        
        # +5
        self.player.volume_relative(5)
        self.player.player.audio_set_volume.assert_called_with(55)
        
        # Try to go over 100
        self.player.player.audio_get_volume.return_value = 98
        self.player.volume_relative(10)
        self.player.player.audio_set_volume.assert_called_with(100)

    def test_toggle_play(self):
        """Test play/pause toggle"""
        # Initial state is playing (from setUp/init)
        self.player.player.is_playing.return_value = 1 # True
        
        self.player.toggle_play()
        self.player.player.pause.assert_called_once()
        self.assertEqual(self.player.btn_play.cget("text"), "Play")
        
        # Toggle back
        self.player.player.is_playing.return_value = 0 # False
        self.player.toggle_play()
        self.player.player.play.assert_called()
        self.assertEqual(self.player.btn_play.cget("text"), "Pause")

    def test_seek_relative(self):
        """Test seeking relative to current time"""
        self.player.player.get_length.return_value = 10000 # 10s
        self.player.player.get_time.return_value = 5000 # 5s
        
        # Seek +5s
        self.player.seek_relative(5000)
        self.player.player.set_time.assert_called_with(10000)
        
        # Seek -2s
        self.player.player.get_time.return_value = 5000
        self.player.seek_relative(-2000)
        self.player.player.set_time.assert_called_with(3000)

    def test_on_close(self):
        """Test cleanup on close"""
        self.player.subtitle = "test.srt"
        with patch('os.remove') as mock_remove, \
             patch('os.path.exists', return_value=True):
            
            self.player.on_close()
            
            self.player.player.stop.assert_called_once()
            self.player.player.release.assert_called_once()
            mock_remove.assert_any_call("test.srt")

if __name__ == '__main__':
    unittest.main()
