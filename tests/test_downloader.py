import unittest
from unittest.mock import patch, MagicMock, call
import os
import tempfile
import shutil # For cleaning up non-empty directories if tempfile.TemporaryDirectory isn't used or fails

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

# Need to add the patch decorator to test_file_already_exists if it's standalone
TestDownloader.test_file_already_exists = patch('src.core.downloader.yt_dlp.YoutubeDL')(TestDownloader.test_file_already_exists)

if __name__ == '__main__':
    unittest.main()
```
