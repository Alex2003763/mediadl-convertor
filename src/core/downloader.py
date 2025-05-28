import yt_dlp
import os
import requests # For direct image downloads
from urllib.parse import urlparse # For parsing URL to get filename
import re # For parsing Content-Disposition header

class DownloadError(Exception):
    """Custom exception for download errors."""
    pass

class Downloader:
    def __init__(self):
        self.progress_callback = None
        self.last_ydl_opts = None # For testing/inspection

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
                    'speed': speed if speed is not None else 0, 
                    'eta': eta if eta is not None else 0 
                })
            else: 
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

    def _get_unique_filepath(self, filepath):
        """Ensures a unique filepath by appending a number if the file already exists."""
        if not os.path.exists(filepath):
            return filepath
        base, ext = os.path.splitext(filepath)
        i = 1
        while True:
            new_filepath = f"{base}_{i}{ext}"
            if not os.path.exists(new_filepath):
                return new_filepath
            i += 1

    def _is_direct_image_url(self, url: str) -> bool:
        """
        Checks if a URL likely points to a direct image based on its extension.
        Case-insensitive.
        """
        image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')
        parsed_url = urlparse(url)
        path = parsed_url.path.lower()
        return any(path.endswith(ext) for ext in image_extensions)

    def download_media(self, url: str, download_path: str, preferred_format_info=None, progress_callback=None) -> str:
        self.progress_callback = progress_callback
        os.makedirs(download_path, exist_ok=True)

        ydl_opts = {
            'outtmpl': os.path.join(download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'nocheckcertificate': True,
            'quiet': True, 
            'no_warnings': True,
            'noplaylist': True, 
        }

        # Clear any format-specific options that might linger if not set by current logic
        ydl_opts.pop('merge_output_format', None)
        ydl_opts.pop('postprocessors', None)
        ydl_opts.pop('extract_audio', None)
        ydl_opts.pop('audio_format', None)
        
        p_format_id = None
        if preferred_format_info and preferred_format_info.get('format_id'):
            p_format_id = preferred_format_info['format_id'].lower()

        if p_format_id == 'mp4':
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/best[ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
        elif p_format_id == 'webm':
            ydl_opts['format'] = 'bestvideo[ext=webm]+bestaudio[ext=webm]/best[ext=webm]/best'
            ydl_opts['merge_output_format'] = 'webm'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'webm'}]
        elif p_format_id == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['extract_audio'] = True
            ydl_opts['audio_format'] = 'mp3'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192', 
            }]
            ydl_opts.pop('merge_output_format', None) 
        elif p_format_id is not None: 
            # Fallback for other formats (avi, mov, wav etc.) -> download high-quality MP4 as source.
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/best[ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'
            ydl_opts['postprocessors'] = [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
        else: 
            # True default: preferred_format_info is None or has no format_id.
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            # No specific merge or postprocessors for format conversion needed here.

        if not progress_callback:
            ydl_opts['quiet'] = False 
        
        self.last_ydl_opts = ydl_opts.copy() # For yt-dlp, clear if not used

        if self._is_direct_image_url(url):
            if self.progress_callback:
                self.progress_callback({'status': 'downloading', 'message': 'Downloading image...', 'percentage': 0, 'total_bytes': 0}) # Initial progress
            
            try:
                response = requests.get(url, stream=True, timeout=20) # Increased timeout
                response.raise_for_status()

                # Determine filename
                filename = None
                content_disposition = response.headers.get('content-disposition')
                if content_disposition:
                    # Example: "attachment; filename="image.jpg""
                    # Using regex to find filename*= or filename=
                    fn_match = re.search(r'filename\*?=(?:UTF-8\'\')?([^;]+)', content_disposition, flags=re.IGNORECASE)
                    if fn_match:
                        filename = requests.utils.unquote(fn_match.group(1)).strip('"')
                
                if not filename:
                    parsed_url = urlparse(url)
                    filename = os.path.basename(parsed_url.path)
                
                if not filename: # Still no filename
                    # Use a default name, try to get extension from Content-Type
                    content_type = response.headers.get('content-type')
                    ext = '.jpg' # Default extension
                    if content_type and content_type.startswith('image/'):
                        guessed_ext = content_type.split('/')[1].split(';')[0] # e.g. jpeg from image/jpeg; charset=UTF-8
                        if guessed_ext:
                            ext = '.' + guessed_ext.lower()
                    filename = "image" + ext
                
                # Sanitize filename (basic)
                filename = "".join(c for c in filename if c.isalnum() or c in ['.', '_', '-']).strip()
                if not filename: # If sanitization results in empty string
                     filename = "downloaded_image" + os.path.splitext(urlparse(url).path)[-1] or ".jpg"


                filepath = os.path.join(download_path, filename)
                filepath = self._get_unique_filepath(filepath)

                total_downloaded = 0
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        total_downloaded += len(chunk)
                        if self.progress_callback: # Optional: update progress per chunk
                             self.progress_callback({'status': 'downloading', 'downloaded_bytes': total_downloaded, 'message': 'Downloading image...'})


                if self.progress_callback:
                    self.progress_callback({
                        'status': 'finished',
                        'filename': filepath,
                        'total_bytes': total_downloaded,
                    })
                return filepath

            except requests.exceptions.RequestException as e:
                error_message = f"Error downloading image: {str(e)}"
                if self.progress_callback:
                    self.progress_callback({'status': 'error', 'message': error_message})
                raise DownloadError(error_message)
            except Exception as e: # Catch any other unexpected errors during image download
                error_message = f"Unexpected error downloading image: {type(e).__name__} - {str(e)}"
                if self.progress_callback:
                     self.progress_callback({'status': 'error', 'message': error_message})
                raise DownloadError(error_message)
        else: # Existing yt-dlp logic
            self.last_ydl_opts = ydl_opts.copy() # Store for testing if it's a yt-dlp download
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info) if info else None
                    if not filename:
                        # Attempt to find the file if title is used and extension changed by postprocessor
                        if info and 'title' in info and 'ext' in info:
                             temp_fn_base = ydl.prepare_filename(info, outtmpl='%(title)s')
                             # Common postprocessed extensions for audio
                             possible_postprocessed_exts = ['.mp3', '.m4a', '.ogg', '.wav', '.flac'] 
                             if p_format_id and p_format_id in possible_postprocessed_exts:
                                 filename_candidate = f"{temp_fn_base}.{p_format_id}"
                                 if os.path.exists(filename_candidate):
                                     filename = filename_candidate

                        if not filename: # If still not found
                            raise DownloadError("Could not determine filename after yt-dlp processing.")
                
                # Check if file exists, sometimes postprocessing might change filename slightly or it might not be reported back correctly
                if not os.path.exists(filename):
                    # yt-dlp might save with a different extension due to format conversion not reflected in `filename`
                    # Example: asking for mp3, yt-dlp downloads .webm then converts. `filename` might still be .webm
                    # We need to find the actual output file.
                    # This is a simplified check; robust checking is complex.
                    # For now, assume the main post-processed file should be what we asked for or what yt-dlp reports.
                    # A more robust way would be to list files in download_path and find the newest one matching the title.
                    
                    # If a specific audio format was requested, check for that.
                    if ydl_opts.get('extract_audio') and ydl_opts.get('audio_format'):
                        base, _ = os.path.splitext(filename)
                        expected_filename = f"{base}.{ydl_opts['audio_format']}"
                        if os.path.exists(expected_filename):
                            filename = expected_filename
                    
                    # If still not found, try to find any file matching the base name (title)
                    if not os.path.exists(filename):
                        base_original_filename = os.path.basename(ydl.prepare_filename(info, outtmpl='%(title)s.%(ext)s') if info else "unknown")
                        base_title = os.path.splitext(base_original_filename)[0]
                        possible_files = [f for f in os.listdir(download_path) if f.startswith(base_title)]
                        if possible_files:
                            # Sort by modification time if multiple, take newest, or just first for simplicity
                            filename = os.path.join(download_path, possible_files[0]) 
                
                if not os.path.exists(filename): # Final check
                    raise DownloadError(f"File not found after download and postprocessing attempts: {filename}")
                return filename
            except yt_dlp.utils.DownloadError as e:
                err_str = str(e).lower()
                if "is not a valid url" in err_str or "unsupported url" in err_str:
                    raise DownloadError(f"Invalid or unsupported URL: {url}. Original error: {e}")
                elif "ffmpeg is not installed" in err_str:
                     raise DownloadError(f"FFmpeg not found. It's required for merging or format conversion. Original error: {e}")
                raise DownloadError(f"yt-dlp download error: {e}")
            except Exception as e:
                raise DownloadError(f"Unexpected error in downloader: {type(e).__name__} - {e}")

if __name__ == "__main__":
    downloader = Downloader()
    test_url = "https://www.youtube.com/watch?v=C0DPdy98e4c" 
    download_directory = "assets/downloads_test" 
    os.makedirs(download_directory, exist_ok=True)

    if os.path.exists(download_directory):
        for item in os.listdir(download_directory):
            item_path = os.path.join(download_directory, item)
            if os.path.isfile(item_path):
                try:
                    os.remove(item_path)
                except OSError as e:
                    print(f"Warning: Could not remove file {item_path} during cleanup: {e}")
    
    def console_progress_callback(progress_data):
        if progress_data['status'] == 'downloading':
            print(f"TestCB: DLing {progress_data.get('percentage',0):.1f}%")
        elif progress_data['status'] == 'finished':
            fn = progress_data.get('filename','')
            if fn: 
                print(f"TestCB: Finished {os.path.basename(fn)}")
            else:
                print("TestCB: Finished (filename not provided in hook data)")

    try:
        print(f"\n--- Test 1: Default (preferred_format_info=None) -> Best quality, yt-dlp decides container ---")
        file_def = downloader.download_media(url=test_url, download_path=download_directory, preferred_format_info=None, progress_callback=console_progress_callback)
        print(f"Default DL to: {os.path.basename(file_def)}")
        print(f"  Opts: format='{downloader.last_ydl_opts.get('format')}', merge='{downloader.last_ydl_opts.get('merge_output_format')}', postprocs={downloader.last_ydl_opts.get('postprocessors')}, extract_audio={downloader.last_ydl_opts.get('extract_audio')}")
        assert os.path.exists(file_def)
        assert downloader.last_ydl_opts.get('format') == 'bestvideo+bestaudio/best'
        assert 'merge_output_format' not in downloader.last_ydl_opts 
        assert 'postprocessors' not in downloader.last_ydl_opts 
        assert 'extract_audio' not in downloader.last_ydl_opts 
        if os.path.exists(file_def): os.remove(file_def)

        print(f"\n--- Test 2: Preferred MP4 ---")
        file_mp4 = downloader.download_media(url=test_url, download_path=download_directory, preferred_format_info={'format_id': 'mp4'}, progress_callback=console_progress_callback)
        print(f"MP4 DL to: {os.path.basename(file_mp4)}")
        print(f"  Opts: format='{downloader.last_ydl_opts.get('format')}', merge='{downloader.last_ydl_opts.get('merge_output_format')}', postprocs={downloader.last_ydl_opts.get('postprocessors')}")
        assert os.path.exists(file_mp4) and file_mp4.lower().endswith(".mp4")
        assert 'bestvideo[ext=mp4]' in downloader.last_ydl_opts.get('format', '')
        assert downloader.last_ydl_opts.get('merge_output_format') == 'mp4'
        assert downloader.last_ydl_opts.get('postprocessors') == [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
        if os.path.exists(file_mp4): os.remove(file_mp4)

        print(f"\n--- Test 3: Preferred WebM (no callback -> quiet=False) ---")
        file_webm = downloader.download_media(url=test_url, download_path=download_directory, preferred_format_info={'format_id': 'webm'}, progress_callback=None)
        print(f"WebM DL to: {os.path.basename(file_webm)}")
        print(f"  Opts: format='{downloader.last_ydl_opts.get('format')}', merge='{downloader.last_ydl_opts.get('merge_output_format')}', postprocs={downloader.last_ydl_opts.get('postprocessors')}, quiet={downloader.last_ydl_opts.get('quiet')}")
        assert os.path.exists(file_webm) and file_webm.lower().endswith(".webm")
        assert '[ext=webm]' in downloader.last_ydl_opts.get('format', '') 
        assert downloader.last_ydl_opts.get('merge_output_format') == 'webm'
        assert downloader.last_ydl_opts.get('postprocessors') == [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'webm'}]
        assert downloader.last_ydl_opts.get('quiet') == False
        if os.path.exists(file_webm): os.remove(file_webm)

        print(f"\n--- Test 4: Preferred MP3 (audio extraction) ---")
        file_mp3 = downloader.download_media(url=test_url, download_path=download_directory, preferred_format_info={'format_id': 'mp3'}, progress_callback=console_progress_callback)
        print(f"MP3 DL to: {os.path.basename(file_mp3)}")
        print(f"  Opts: format='{downloader.last_ydl_opts.get('format')}', extract_audio={downloader.last_ydl_opts.get('extract_audio')}, audio_fmt='{downloader.last_ydl_opts.get('audio_format')}', postprocs={downloader.last_ydl_opts.get('postprocessors')}")
        assert os.path.exists(file_mp3) and file_mp3.lower().endswith(".mp3")
        assert downloader.last_ydl_opts.get('format') == 'bestaudio/best'
        assert downloader.last_ydl_opts.get('extract_audio') == True
        assert downloader.last_ydl_opts.get('audio_format') == 'mp3'
        assert downloader.last_ydl_opts.get('postprocessors') == [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
        assert 'merge_output_format' not in downloader.last_ydl_opts 
        if os.path.exists(file_mp3): os.remove(file_mp3)

        print(f"\n--- Test 5: Preferred AVI (fallback to MP4 source) ---")
        file_avi_src = downloader.download_media(url=test_url, download_path=download_directory, preferred_format_info={'format_id': 'avi'}, progress_callback=console_progress_callback)
        print(f"AVI source (MP4) DL to: {os.path.basename(file_avi_src)}")
        print(f"  Opts: format='{downloader.last_ydl_opts.get('format')}', merge='{downloader.last_ydl_opts.get('merge_output_format')}', postprocs={downloader.last_ydl_opts.get('postprocessors')}")
        assert os.path.exists(file_avi_src) and file_avi_src.lower().endswith(".mp4") 
        assert 'bestvideo[ext=mp4]' in downloader.last_ydl_opts.get('format', '') 
        assert downloader.last_ydl_opts.get('merge_output_format') == 'mp4'
        assert downloader.last_ydl_opts.get('postprocessors') == [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}]
        if os.path.exists(file_avi_src): os.remove(file_avi_src)

        print("\n--- Test 6: Invalid URL ---")
        invalid_url = "htp://invalid.url.thisdoesnotexist"
        try:
            downloader.download_media(url=invalid_url, download_path=download_directory, preferred_format_info=None)
        except DownloadError as e:
            print(f"Correctly caught DownloadError for invalid URL: {e}")

    except DownloadError as e:
        print(f"A DL test failed: {e}")
    except Exception as e:
        print(f"Unexpected error in main: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(download_directory): 
            for item in os.listdir(download_directory):
                 item_path = os.path.join(download_directory, item)
                 if os.path.isfile(item_path):
                    try:
                        os.remove(item_path)
                    except OSError as e:
                         print(f"Warning: Could not remove file {item_path} during final cleanup: {e}")
            try:
                if not os.listdir(download_directory): 
                     os.rmdir(download_directory)
                else:
                     print(f"Warning: Test download directory {download_directory} not empty, not removing.")
            except OSError as e:
                print(f"Warning: Could not remove directory {download_directory}: {e}")
        print("\nTests finished.")

