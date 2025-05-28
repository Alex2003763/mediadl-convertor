import yt_dlp
import os

class DownloadError(Exception):
    """Custom exception for download errors."""
    pass

class Downloader:
    def __init__(self):
        self.progress_callback = None

    def _progress_hook(self, d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            speed = d.get('speed', 0)
            eta = d.get('eta', 0)
            percentage = 0
            if total_bytes > 0:
                percentage = (downloaded_bytes / total_bytes) * 100
            
            speed_str = f"{speed:.2f} B/s" if speed is not None else "N/A"
            eta_str = f"{eta}s" if eta is not None else "N/A"

            if self.progress_callback:
                self.progress_callback({
                    'status': 'downloading',
                    'total_bytes': total_bytes,
                    'downloaded_bytes': downloaded_bytes,
                    'percentage': percentage,
                    'speed': speed if speed is not None else 0, # bytes/sec
                    'eta': eta if eta is not None else 0 # seconds
                })
            else: # Default console output if no callback
                print(f"Downloading: {percentage:.2f}% of {total_bytes or 'Unknown'} bytes at {speed_str}, ETA: {eta_str}")

        elif d['status'] == 'finished':
            filename = d.get('filename')
            final_filesize = d.get('total_bytes', d.get('info_dict', {}).get('filesize'))
            if not final_filesize and filename and os.path.exists(filename):
                final_filesize = os.path.getsize(filename)

            if self.progress_callback:
                self.progress_callback({
                    'status': 'finished',
                    'filename': filename,
                    'total_bytes': final_filesize or 0,
                })
            else:
                print(f"Download finished: {filename}")
        
        elif d['status'] == 'error':
            if self.progress_callback:
                self.progress_callback({'status': 'error', 'message': 'Error during yt-dlp hook processing.'})
            else:
                print("Error during download (reported by hook).")


    def download_media(self, url: str, download_path: str, progress_callback=None) -> str:
        """
        Downloads media from the given URL to the specified path.

        Args:
            url: The URL of the media to download.
            download_path: The directory where the media should be saved.
            progress_callback: An optional function to call with progress updates.
                               The callback will receive a dictionary with progress info.

        Returns:
            The full path to the downloaded file.

        Raises:
            DownloadError: If any error occurs during the download process.
        """
        self.progress_callback = progress_callback
        
        # Ensure download path exists
        os.makedirs(download_path, exist_ok=True)

        ydl_opts = {
            'format': 'bestvideo+bestaudio/best', # Download best quality video and audio
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'), # Save in download_path
            'progress_hooks': [self._progress_hook],
            'nocheckcertificate': True, # Sometimes useful for avoiding SSL issues with certain sites
            # 'quiet': True, # Suppress yt-dlp direct console output if we have a callback. Keep it false for now for debugging.
            'noplaylist': True, # Download only single video if URL is part of a playlist
            'merge_output_format': None, # if format is 'best', yt-dlp handles merge to default (mkv/mp4)
        }
        
        # If there's a progress callback, we can be quiet. Otherwise, let yt-dlp print some info.
        # For now, keeping quiet=False to see all yt-dlp output during debugging.
        if progress_callback:
            ydl_opts['quiet'] = True # Be quiet if we have a callback
        else:
            ydl_opts['quiet'] = False # Show yt-dlp native output if no callback


        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True) # Download directly
                
                filename = ydl.prepare_filename(info) if info else None

                if not filename: # If, for some reason, prepare_filename failed or info was None
                    # This part is tricky as yt-dlp might have downloaded something without full info dict
                    # Or it might have failed before even getting info.
                    # We need to rely on the hook for 'finished' status or error.
                    # If the hook reported finished, it should have provided the filename.
                    # If an error occurred, it should be caught by the exception handlers.
                    # This is a fallback, but might not always work.
                    # Look for files in the download_path that might have been downloaded
                    # This is not robust. Best to rely on yt-dlp's info.
                    # For now, if filename is None after download, it's an issue.
                    raise DownloadError("Could not determine filename after download process.")

            # The hook should have updated status to 'finished' and provided filename
            # If we are here, and an exception wasn't raised, it means ydl.download completed.
            # The filename is taken from ydl.prepare_filename(info)
            
            # Verify file existence based on the prepared filename
            if not os.path.exists(filename):
                # It's possible the 'outtmpl' resulted in a different extension after merge
                # Let's try to find the file if the extension is different (e.g. webm -> mkv)
                base, _ = os.path.splitext(filename)
                possible_files = [f for f in os.listdir(download_path) if f.startswith(os.path.basename(base))]
                if possible_files:
                    filename = os.path.join(download_path, possible_files[0])
                
                if not os.path.exists(filename): # Check again
                    raise DownloadError(f"File not found after download attempt: {filename}. It might be an issue with filename generation or the download itself.")

            return filename
        
        except yt_dlp.utils.DownloadError as e:
            err_str = str(e).lower()
            if "is not a valid url" in err_str or "unsupported url" in err_str:
                raise DownloadError(f"Invalid or unsupported URL: {url}. Original error: {e}")
            elif "ffmpeg is not installed" in err_str:
                 raise DownloadError(f"FFmpeg not found. It's required for merging formats. Please install FFmpeg. Original error: {e}")
            # Add more specific error checks here as needed
            raise DownloadError(f"yt-dlp download error: {e}")
        except Exception as e:
            # Catching generic Exception to provide more context if it's not a DownloadError
            raise DownloadError(f"An unexpected error occurred in downloader: {type(e).__name__} - {e}")

if __name__ == "__main__":
    downloader = Downloader()
    
    # Example URL (Creative Commons): Big Buck Bunny - quite large
    # test_url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ" 
    # Using a shorter, smaller Creative Commons video for quicker tests
    test_url = "https://www.youtube.com/watch?v=C0DPdy98e4c" # LEGO Star Wars Stop Motion (CC) 2min
    # test_url = "https://commons.wikimedia.org/wiki/File:Example.ogv" # Very short OGV video

    download_directory = "assets/downloads"
    os.makedirs(download_directory, exist_ok=True)


    def console_progress_callback(progress_data):
        if progress_data['status'] == 'downloading':
            speed_val = progress_data.get('speed', 0) or 0
            eta_val = progress_data.get('eta', 0) or 0
            total_bytes_val = progress_data.get('total_bytes',0) or 0
            percentage_val = progress_data.get('percentage', 0) or 0

            print(f"Status: {progress_data['status']}, "
                  f"{percentage_val:.2f}% of {total_bytes_val}B, "
                  f"Speed: {speed_val:.2f} B/s, ETA: {eta_val}s")
        elif progress_data['status'] == 'finished':
            print(f"Status: {progress_data['status']}, File: {progress_data.get('filename')}")
            print(f"Downloaded to: {progress_data.get('filename')}")
        elif progress_data['status'] == 'error':
            print(f"Status: error during download. Message: {progress_data.get('message')}")

    print(f"Attempting to download: {test_url} to {download_directory}")
    
    # Clean up previous downloads of the test video to ensure fresh download
    # This is a bit simplistic; assumes yt-dlp default naming for this URL.
    # A more robust cleanup would parse the title from the URL or a preliminary info extraction.
    # For now, let's try to remove potential variations.
    expected_title_part = "LEGO Star Wars Stop Motion" 
    for item in os.listdir(download_directory):
        if expected_title_part in item:
            try:
                os.remove(os.path.join(download_directory, item))
                print(f"Removed old test file: {item}")
            except OSError as e:
                print(f"Error removing old test file {item}: {e}")


    try:
        print("\n--- Test with console_progress_callback ---")
        downloaded_file_path = downloader.download_media(test_url, download_directory, progress_callback=console_progress_callback)
        print(f"Successfully downloaded (with callback): {downloaded_file_path}")
        assert os.path.exists(downloaded_file_path), f"File {downloaded_file_path} does not exist after download."

        print("\n--- Test with internal printing (no callback) ---")
        # To ensure it downloads again and tests the 'already downloaded path', we'd ideally rename or delete
        # For simplicity in this test, we'll let it be potentially skipped by yt-dlp if not cleaned,
        # but the goal is to test the internal printing path.
        # A better test would use a different URL or ensure cleanup.
        # For now, let's assume the previous cleanup was sufficient or yt-dlp handles re-download/skip.
        
        # To force re-download for testing internal print, remove the previously downloaded file
        if os.path.exists(downloaded_file_path):
             os.remove(downloaded_file_path)
             print(f"Removed {downloaded_file_path} for the second test run.")

        downloaded_file_path_no_cb = downloader.download_media(test_url, download_directory) # No callback
        print(f"Successfully downloaded (no callback): {downloaded_file_path_no_cb}")
        assert os.path.exists(downloaded_file_path_no_cb), f"File {downloaded_file_path_no_cb} does not exist after download."

        print("\n--- Test with an invalid URL ---")
        invalid_url = "htp://invalid.url.thisdoesnotexist"
        try:
            downloader.download_media(invalid_url, download_directory, progress_callback=console_progress_callback)
        except DownloadError as e:
            print(f"Correctly caught DownloadError for invalid URL: {e}")
        
        print("\n--- Test with a (likely) unsupported URL type ---")
        unsupported_url = "https://www.google.com" # Not a media page
        try:
            downloader.download_media(unsupported_url, download_directory, progress_callback=console_progress_callback)
        except DownloadError as e:
            print(f"Correctly caught DownloadError for non-media URL: {e}")


    except DownloadError as e:
        print(f"\nDownload failed: {e}")
    except Exception as e:
        print(f"\nAn unexpected error in main: {type(e).__name__} - {e}")
