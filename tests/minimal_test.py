import sys
import os
import tempfile
import subprocess
import shutil

# Add src directory to sys.path to allow importing Downloader
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.downloader import Downloader, DownloadError

# Test URL
TEST_URL = "https://www.youtube.com/watch?v=rokGy0huYEA" # Sprite Fright

def progress_printer(data):
    print(f"MINIMAL_TEST_PROGRESS: {data}")

def run_minimal_test():
    temp_dir = None # Initialize to None for robust cleanup
    print("MINIMAL_TEST_SCRIPT_STARTED")
    try:
        temp_dir = tempfile.mkdtemp(prefix="min_test_")
        print(f"MINIMAL_TEST_TEMP_DIR_CREATED: {temp_dir}")
        
        downloader = Downloader()
        file_path = None
        
        print(f"MINIMAL_TEST_STARTING_DOWNLOAD: {TEST_URL}")
        file_path = downloader.download_media(
            TEST_URL,
            temp_dir,
            preferred_format_info={'format_id': 'mp4'},
            progress_callback=progress_printer
        )
        
        if file_path and os.path.exists(file_path):
            print(f"MINIMAL_TEST_DOWNLOAD_SUCCESS_PATH: {file_path}")
            if file_path.lower().endswith('.mp4'):
                print("MINIMAL_TEST_EXTENSION_CHECK: MP4_Correct")
            else:
                print(f"MINIMAL_TEST_EXTENSION_CHECK: MP4_Incorrect (Got {os.path.splitext(file_path)[1]})")
            
            # Basic FFmpeg check (optional for minimal, but good to include)
            print(f"MINIMAL_TEST_FFMPEG_CHECK_STARTING: {file_path}")
            try:
                result = subprocess.run(
                    ['ffmpeg', '-v', 'error', '-i', file_path, '-f', 'null', '-'],
                    capture_output=True, text=True, check=False
                )
                if result.returncode == 0 and not result.stderr.strip():
                    print(f"MINIMAL_TEST_FFMPEG_CHECK_SUCCESS: {file_path} appears valid.")
                else:
                    print(f"MINIMAL_TEST_FFMPEG_CHECK_FAILURE: {file_path} - FFmpeg stderr: {result.stderr.strip()} (Code: {result.returncode})")
            except FileNotFoundError:
                print("MINIMAL_TEST_FFMPEG_CHECK_ERROR: ffmpeg command not found.")
            except Exception as e_ffmpeg:
                print(f"MINIMAL_TEST_FFMPEG_CHECK_ERROR: Exception: {e_ffmpeg}")

        else:
            print(f"MINIMAL_TEST_DOWNLOAD_FAILURE: No file path returned ('{file_path}') or file does not exist.")

    except DownloadError as de:
        print(f"MINIMAL_TEST_DOWNLOAD_ERROR: {de}")
    except Exception as e:
        print(f"MINIMAL_TEST_UNEXPECTED_ERROR: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"MINIMAL_TEST_CLEANUP_ATTEMPT: {temp_dir}")
        try:
            if temp_dir and os.path.exists(temp_dir): 
                shutil.rmtree(temp_dir)
                print(f"MINIMAL_TEST_TEMP_DIR_REMOVED: {temp_dir}")
            else:
                print("MINIMAL_TEST_TEMP_DIR_NOT_FOUND_OR_NOT_CREATED")
        except Exception as e:
            print(f"MINIMAL_TEST_ERROR_REMOVING_TEMP_DIR: {temp_dir} - {e}")
    print("MINIMAL_TEST_SCRIPT_FINISHED")

if __name__ == "__main__":
    run_minimal_test()
```
