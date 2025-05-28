import unittest
from unittest.mock import patch, MagicMock, call
import os
import tempfile
import shutil # For cleaning up non-empty directories if tempfile.TemporaryDirectory isn't used or fails

import requests # For requests.exceptions
# Ensure src modules can be imported
import sys
if __name__ == "__main__" or __package__ is None: # For running a single test file
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.core.downloader import Downloader, DownloadError
# In yt-dlp, DownloadError is a generic exception, but we are testing our wrapper's DownloadError
from yt_dlp.utils import DownloadError as YTDLP_DownloadError 


class TestDownloader(unittest.TestCase):
    def setUp(self):
        self.downloader = Downloader()
        # Create a temporary directory for downloads
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir = self.temp_dir_obj.name
        self.test_url = "https://www.youtube.com/watch?v=testvideo"

    def tearDown(self):
        # Cleanup the temporary directory
        self.temp_dir_obj.cleanup()

    @patch('src.core.downloader.yt_dlp.YoutubeDL')
    def test_successful_download(self, MockYoutubeDL):
        # Configure the mock YoutubeDL instance
        mock_ydl_instance = MockYoutubeDL.return_value.__enter__.return_value
        
        # Simulate that extract_info provides a filename and then download completes
        # The current Downloader directly calls download=True in extract_info
        # So, we primarily mock extract_info
        
        expected_title = "test_video_title"
        expected_ext = "mp4"
        expected_filename_in_info = f"{expected_title}.{expected_ext}"
        # This is the path yt-dlp would internally determine and use for the downloaded file
        full_expected_path = os.path.join(self.temp_dir, expected_filename_in_info)

        mock_info_dict = {
            'title': expected_title,
            'ext': expected_ext,
            'requested_downloads': [{'filepath': full_expected_path}], # Used by prepare_filename
            '_filename': full_expected_path, # Another fallback
            'filepath': full_expected_path, # General fallback
        }
        mock_ydl_instance.extract_info.return_value = mock_info_dict
        mock_ydl_instance.prepare_filename.return_value = full_expected_path

        # Simulate file creation by download
        def side_effect_download(*args, **kwargs):
            # Create the dummy file that download() would create
            os.makedirs(os.path.dirname(full_expected_path), exist_ok=True)
            with open(full_expected_path, 'w') as f:
                f.write("dummy video data")
            return mock_info_dict # extract_info (with download=True) returns info_dict
        
        mock_ydl_instance.extract_info.side_effect = side_effect_download

        # Call the download_media method
        downloaded_file = self.downloader.download_media(self.test_url, self.temp_dir)

        # Assertions
        mock_ydl_instance.extract_info.assert_called_once_with(self.test_url, download=True)
        self.assertEqual(downloaded_file, full_expected_path)
        self.assertTrue(os.path.exists(full_expected_path)) # Check if the dummy file was created

    @patch('src.core.downloader.yt_dlp.YoutubeDL')
    def test_download_failure_yt_dlp_error(self, MockYoutubeDL):
        mock_ydl_instance = MockYoutubeDL.return_value.__enter__.return_value
        # Configure the mock to raise YTDLP_DownloadError (from yt_dlp.utils)
        mock_ydl_instance.extract_info.side_effect = YTDLP_DownloadError("Simulated yt-dlp download error", YTDLP_DownloadError())

        with self.assertRaisesRegex(DownloadError, "yt-dlp download error: Simulated yt-dlp download error"):
            self.downloader.download_media(self.test_url, self.temp_dir)

    @patch('src.core.downloader.yt_dlp.YoutubeDL')
    def test_download_failure_generic_exception(self, MockYoutubeDL):
        mock_ydl_instance = MockYoutubeDL.return_value.__enter__.return_value
        # Configure the mock to raise a generic Exception
        mock_ydl_instance.extract_info.side_effect = Exception("Generic simulated error")

        with self.assertRaisesRegex(DownloadError, "An unexpected error occurred in downloader: Exception - Generic simulated error"):
            self.downloader.download_media(self.test_url, self.temp_dir)
            
    @patch('src.core.downloader.yt_dlp.YoutubeDL')
    def test_progress_hook_callback(self, MockYoutubeDL):
        mock_ydl_instance = MockYoutubeDL.return_value.__enter__.return_value
        mock_callback = MagicMock()

        expected_title = "progress_test_video"
        expected_ext = "mkv"
        expected_filename_in_info = f"{expected_title}.{expected_ext}"
        full_expected_path = os.path.join(self.temp_dir, expected_filename_in_info)

        # Simulate how the progress hook might be called by yt-dlp via ydl_opts
        # The hook is part of ydl_opts, so we need to capture those opts
        # and manually call our hook if we want to test its behavior directly.
        
        # The Downloader's _progress_hook is called by yt-dlp internally.
        # We need to simulate yt-dlp calling this hook.
        # The `extract_info` or `download` call in yt-dlp would trigger it.
        
        # Sample progress data
        progress_downloading = {
            'status': 'downloading', 
            'total_bytes': 1000, 
            'downloaded_bytes': 500, 
            'percentage': 50.0, 
            'speed': 100, 
            'eta': 5
        }
        progress_finished = {
            'status': 'finished', 
            'filename': full_expected_path,
            'total_bytes': 1000
        }

        def side_effect_extract_info_with_hook_call(url, download):
            # Simulate yt-dlp calling the hook
            # The hook is obtained from ydl_opts in the actual Downloader code.
            # We need to find the hook in the options passed to YoutubeDL constructor.
            
            # Get the ydl_opts that would be passed to YoutubeDL
            # This is a bit tricky as the opts are generated inside download_media
            # For this test, we can assume the hook is correctly set up in ydl_opts
            # and our Downloader._progress_hook will be called.
            
            # Let's simulate the Downloader's _progress_hook being called
            # by yt-dlp when extract_info (with download=True) is running.
            if self.downloader.progress_callback: # progress_callback is set in download_media
                 self.downloader._progress_hook(progress_downloading)
                 self.downloader._progress_hook(progress_finished)
            
            # Create the dummy file
            os.makedirs(os.path.dirname(full_expected_path), exist_ok=True)
            with open(full_expected_path, 'w') as f:
                f.write("dummy video data")

            return { # Standard info_dict returned by extract_info
                'title': expected_title, 'ext': expected_ext, 
                'requested_downloads': [{'filepath': full_expected_path}],
                '_filename': full_expected_path
            }

        mock_ydl_instance.extract_info.side_effect = side_effect_extract_info_with_hook_call
        mock_ydl_instance.prepare_filename.return_value = full_expected_path


        self.downloader.download_media(self.test_url, self.temp_dir, progress_callback=mock_callback)

        # Assertions
        # Check if the callback was called with the data we simulated
        calls = [
            call({'status': 'downloading', 'total_bytes': 1000, 'downloaded_bytes': 500, 'percentage': 50.0, 'speed': 100, 'eta': 5}),
            call({'status': 'finished', 'filename': full_expected_path, 'total_bytes': 1000})
        ]
        mock_callback.assert_has_calls(calls, any_order=False)
        self.assertEqual(mock_callback.call_count, 2)

    def test_file_already_exists(self, MockYoutubeDL): # Added MockYoutubeDL as it's used by @patch
        # This test is a bit more conceptual with the current Downloader structure,
        # as yt-dlp handles "already downloaded" internally.
        # Our Downloader's current logic for "already exists" is minimal:
        # it relies on `ydl.download([url])` to handle it if `extract_info(download=False)` was used.
        # Since we switched to `extract_info(download=True)`, yt-dlp itself
        # will typically report it as finished or skip redownloading.

        mock_ydl_instance = MockYoutubeDL.return_value.__enter__.return_value
        
        expected_title = "existing_video"
        expected_ext = "mp4"
        expected_filename = f"{expected_title}.{expected_ext}"
        full_expected_path = os.path.join(self.temp_dir, expected_filename)

        # Create the "existing" file
        os.makedirs(os.path.dirname(full_expected_path), exist_ok=True)
        with open(full_expected_path, 'w') as f:
            f.write("dummy data")

        # Simulate yt-dlp behavior when file exists:
        # It might still call the progress hook with 'finished' status.
        mock_info_dict = {
            'title': expected_title, 'ext': expected_ext,
            'filepath': full_expected_path, # yt-dlp might provide this
            '_filename': full_expected_path,
            # 'requested_downloads': [{'filepath': full_expected_path}], # Not always present if download=True and file exists
        }
        
        def side_effect_extract_info_existing(url, download):
            # If file exists, yt-dlp might not redownload but still provide info
            # and call the 'finished' hook.
            self.downloader._progress_hook({
                'status': 'finished', 
                'filename': full_expected_path,
                'total_bytes': os.path.getsize(full_expected_path)
            })
            return mock_info_dict

        mock_ydl_instance.extract_info.side_effect = side_effect_extract_info_existing
        mock_ydl_instance.prepare_filename.return_value = full_expected_path
        
        mock_cb = MagicMock()
        returned_path = self.downloader.download_media(self.test_url, self.temp_dir, progress_callback=mock_cb)

        self.assertEqual(returned_path, full_expected_path)
        # Check that extract_info was called (yt-dlp still checks metadata)
        mock_ydl_instance.extract_info.assert_called_once_with(self.test_url, download=True)
        
        # Check that the callback was notified of finish
        mock_cb.assert_called_once_with({
            'status': 'finished', 
            'filename': full_expected_path,
            'total_bytes': os.path.getsize(full_expected_path)
        })

    def test__is_direct_image_url(self):
        test_cases = [
            ("http://example.com/image.png", True),
            ("https://example.com/IMAGE.JPG", True),
            ("http://example.com/image.jpeg?query=param", True),
            ("http://example.com/image.gif", True),
            ("http://example.com/image.bmp", True),
            ("http://example.com/image.webp", True),
            ("http://example.com/document.pdf", False),
            ("https://youtube.com/watch?v=id", False),
            ("http://example.com/page", False),
            ("http://example.com/imagepng", False), # No dot
            ("http://example.com/image.pngg", False), # Wrong extension like .pngg
            ("http://example.com/archive.tar.gz", False),
            ("", False), # Empty string
            ("http://example.com/noextension/", False),
            ("http://example.com/.png", True), # Starts with dot, valid if server allows
        ]
        for url, expected_result in test_cases:
            with self.subTest(url=url):
                self.assertEqual(self.downloader._is_direct_image_url(url), expected_result)

    @patch('src.core.downloader.requests.get')
    def test_download_media_direct_image_success(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Disposition': 'attachment; filename="test_image.png"'
        }
        mock_response.iter_content.return_value = [b'fake', b'image', b'data']
        mock_requests_get.return_value = mock_response

        mock_progress_callback = MagicMock()
        image_url = "http://example.com/test_image.png"
        
        downloaded_filepath = self.downloader.download_media(
            image_url, 
            self.temp_dir, 
            progress_callback=mock_progress_callback
        )

        mock_requests_get.assert_called_once_with(image_url, stream=True, timeout=20)
        
        expected_filename = "test_image.png" # From Content-Disposition
        expected_filepath = os.path.join(self.temp_dir, expected_filename)
        self.assertEqual(downloaded_filepath, expected_filepath)
        self.assertTrue(os.path.exists(expected_filepath))

        with open(expected_filepath, 'rb') as f:
            content = f.read()
            self.assertEqual(content, b'fakeimagedata')

        expected_calls = [
            call({'status': 'downloading', 'message': 'Downloading image...', 'percentage': 0, 'total_bytes': 0}),
            call({'status': 'downloading', 'downloaded_bytes': 4, 'message': 'Downloading image...'}),
            call({'status': 'downloading', 'downloaded_bytes': 9, 'message': 'Downloading image...'}),
            call({'status': 'downloading', 'downloaded_bytes': 13, 'message': 'Downloading image...'}),
            call({'status': 'finished', 'filename': expected_filepath, 'total_bytes': 13})
        ]
        mock_progress_callback.assert_has_calls(expected_calls)

    @patch('src.core.downloader.requests.get')
    def test_download_media_direct_image_http_error(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found" # requests.Response uses 'reason'
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Client Error: Not Found for url", response=mock_response
        )
        mock_requests_get.return_value = mock_response
        
        mock_progress_callback = MagicMock()
        image_url = "http://example.com/notfound.png"

        with self.assertRaisesRegex(DownloadError, "Error downloading image: 404 Client Error: Not Found for url"):
            self.downloader.download_media(image_url, self.temp_dir, progress_callback=mock_progress_callback)

        mock_progress_callback.assert_any_call({
            'status': 'error', 
            'message': 'Error downloading image: 404 Client Error: Not Found for url'
        })

    @patch('src.core.downloader.requests.get')
    def test_download_media_direct_image_connection_error(self, mock_requests_get):
        mock_requests_get.side_effect = requests.exceptions.ConnectionError("Test connection error")
        
        mock_progress_callback = MagicMock()
        image_url = "http://example.com/networkissue.png"

        with self.assertRaisesRegex(DownloadError, "Error downloading image: Test connection error"):
            self.downloader.download_media(image_url, self.temp_dir, progress_callback=mock_progress_callback)
        
        mock_progress_callback.assert_any_call({
            'status': 'error',
            'message': 'Error downloading image: Test connection error'
        })

    @patch('src.core.downloader.requests.get')
    def test_download_image_filename_from_content_disposition_utf8(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Example from RFC 6266: filename*=UTF-8''%e2%82%ac%20exchange%20rate.pdf
        # Using a simpler name: test ä image.png (test%20%C3%A4%20image.png)
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Disposition': "attachment; filename*=UTF-8''test%20%C3%A4%20image.png"
        }
        mock_response.iter_content.return_value = [b'data']
        mock_requests_get.return_value = mock_response

        image_url = "http://example.com/image_with_utf8_name.png"
        downloaded_filepath = self.downloader.download_media(image_url, self.temp_dir, progress_callback=MagicMock())
        
        # The requests.utils.unquote should handle the UTF-8 decoding.
        # The filename sanitization in downloader is basic, so 'ä' might be stripped if not alnum.
        # Current sanitization: "".join(c for c in filename if c.isalnum() or c in ['.', '_', '-']).strip()
        # 'ä' is not alnum. So it will be stripped.
        # Let's test the expected outcome of current sanitization.
        # expected_filename = "test image.png" # Ideal if 'ä' was preserved and allowed
        expected_filename = "testimage.png" # Due to current sanitization stripping ' ' and 'ä'
        self.assertTrue(downloaded_filepath.endswith(expected_filename), f"Expected ends with {expected_filename}, got {downloaded_filepath}")

    @patch('src.core.downloader.requests.get')
    def test_download_image_filename_from_url_path(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'image/jpeg'} # No Content-Disposition
        mock_response.iter_content.return_value = [b'data']
        mock_requests_get.return_value = mock_response

        image_url = "http://example.com/path/to/url_filename.jpg?query=123"
        downloaded_filepath = self.downloader.download_media(image_url, self.temp_dir, progress_callback=MagicMock())
        expected_filename = "url_filename.jpg"
        self.assertTrue(downloaded_filepath.endswith(expected_filename),  f"Expected ends with {expected_filename}, got {downloaded_filepath}")

    @patch('src.core.downloader.requests.get')
    def test_download_image_filename_from_content_type(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'image/gif'} # No C-D, path has no extension
        mock_response.iter_content.return_value = [b'data']
        mock_requests_get.return_value = mock_response

        image_url = "http://example.com/nodisposition/noextensioninsurl"
        downloaded_filepath = self.downloader.download_media(image_url, self.temp_dir, progress_callback=MagicMock())
        expected_filename = "image.gif" # Default name "image" + ext from Content-Type
        self.assertTrue(downloaded_filepath.endswith(expected_filename), f"Expected ends with {expected_filename}, got {downloaded_filepath}")

    @patch('src.core.downloader.requests.get')
    def test_download_image_filename_fallback_default(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {} # No C-D, no Content-Type that helps with extension
        mock_response.iter_content.return_value = [b'data']
        mock_requests_get.return_value = mock_response

        image_url = "http://example.com/someservice/resource" # Path gives no extension
        downloaded_filepath = self.downloader.download_media(image_url, self.temp_dir, progress_callback=MagicMock())
        # Fallback logic: "image" + ".jpg" (if path has no ext) or "image" + path_ext
        expected_filename = "image.jpg" 
        self.assertTrue(downloaded_filepath.endswith(expected_filename), f"Expected ends with {expected_filename}, got {downloaded_filepath}")

    @patch('src.core.downloader.requests.get')
    def test_download_image_filename_sanitization(self, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'image/png',
            'Content-Disposition': 'attachment; filename="im@g<e> file name.png"'
        }
        mock_response.iter_content.return_value = [b'data']
        mock_requests_get.return_value = mock_response

        image_url = "http://example.com/image_to_be_sanitized.png"
        downloaded_filepath = self.downloader.download_media(image_url, self.temp_dir, progress_callback=MagicMock())
        
        # Current sanitization: "".join(c for c in filename if c.isalnum() or c in ['.', '_', '-']).strip()
        # "im@g<e> file name.png" -> "imgefilename.png"
        expected_filename_ending = "imgefilename.png"
        self.assertTrue(downloaded_filepath.endswith(expected_filename_ending), f"Expected ends with {expected_filename_ending}, got {downloaded_filepath}")

    @patch('src.core.downloader.requests.get')
    def test_download_image_unique_filename(self, mock_requests_get):
        # First download
        mock_response1 = MagicMock()
        mock_response1.status_code = 200
        mock_response1.headers = {'Content-Disposition': 'filename="unique_test.png"'}
        mock_response1.iter_content.return_value = [b'data1']
        
        # Second download, requests.get will be called again
        mock_response2 = MagicMock()
        mock_response2.status_code = 200
        mock_response2.headers = {'Content-Disposition': 'filename="unique_test.png"'} # Same original name
        mock_response2.iter_content.return_value = [b'data2']

        # Configure mock_requests_get to return different responses for sequential calls
        mock_requests_get.side_effect = [mock_response1, mock_response2]

        image_url = "http://example.com/unique_test.png"
        
        # Download first time
        filepath1 = self.downloader.download_media(image_url, self.temp_dir, progress_callback=MagicMock())
        self.assertTrue(filepath1.endswith("unique_test.png"))
        self.assertTrue(os.path.exists(filepath1))
        with open(filepath1, 'rb') as f: self.assertEqual(f.read(), b'data1')

        # Download second time (should get unique name)
        filepath2 = self.downloader.download_media(image_url, self.temp_dir, progress_callback=MagicMock())
        self.assertTrue(filepath2.endswith("unique_test_1.png")) # _get_unique_filepath appends _1
        self.assertTrue(os.path.exists(filepath2))
        with open(filepath2, 'rb') as f: self.assertEqual(f.read(), b'data2')
        
        self.assertEqual(mock_requests_get.call_count, 2)


# Need to add the patch decorator to test_file_already_exists if it's standalone
TestDownloader.test_file_already_exists = patch('src.core.downloader.yt_dlp.YoutubeDL')(TestDownloader.test_file_already_exists)

if __name__ == '__main__':
    unittest.main()
```
