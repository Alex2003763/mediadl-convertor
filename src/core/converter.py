import ffmpeg
import os
import sys
import threading
import subprocess
import signal

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
    def __init__(self):
        self._stop_flag = threading.Event()
        self._ffmpeg_process = None # To hold the subprocess object

    def stop_conversion(self):
        """Signals the current conversion to stop."""
        self._stop_flag.set()
        if self._ffmpeg_process:
           self._ffmpeg_process.kill() # Forcefully terminate the FFmpeg process

    def _parse_ffmpeg_progress(self, line):
        """Parses a line of FFmpeg stderr output to extract progress information."""
        # Example FFmpeg progress line:
        # frame=  137 fps= 25 q=28.0 size=     432kB time=00:00:05.48 bitrate= 645.0kbits/s speed=1.01x
        progress = {}
        if line.startswith("frame="):
            parts = line.split()
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    if key == "frame" and value.strip():
                        try:
                            progress['frame'] = int(value)
                        except ValueError:
                            pass # Ignore if value is not a valid int
                    elif key == "fps" and value.strip():
                        try:
                            progress['fps'] = float(value)
                        except ValueError:
                            pass # Ignore if value is not a valid float
                    elif key == "size":
                        # Handle size like 432kB, 10MB
                        if 'kB' in value.lower():
                            progress['size_kb'] = float(value.lower().replace('kb', ''))
                        elif 'mb' in value.lower():
                            progress['size_mb'] = float(value.lower().replace('mb', ''))
                    elif key == "time": # HH:MM:SS.ms
                        progress['time_str'] = value
                        try:
                            h, m, s_ms = value.split(':')
                            s_val, ms_val = s_ms.split('.')
                            if h.strip() and m.strip() and s_val.strip() and ms_val.strip():
                                progress['time_seconds'] = int(h) * 3600 + int(m) * 60 + float(s_val) + (float(ms_val) / 100.0)
                        except ValueError:
                            pass 
                    elif key == "bitrate" and value.strip().lower().replace('kbits/s', '').replace('.', '', 1).isdigit():
                        try:
                            progress['bitrate_kbits'] = float(value.lower().replace('kbits/s', ''))
                        except ValueError:
                            pass
                    elif key == "speed" and value.strip():
                        progress['speed'] = value
        return progress

    def convert_media(self, input_file_path: str, output_file_path: str, output_format: str, threads: int = 8, preset: str = 'ultrafast', progress_callback=None, start_time: str = None, end_time: str = None, gif_fps: int = 10, gif_scale_width: int = 480) -> str:
        """
        Converts a media file to the specified output format, with optional trimming and GIF specific settings.

        Args:
            input_file_path: Path to the input media file.
            output_file_path: Desired path for the converted media file (including new extension).
            output_format: The target format (e.g., "mp3", "mp4", "avi", "mov", "gif").
            threads: Number of threads to use for conversion. 0 means auto-detect.
            preset: FFmpeg preset for video encoding (e.g., 'ultrafast', 'fast', 'medium', 'slow').
            progress_callback: Callback function for progress updates.
            start_time: Start time for trimming (e.g., "00:00:10").
            end_time: End time for trimming (e.g., "00:00:20").
            gif_fps: FPS for GIF conversion.
            gif_scale_width: Width to scale GIF to (height is auto, -1).

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
            input_options = {}
            if start_time:
                input_options['ss'] = start_time
            if end_time:
                # If using 'to' with 'ss', 'to' is an absolute timestamp.
                # If 'ss' is before 'to', it effectively sets a duration from 'ss'.
                # For simplicity, if both are provided, 'to' acts as the endpoint.
                # ffmpeg-python's 'to' parameter corresponds to ffmpeg's -to option.
                input_options['to'] = end_time
            
            stream = ffmpeg.input(input_file_path, **input_options)
            
            # Common options
            ffmpeg_options = {'y': None} # Overwrite output file if it exists

            # Add threads option if specified
            if threads is not None:
                 ffmpeg_options['threads'] = threads

            if output_format.lower() == "mp3":
                stream = ffmpeg.output(stream, output_file_path, acodec='libmp3lame', vn=None, **ffmpeg_options)
            elif output_format.lower() == "gif":
                # For GIF, we use a filter_complex for palette generation and usage
                # This improves GIF quality significantly.
                # Example: ffmpeg -i input.mp4 -vf "fps=10,scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" output.gif
                
                # For GIF, use a filter_complex for palette generation and usage for better quality.
                # The filter string combines scaling, FPS adjustment, splitting for palette generation,
                # generating the palette, and then using that palette.
                # [0:v] refers to the first video stream from the input.
                filter_graph_str = (
                    f"[0:v]fps={gif_fps},scale={gif_scale_width}:-1:flags=lanczos,"
                    f"split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
                )
                
                # Apply the complex filter graph to the input stream
                # Apply initial filters (fps, scale)
                processed_stream = stream.filter('fps', fps=gif_fps)
                processed_stream = processed_stream.filter('scale', width=gif_scale_width, height=-1, flags='lanczos')

                # Split the stream for palette generation and main processing
                split_streams = processed_stream.split()
                
                stream_for_palette = split_streams[0]
                stream_for_use = split_streams[1]

                # Generate palette from one part of the split stream
                # stats_mode='single' can be more efficient for animated GIFs
                palette_stream = stream_for_palette.filter('palettegen', stats_mode='single')

                # Use the generated palette with the other part of the split stream
                # The ffmpeg.filter function takes a list of input streams
                processed_gif_stream = ffmpeg.filter([stream_for_use, palette_stream], 'paletteuse', dither='sierra2_4a')
                
                # Output the final processed stream
                stream = ffmpeg.output(processed_gif_stream, output_file_path, **ffmpeg_options)

            elif output_format.lower() in ["mp4", "mov", "avi", "webm"]:
                 # Add preset for video formats
                 video_options = {'preset': preset}
                 # Merge video options with common options
                 merged_options = {**ffmpeg_options, **video_options}

                 if output_format.lower() == "mp4":
                     stream = ffmpeg.output(stream, output_file_path, vcodec='libx264', acodec='aac', **merged_options)
                 elif output_format.lower() == "mov":
                     stream = ffmpeg.output(stream, output_file_path, vcodec='libx264', acodec='aac', **merged_options)
                 elif output_format.lower() == "avi":
                     stream = ffmpeg.output(stream, output_file_path, vcodec='mpeg4', acodec='mp3', **merged_options)
                 elif output_format.lower() == "webm":
                     stream = ffmpeg.output(stream, output_file_path, vcodec='libvpx-vp9', acodec='libopus', **merged_options)
            else:
                # Default case for other formats
                stream = ffmpeg.output(stream, output_file_path, **ffmpeg_options)

            # For debugging, print the command:
            # print("FFmpeg command:", stream.compile())

            # Get total duration of input file for percentage calculation
            # If start_time and end_time are provided, the effective duration changes.
            total_duration_seconds = 0
            try:
                probe_input_options = {}
                # Probing should be on the original file for full duration,
                # or on the trimmed segment if we want progress relative to trimmed part.
                # For now, let's get original duration and adjust if trimmed.
                probe = ffmpeg.probe(input_file_path) # Probe original file
                
                file_duration = 0
                video_stream_info = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
                if video_stream_info and 'duration' in video_stream_info:
                    file_duration = float(video_stream_info['duration'])
                elif 'format' in probe and 'duration' in probe['format']:
                    file_duration = float(probe['format']['duration'])

                if start_time or end_time:
                    s_time = 0.0
                    e_time = file_duration

                    if start_time:
                        try:
                            h, m, s = map(float, start_time.split(':'))
                            s_time = h * 3600 + m * 60 + s
                        except ValueError:
                            print(f"Warning: Could not parse start_time '{start_time}' for duration calculation.")
                            s_time = 0.0
                    
                    if end_time:
                        try:
                            h, m, s = map(float, end_time.split(':'))
                            e_time = h * 3600 + m * 60 + s
                        except ValueError:
                            print(f"Warning: Could not parse end_time '{end_time}' for duration calculation.")
                            e_time = file_duration
                    
                    total_duration_seconds = max(0, e_time - s_time)
                    if total_duration_seconds == 0 and file_duration > 0 : # if parsing failed or times were identical
                        total_duration_seconds = file_duration # fallback to full duration if trim calculation is problematic
                else:
                    total_duration_seconds = file_duration

            except ffmpeg.Error as e_probe:
                print(f"Warning: Could not probe input file duration: {e_probe.stderr.decode('utf8') if e_probe.stderr else str(e_probe)}")



            cmd = stream.compile()
            # Explicitly set encoding to utf-8 and handle errors
            
            # Use creationflags for Windows to ensure child processes are terminated
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

            self._ffmpeg_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, encoding='utf-8', errors='replace', creationflags=creationflags)
            self._stop_flag.clear() # Clear the stop flag for a new conversion

            stderr_output = ""
            for line in iter(self._ffmpeg_process.stderr.readline, ""):
                stderr_output += line
                if self._stop_flag.is_set():
                    # If stop is requested, terminate FFmpeg and raise an error
                    # Use os.kill on Windows to terminate the process group
                    if sys.platform == "win32":
                        # Use SIGTERM first, then SIGKILL if needed
                        try:
                            os.kill(self._ffmpeg_process.pid, signal.SIGTERM)
                        except OSError:
                            pass # Process might have already exited
                        # Give it a moment, then kill if still alive
                        self._ffmpeg_process.poll()
                        if self._ffmpeg_process.returncode is None:
                             try:
                                 os.kill(self._ffmpeg_process.pid, signal.SIGKILL)
                             except OSError:
                                 pass # Process might have already exited
                    else:
                        # Use terminate() or kill() on other platforms
                        self._ffmpeg_process.kill() # Use kill for consistency with stop_conversion

                    raise ConversionError("Conversion stopped by user.")

                if progress_callback:
                    progress_data = self._parse_ffmpeg_progress(line.strip())
                    if progress_data:
                        progress_data['status'] = 'converting'
                        if total_duration_seconds > 0 and 'time_seconds' in progress_data:
                            progress_data['percentage'] = (progress_data['time_seconds'] / total_duration_seconds) * 100
                        else:
                            progress_data['percentage'] = None # Indeterminate if no duration
                        progress_callback(progress_data)
            
            self._ffmpeg_process.wait() # Wait for the process to complete

            if self._ffmpeg_process.returncode != 0:
                raise ConversionError(f"ffmpeg error (return code {self._ffmpeg_process.returncode}): {stderr_output}")

            if progress_callback:
                progress_callback({'status': 'finished_conversion', 'filename': output_file_path})

            return output_file_path

        except ConversionError as e: # Catch the specific ConversionError for user stop
            raise e
        except ffmpeg.Error as e: # Should be caught by subprocess handling now, but keep as fallback
            error_message = f"ffmpeg.Error: {e.stderr.decode('utf8') if e.stderr else 'Unknown ffmpeg error'}"
            raise ConversionError(error_message)
        except Exception as e:
            raise ConversionError(f"An unexpected error occurred during conversion: {type(e).__name__} - {e}")
        finally:
            self._ffmpeg_process = None # Clear reference after process finishes or errors

if __name__ == "__main__":
    converter = Converter()
    downloader = Downloader()
