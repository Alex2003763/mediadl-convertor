import sys
import os
import tempfile
import subprocess
import shutil

# Add src directory to sys.path to allow importing Downloader
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.core.downloader import Downloader, DownloadError

# Test URLs
TEST_URLS = [
    "https://www.youtube.com/watch?v=rokGy0huYEA",  # Blender Open Movie: "Sprite Fright"
    "https://www.youtube.com/watch?v=z2K4yL4h01Y",  # Google Chrome Developers
    "https://www.youtube.com/watch?v=aqz-KE-bpKQ"   # Blender Open Movie: "Big Buck Bunny"
]

# Mock GUI callback to capture progress data
# This global dictionary can be used if we want to analyze all progress data after the run.
# For this script, direct printing in mock_gui_callback is the primary feedback.
progress_data_log_for_analysis = {} 

def mock_gui_callback(data):
    # Simple print for immediate feedback during testing
    print(f"PROGRESS_CALLBACK_DATA: {data}")
    
    # Optional: Store data for later summary
    # url_key = data.get('url_key_for_test', 'unknown_url') 
    # if url_key not in progress_data_log_for_analysis:
    #     progress_data_log_for_analysis[url_key] = []
    # progress_data_log_for_analysis[url_key].append(data)

def check_ffmpeg_validity(filepath):
    print(f"  FFMPEG_CHECK: Validating {os.path.basename(filepath)}...")
    if not os.path.exists(filepath):
        print(f"FFMPEG_CHECK_FAILURE: File not found at {filepath}")
        return "File not found" # Changed from False for clarity in summary
    try:
        result = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', filepath, '-f', 'null', '-'],
            capture_output=True,
            text=True,
            check=False  # Do not raise exception on non-zero exit
        )
        if result.returncode == 0 and not result.stderr.strip(): # Check for empty stderr as well
            print(f"FFMPEG_CHECK_SUCCESS: {os.path.basename(filepath)} appears valid.")
            return "Valid"
        else:
            error_output = result.stderr.strip() if result.stderr.strip() else "No specific error on stderr."
            print(f"FFMPEG_CHECK_FAILURE: {os.path.basename(filepath)} - FFmpeg (code {result.returncode}): {error_output}")
            return f"FFmpeg errors (code {result.returncode}): {error_output}"
    except FileNotFoundError:
        print("FFMPEG_CHECK_FAILURE: ffmpeg command not found. Ensure ffmpeg is installed and in PATH.")
        return "ffmpeg command not found"
    except Exception as e:
        print(f"FFMPEG_CHECK_FAILURE: An unexpected error occurred during ffmpeg check: {e}")
        return f"Exception: {e}"

def run_tests():
    temp_dir_main = tempfile.mkdtemp(prefix="mp4_test_main_")
    print(f"TEMP_DIR_CREATED: {temp_dir_main}")
    downloader = Downloader()
    results = {} # Store summary results per URL

    # This try-finally block is for the entire run_tests function
    try:
        for i, url in enumerate(TEST_URLS):
            print(f"--------------------------------------------------")
            print(f"TESTING_URL ({i+1}/{len(TEST_URLS)}): {url}")
            
            file_path = None # Initialize file_path for this iteration
            current_result_data = {
                "status": "Not run", 
                "path": "N/A", 
                "ext_ok": "N/A", 
                "ffmpeg_ok": "N/A", 
                "error": None,
                "progress_updates_count": 0
            }
            
            # Create a unique subdirectory for this specific URL's download
            # This helps in isolating files if names are the same from yt-dlp
            url_specific_download_path = os.path.join(temp_dir_main, f"video_{i}")
            os.makedirs(url_specific_download_path, exist_ok=True)

            # Counter for progress updates for this specific URL
            current_url_progress_count = 0
            def test_specific_callback(progress_data):
                nonlocal current_url_progress_count
                current_url_progress_count +=1
                mock_gui_callback(progress_data) # Call the general printer

            try:
                file_path = downloader.download_media(
                    url,
                    url_specific_download_path, 
                    preferred_format_info={'format_id': 'mp4'},
                    progress_callback=test_specific_callback
                )

                current_result_data["progress_updates_count"] = current_url_progress_count

                if file_path and os.path.exists(file_path):
                    print(f"DOWNLOAD_SUCCESS_PATH: {file_path}")
                    current_result_data["status"] = "Success"
                    current_result_data["path"] = file_path
                    
                    extension_correct = file_path.lower().endswith('.mp4')
                    current_result_data["ext_ok"] = extension_correct
                    print(f"EXTENSION_CHECK: {'MP4_Correct' if extension_correct else 'MP4_Incorrect'}")
                    
                    ffmpeg_valid_status = check_ffmpeg_validity(file_path)
                    current_result_data["ffmpeg_ok"] = ffmpeg_valid_status
                else:
                    print(f"DOWNLOAD_FAILURE: No file path returned or file does not exist (Path: {file_path}).")
                    current_result_data["status"] = "Failure (No file)"
                    current_result_data["path"] = str(file_path) # Store what was returned

            except DownloadError as de:
                print(f"DOWNLOAD_ERROR: {de}")
                current_result_data["status"] = "DownloadError"
                current_result_data["error"] = str(de)
                current_result_data["progress_updates_count"] = current_url_progress_count # Log count even on error
            except Exception as e:
                print(f"DOWNLOAD_UNEXPECTED_ERROR: {type(e).__name__} - {e}")
                current_result_data["status"] = "UnexpectedError"
                current_result_data["error"] = str(e)
                current_result_data["progress_updates_count"] = current_url_progress_count # Log count even on error
                import traceback
                traceback.print_exc()


            results[url] = current_result_data
            print(f"--- Test for {url} ended ---")

    finally:
        # This finally block ensures cleanup happens after all tests in run_tests are done
        try:
            if os.path.exists(temp_dir_main): # Check if temp_dir was created
                shutil.rmtree(temp_dir_main)
                print(f"TEMP_DIR_REMOVED: {temp_dir_main}")
        except Exception as e:
            print(f"ERROR_REMOVING_TEMP_DIR: {temp_dir_main} - {e}")

    print(f"--------------------------------------------------")
    print(f"FINAL_RESULTS_SUMMARY:")
    for url_key, result_val in results.items():
        print(f"  URL: {url_key}")
        for k, v_item in result_val.items(): # Changed v to v_item to avoid conflict
            # For path, just print basename for cleaner summary
            if k == "path" and isinstance(v_item, str) and v_item != "N/A":
                print(f"    {k}: .../{os.path.basename(v_item)}")
            else:
                print(f"    {k}: {v_item}")
    print(f"--------------------------------------------------")


if __name__ == "__main__":
    run_tests()
```
