import ffmpeg
import os
import sys

# Add src directory to sys.path to allow direct import of Downloader
# This is for the __main__ block and might need adjustment based on final project structure
if __name__ == "__main__":
    # Correctly add the project root (/app) to sys.path
    # __file__ is /app/src/core/converter.py
    # os.path.dirname(__file__) is /app/src/core
    # os.path.join(..., '..', '..') is /app
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.core.downloader import Downloader, DownloadError

class ConversionError(Exception):
    """Custom exception for conversion errors."""
    pass

class Converter:
    def convert_media(self, input_file_path: str, output_file_path: str, output_format: str) -> str:
        """
        Converts a media file to the specified output format.

        Args:
            input_file_path: Path to the input media file.
            output_file_path: Desired path for the converted media file (including new extension).
            output_format: The target format (e.g., "mp3", "mp4", "avi", "mov").
                           This helps in setting specific ffmpeg options.

        Returns:
            The full path to the converted file.

        Raises:
            ConversionError: If any error occurs during the conversion.
            FileNotFoundError: If the input file does not exist.
        """
        if not os.path.exists(input_file_path):
            raise FileNotFoundError(f"Input file not found: {input_file_path}")

        # Ensure output directory exists
        output_dir = os.path.dirname(output_file_path)
        if output_dir: # Handle cases where output is in current dir
            os.makedirs(output_dir, exist_ok=True)

        try:
            stream = ffmpeg.input(input_file_path)
            
            # Common options
            ffmpeg_options = {'y': None} # Overwrite output file if it exists

            if output_format.lower() == "mp3":
                stream = ffmpeg.output(stream, output_file_path, acodec='libmp3lame', vn=None, **ffmpeg_options)
            elif output_format.lower() == "avi":
                # For AVI, ffmpeg might need specific codecs if defaults are problematic
                # For now, rely on ffmpeg's defaults for the container.
                # Common codecs for AVI: video='mpeg4', audio='mp3'
                stream = ffmpeg.output(stream, output_file_path, vcodec='mpeg4', acodec='mp3', **ffmpeg_options)
            elif output_format.lower() == "mov":
                # MOV often uses H.264 for video and AAC for audio.
                # Rely on ffmpeg's defaults first.
                stream = ffmpeg.output(stream, output_file_path, vcodec='libx264', acodec='aac', **ffmpeg_options)
            elif output_format.lower() == "mp4":
                 # Default for mp4 is often h264 and aac, which is good.
                 # If input is already mp4, this is more like a re-encode or stream copy if options allow.
                 # For simplicity, let's assume a re-encode if mp4 is chosen.
                stream = ffmpeg.output(stream, output_file_path, vcodec='libx264', acodec='aac', **ffmpeg_options)
            else:
                # For other formats, try to let ffmpeg infer from output_file_path extension
                # This might not always pick the best codecs.
                stream = ffmpeg.output(stream, output_file_path, **ffmpeg_options)
            
            # Execute ffmpeg command
            # .run() can take 'capture_stdout=True, capture_stderr=True'
            # stdout, stderr = ffmpeg.run(stream, capture_stdout=True, capture_stderr=True, overwrite_output=True)
            # Using overwrite_output in run() is another way, or -y in global_args
            
            # For debugging, print the command:
            # print("FFmpeg command:", stream.compile())

            _, stderr = stream.run(capture_stdout=True, capture_stderr=True) # overwrite_output=True handled by -y

            return output_file_path

        except ffmpeg.Error as e:
            # The stderr from ffmpeg.Error is often very informative
            error_message = f"ffmpeg error: {e.stderr.decode('utf8') if e.stderr else 'Unknown ffmpeg error'}"
            raise ConversionError(error_message)
        except Exception as e:
            raise ConversionError(f"An unexpected error occurred during conversion: {type(e).__name__} - {e}")

if __name__ == "__main__":
    converter = Converter()
    downloader = Downloader()

    # Test video URL (short Creative Commons video)
    test_url = "https://www.youtube.com/watch?v=C0DPdy98e4c" # LEGO Star Wars Stop Motion (CC) ~2min
    download_dir = "assets/downloads"
    converted_dir = "assets/converted"

    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(converted_dir, exist_ok=True)

    downloaded_file_path = None
    base_filename = "test_video_for_conversion" # Keep it simple

    try:
        print(f"Downloading test video from {test_url}...")
        # To avoid re-downloading every time, let's check if a version exists
        # This is a simplified check; real usage would involve more robust file management.
        
        # Clean up any previous specific test files to ensure fresh download/conversion
        # This is a bit more targeted than cleaning the whole directory.
        temp_download_path_base = os.path.join(download_dir, base_filename)
        
        # Remove files starting with this base name in download_dir
        for f in os.listdir(download_dir):
            if f.startswith(base_filename):
                os.remove(os.path.join(download_dir, f))
                print(f"Removed old download: {f}")

        # Change yt-dlp output template for this specific download to control the name
        original_ydl_opts = downloader.ydl_opts if hasattr(downloader, 'ydl_opts') else {} # Save original
        
        # Hacky way to change ydl_opts for this test.
        # A better Downloader class might allow passing ydl_opts per call.
        # For now, directly modify if possible, or accept this limitation.
        # Let's assume the Downloader's default naming is fine, and we'll find the file.
        # The Downloader's current implementation uses '%(title)s.%(ext)s'.
        # The title of 'C0DPdy98e4c' is "TEST VIDEO".
        
        print("Using Downloader to fetch a sample video...")
        downloaded_file_path = downloader.download_media(test_url, download_dir)
        print(f"Video downloaded to: {downloaded_file_path}")

        if not downloaded_file_path or not os.path.exists(downloaded_file_path):
            raise Exception(f"Test video download failed or file not found: {downloaded_file_path}")

        # --- Test 1: Convert to MP3 ---
        output_mp3_path = os.path.join(converted_dir, base_filename + ".mp3")
        print(f"\nConverting {downloaded_file_path} to MP3 ({output_mp3_path})...")
        try:
            converted_mp3 = converter.convert_media(downloaded_file_path, output_mp3_path, "mp3")
            print(f"Successfully converted to MP3: {converted_mp3}")
            assert os.path.exists(converted_mp3)
        except ConversionError as e:
            print(f"MP3 Conversion failed: {e}")
        except FileNotFoundError as e:
             print(f"MP3 Conversion FileNotFoundError: {e}")


        # --- Test 2: Convert to AVI (from original downloaded file) ---
        output_avi_path = os.path.join(converted_dir, base_filename + ".avi")
        print(f"\nConverting {downloaded_file_path} to AVI ({output_avi_path})...")
        try:
            converted_avi = converter.convert_media(downloaded_file_path, output_avi_path, "avi")
            print(f"Successfully converted to AVI: {converted_avi}")
            assert os.path.exists(converted_avi)
        except ConversionError as e:
            print(f"AVI Conversion failed: {e}")
        except FileNotFoundError as e:
             print(f"AVI Conversion FileNotFoundError: {e}")

        # --- Test 3: Convert to MOV (from original downloaded file) ---
        output_mov_path = os.path.join(converted_dir, base_filename + ".mov")
        print(f"\nConverting {downloaded_file_path} to MOV ({output_mov_path})...")
        try:
            converted_mov = converter.convert_media(downloaded_file_path, output_mov_path, "mov")
            print(f"Successfully converted to MOV: {converted_mov}")
            assert os.path.exists(converted_mov)
        except ConversionError as e:
            print(f"MOV Conversion failed: {e}")
        except FileNotFoundError as e:
            print(f"MOV Conversion FileNotFoundError: {e}")


    except DownloadError as e:
        print(f"Could not download test video: {e}")
    except FileNotFoundError as e:
        print(f"A file was not found during testing: {e}")
    except Exception as e:
        print(f"An unexpected error occurred in the test script: {type(e).__name__} - {e}")
    finally:
        # --- Cleanup ---
        print("\nCleaning up test files...")
        if downloaded_file_path and os.path.exists(downloaded_file_path):
            try:
                os.remove(downloaded_file_path)
                print(f"Removed downloaded file: {downloaded_file_path}")
            except OSError as e:
                print(f"Error removing downloaded file {downloaded_file_path}: {e}")
        
        files_to_remove_in_converted = [
            os.path.join(converted_dir, base_filename + ".mp3"),
            os.path.join(converted_dir, base_filename + ".avi"),
            os.path.join(converted_dir, base_filename + ".mov")
        ]
        for f_path in files_to_remove_in_converted:
            if os.path.exists(f_path):
                try:
                    os.remove(f_path)
                    print(f"Removed converted file: {f_path}")
                except OSError as e:
                    print(f"Error removing converted file {f_path}: {e}")
        print("Cleanup complete.")
