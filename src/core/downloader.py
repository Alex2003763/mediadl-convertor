import yt_dlp
import os

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
        
        self.last_ydl_opts = ydl_opts.copy()

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info) if info else None
                if not filename:
                    raise DownloadError("Could not determine filename, possibly due to an issue with URL or initial processing.")
            
            if not os.path.exists(filename):
                base, _ = os.path.splitext(filename)
                possible_files = [f for f in os.listdir(download_path) if f.startswith(os.path.basename(base))]
                if possible_files:
                    filename = os.path.join(download_path, possible_files[0])
                if not os.path.exists(filename):
                    raise DownloadError(f"File not found after download and postprocessing: {filename}")
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
```
