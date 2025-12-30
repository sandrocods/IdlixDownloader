import unittest
import os
from unittest.mock import MagicMock, patch
from src.idlixHelper import IdlixHelper

class TestIdlixHelper(unittest.TestCase):
    def setUp(self):
        self.helper = IdlixHelper()
        self.helper.video_name = "Test Movie: Subtitle & More!"
        self.helper.request = MagicMock()

    def test_get_safe_title(self):
        """Verify sanitization of filenames"""
        safe = self.helper.get_safe_title()
        # Should remove : and & (and others) and replace spaces with _
        self.assertNotIn(":", safe)
        self.assertNotIn("&", safe)
        self.assertEqual(safe, "Test_Movie_Subtitle__More!")

    def test_set_m3u8_url_relative(self):
        """Verify relative URL expansion"""
        self.helper.set_m3u8_url("/stream.m3u8")
        self.assertEqual(self.helper.m3u8_url, "https://jeniusplay.com/stream.m3u8")

    def test_set_m3u8_url_absolute(self):
        """Verify absolute URL is kept"""
        url = "https://jeniusplay.com/ext.m3u8"
        self.helper.set_m3u8_url(url)
        self.assertEqual(self.helper.m3u8_url, url)

    @patch('src.idlixHelper.ConvertFile')
    def test_convert_vtt_to_srt(self, mock_convert):
        """Test if vtt_to_srt is called with correct arguments"""
        self.helper.convert_vtt_to_srt("dummy.vtt")
        mock_convert.assert_called_once_with("dummy.vtt", "utf-8")
        mock_convert.return_value.convert.assert_called_once()

    @patch('src.idlixHelper.requests.get')
    def test_get_subtitle_failure(self, mock_get):
        """Test subtitle retrieval failure handling"""
        # Mocking empty response for embed_url which results in no subtitle found
        self.helper.embed_url = None
        result = self.helper.get_subtitle()
        self.assertFalse(result['status'])
        self.assertEqual(result['message'], 'Embed URL is required')

    def test_get_home_success(self):
        """Test get_home with successful response"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        # HTML with valid href structure (at least 4 segments)
        html_content = """
        <div class="items featured">
            <article class="item">
                <div class="poster">
                    <img src="http://img.url/poster.jpg" alt="Movie Title">
                    <div class="rating">8.5</div>
                    <div class="mepo">
                         <a href="https://tv12.idlixku.com/movie/movie-title"></a>
                    </div>
                </div>
                <div class="data">
                    <h3><a href="https://tv12.idlixku.com/movie/movie-title">Movie Title</a></h3>
                    <span>2023</span>
                </div>
            </article>
        </div>
        """
        mock_response.text = html_content
        self.helper.request.get.return_value = mock_response

        result = self.helper.get_home()
        
        self.assertTrue(result['status'])
        self.assertEqual(len(result['featured_movie']), 1)
        self.assertEqual(result['featured_movie'][0]['title'], "Movie Title")
        self.assertEqual(result['featured_movie'][0]['url'], "https://tv12.idlixku.com/movie/movie-title")

    def test_get_video_data_success(self):
        """Test get_video_data with successful response"""
        url = "https://tv12.idlixku.com/movie/test-movie"
        mock_response = MagicMock()
        mock_response.status_code = 200
        # HTML with video ID, name, and poster meta tags
        html_content = """
        <meta id="dooplay-ajax-counter" data-postid="12345">
        <meta itemprop="name" content="Test Movie">
        <img itemprop="image" src="http://img.url/poster.jpg">
        """
        mock_response.text = html_content
        self.helper.request.get.return_value = mock_response

        result = self.helper.get_video_data(url)
        
        self.assertTrue(result['status'])
        self.assertEqual(result['video_id'], "12345")
        self.assertEqual(result['video_name'], "Test Movie")

    @patch('src.idlixHelper.CryptoJsAes.decrypt')
    @patch('src.idlixHelper.dec')
    def test_get_embed_url_success(self, mock_dec, mock_decrypt):
        """Test get_embed_url with successful response"""
        self.helper.video_id = "12345"
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Mock response json
        mock_response.json.return_value = {
            "embed_url": '{"m": "dummy_m"}', # Needs to be json loadable for 'm' extraction
            "key": "dummy_key"
        }
        self.helper.request.post.return_value = mock_response
        
        # Mock decryption results
        mock_dec.return_value = "passphrase"
        mock_decrypt.return_value = "https://jeniusplay.com/player/index.php?data=hash123&do=getVideo"

        result = self.helper.get_embed_url()
        
        self.assertTrue(result['status'])
        self.assertIn("jeniusplay.com", result['embed_url'])

    @patch('src.idlixHelper.m3u8')
    def test_get_m3u8_url_success(self, mock_m3u8):
        """Test get_m3u8_url with successful response"""
        # Set embed_url to something that parses correctly
        self.helper.embed_url = "https://jeniusplay.com/player/index.php?data=hash123"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "videoSource": "https://server.com/playlist.m3u8"
        }
        self.helper.request.post.return_value = mock_response
        
        # Mock m3u8 loading
        mock_playlist = MagicMock()
        mock_playlist.playlists = [] # No variants for this simple test
        mock_m3u8.load.return_value = mock_playlist

        result = self.helper.get_m3u8_url()
        
        self.assertTrue(result['status'])
        self.assertEqual(result['m3u8_url'], "https://server.com/playlist.m3u8")

if __name__ == '__main__':
    unittest.main()
