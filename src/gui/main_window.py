import tkinter as tk
from tkinter import ttk
import os
import threading
import re # For cleaning ANSI codes from yt-dlp progress string

# Ensure the script can find the core package when run directly
if __name__ == "__main__" and __package__ is None:
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.core.downloader import Downloader, DownloadError
from src.core.converter import Converter, ConversionError


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Media Downloader and Converter")
        self.geometry("700x450")  # Adjusted size for better layout

        # Core components
        self.downloader = Downloader()
        self.converter = Converter()
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)

        # --- UI Elements ---
        self.grid_columnconfigure(1, weight=1) # Allow entry and menu to expand

        # Media URL
        self.url_label = ttk.Label(self, text="Media URL:")
        self.url_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.url_entry = ttk.Entry(self, width=60)
        self.url_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Output Format
        self.format_label = ttk.Label(self, text="Output Format:")
        self.format_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.format_options = ["mp4", "mp3", "avi", "mov", "webm"] # Lowercase, added webm
        self.format_var = tk.StringVar(self)
        self.format_var.set(self.format_options[0]) # Default value
        self.format_menu = ttk.OptionMenu(self, self.format_var, self.format_options[0], *self.format_options)
        self.format_menu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # Download & Convert Button
        self.download_button = ttk.Button(self, text="Download & Convert", command=self.start_download_and_convert)
        self.download_button.grid(row=2, column=0, columnspan=2, padx=10, pady=15)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(self, orient="horizontal", length=400, mode="determinate")
        self.progress_bar.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        # Status Messages
        self.status_text_frame = ttk.Frame(self) # Frame for Text and Scrollbar
        self.status_text_frame.grid(row=4, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.status_text_frame.grid_rowconfigure(0, weight=1)
        self.status_text_frame.grid_columnconfigure(0, weight=1)

        self.status_text = tk.Text(self.status_text_frame, height=10, width=80, state="disabled", wrap=tk.WORD)
        self.status_text.grid(row=0, column=0, sticky="nsew")
        
        self.scrollbar = ttk.Scrollbar(self.status_text_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.grid_rowconfigure(4, weight=1) # Allow status_text_frame to expand

        self.update_status("Ready. Enter a URL and select a format.")

    def _get_unique_filepath(self, filepath):
        if not os.path.exists(filepath):
            return filepath
        base, ext = os.path.splitext(filepath)
        i = 1
        while True:
            new_filepath = f"{base}_{i}{ext}"
            if not os.path.exists(new_filepath):
                return new_filepath
            i += 1

    def update_status(self, message):
        def _update():
            self.status_text.config(state="normal")
            self.status_text.insert(tk.END, message + "\n")
            self.status_text.see(tk.END) # Scroll to the end
            self.status_text.config(state="disabled")
        # Schedule the update on the main GUI thread
        # Using self.after, not self.status_text.after for Tk instance method
        self.after(0, _update)


    def start_download_and_convert(self):
        url = self.url_entry.get().strip()
        if not url:
            self.update_status("Please enter a media URL.")
            # Ensure button is re-enabled if it was disabled by a previous valid run's finally block
            # or if it's the first run and it's simply not proceeding.
            self.download_button['state'] = 'normal' 
            return

        self.download_button['state'] = 'disabled'
        output_format = self.format_var.get()

        # Clear previous status messages
        self.status_text.config(state="normal")
        self.status_text.delete('1.0', tk.END)
        self.status_text.config(state="disabled")
        
        self.progress_bar['value'] = 0
        self.update_status(f"Starting process for URL: {url} to format: {output_format}")

        thread = threading.Thread(target=self._download_and_convert_thread, args=(url, output_format))
        thread.daemon = True # Allow main program to exit even if threads are running
        thread.start()

    def _gui_progress_hook(self, d):
        if d['status'] == 'downloading':
            # yt-dlp progress fields: _percent_str, _total_bytes_str, _speed_str, _eta_str
            percent_str = d.get('_percent_str', '0.0%')
            # Clean ANSI escape codes (like color codes) that yt-dlp might output
            cleaned_percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
            
            try:
                # Extract numeric part of percentage
                match = re.search(r'(\d+\.?\d*)%', cleaned_percent_str)
                if match:
                    p_numeric = float(match.group(1))
                    # Update progress bar (thread-safe)
                    self.after(0, lambda: self.progress_bar.config(value=p_numeric))
                else:
                    p_numeric = None # Cannot parse

                total_bytes_str = d.get('_total_bytes_str', 'N/A')
                speed_str = d.get('_speed_str', 'N/A')
                eta_str = d.get('_eta_str', 'N/A')
                
                self.update_status(f"Downloading: {cleaned_percent_str} of {total_bytes_str} at {speed_str} ETA {eta_str}")

            except Exception as e:
                self.update_status(f"Error parsing progress: {e}")

        elif d['status'] == 'finished':
            self.update_status(f"Download finished: {d.get('filename', 'Unknown file')}. Preparing for conversion...")
            self.after(0, lambda: self.progress_bar.config(value=100)) # Briefly show 100% for download
        
        elif d['status'] == 'error':
            self.update_status("Error during download (reported by yt-dlp hook).")


    def _download_and_convert_thread(self, url, output_format_selected):
        downloaded_file_path = None
        try:
            self.update_status(f"Fetching URL: {url}")
            # Note: The progress_callback is called by yt-dlp from its own thread context.
            # The _gui_progress_hook uses self.after to marshal GUI updates to the main Tk thread.
            downloaded_file_path = self.downloader.download_media(url, self.download_dir, progress_callback=self._gui_progress_hook)
            
            if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                self.update_status(f"Download failed: File not found at expected path '{downloaded_file_path}'. Please check the URL and try again.")
                return # Exit thread if download failed

            self.update_status(f"Successfully downloaded: {os.path.basename(downloaded_file_path)}")
            self.after(0, lambda: self.progress_bar.config(value=0)) # Reset for conversion step

            # Determine output path
            base, orig_ext = os.path.splitext(os.path.basename(downloaded_file_path))
            new_filename_base = base 
            output_filename_candidate = f"{new_filename_base}.{output_format_selected.lower()}"
            potential_output_path = os.path.join(self.download_dir, output_filename_candidate)
            
            # Handle potential file overwrite for the final output file
            output_file_path = self._get_unique_filepath(potential_output_path)
            if output_file_path != potential_output_path:
                self.update_status(f"Note: Output file will be saved as {os.path.basename(output_file_path)} to avoid overwriting an existing file.")


            # Check if conversion is needed
            # Compare absolute paths in case download_dir is relative
            abs_downloaded_file_path = os.path.abspath(downloaded_file_path)
            abs_output_file_path_if_same_format = os.path.abspath(os.path.join(self.download_dir, f"{new_filename_base}{orig_ext}"))


            if abs_downloaded_file_path.lower() == abs_output_file_path_if_same_format.lower() and \
               orig_ext.lower().strip('.') == output_format_selected.lower():
                # File is already in the target format and its original name matches the base for output
                self.update_status(f"File is already in {output_format_selected} format.")
                # If the unique path logic changed the name, rename it
                if abs_downloaded_file_path != os.path.abspath(output_file_path):
                    os.rename(abs_downloaded_file_path, output_file_path)
                    self.update_status(f"File renamed to: {os.path.basename(output_file_path)}")
                    downloaded_file_path = output_file_path # Update for further reference
                else:
                    self.update_status(f"File located at: {os.path.basename(output_file_path)}")

            else: # Conversion is needed or file needs renaming to standard output format name
                self.update_status(f"Converting {os.path.basename(downloaded_file_path)} to {output_format_selected}...")
                self.after(0, lambda: self.progress_bar.config(mode='indeterminate'))
                self.after(0, lambda: self.progress_bar.start(10))

                # The converter will use output_file_path which is already unique
                converted_file = self.converter.convert_media(downloaded_file_path, output_file_path, output_format_selected)
                
                self.after(0, lambda: self.progress_bar.stop())
                self.after(0, lambda: self.progress_bar.config(mode='determinate', value=100))
                self.update_status(f"Successfully converted to: {os.path.basename(converted_file)}")

                # Clean up original downloaded file if conversion created a new file (different name)
                # and it wasn't just a rename of the same format.
                if os.path.abspath(converted_file) != abs_downloaded_file_path and os.path.exists(downloaded_file_path):
                    try:
                        os.remove(downloaded_file_path)
                        self.update_status(f"Removed temporary downloaded file: {os.path.basename(downloaded_file_path)}")
                    except OSError as e:
                        self.update_status(f"Error removing temporary file: {str(e)}")
            
            # Final message about the output file
            final_output_file = output_file_path # This path is now unique
            self.update_status(f"Process completed. Final file: {os.path.basename(final_output_file)}")

        except DownloadError as e:
            self.update_status(f"Download Error: {str(e)}. Please check the URL and your internet connection.")
        except ConversionError as e:
            self.update_status(f"Conversion Error: {str(e)}. The downloaded file might still be available if download succeeded.")
            if downloaded_file_path and os.path.exists(downloaded_file_path):
                 self.update_status(f"Original downloaded file kept at: {os.path.basename(downloaded_file_path)}")
        except FileNotFoundError as e: 
            self.update_status(f"Error: A required file was not found. Details: {str(e)}")
        except Exception as e:
            self.update_status(f"An unexpected error occurred: {type(e).__name__} - {str(e)}. Please check the logs or report this issue.")
        finally:
            self.after(0, lambda: self.download_button.config(state='normal'))
            self.after(0, lambda: self.progress_bar.stop())
            # Set progress to 0 if download_file_path is None (e.g. URL validation failed before any processing)
            # or to 100 if process finished (even if with errors after download step).
            final_progress_val = 0
            if 'downloaded_file_path' in locals() and downloaded_file_path: # Check if variable exists and is not None
                final_progress_val = 100
            
            self.after(0, lambda: self.progress_bar.config(mode='determinate', value=final_progress_val))


if __name__ == "__main__":
    app = App()
    app.mainloop()
