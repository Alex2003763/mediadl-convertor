import tkinter as tk
from tkinter import ttk, PhotoImage
import os
import threading
import re # For cleaning ANSI codes from yt-dlp progress string

import tkinter.font as tkFont # Import for font management
# Ensure the script can find the core package when run directly
if __name__ == "__main__" and __package__ is None:
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.core.downloader import Downloader, DownloadError
from src.core.converter import Converter, ConversionError
from . import theme # Import the theme


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.configure(bg=theme.BACKGROUND_WINDOW) # Set main window background

        self.title("Media Downloader and Converter")
        self.geometry("700x450")  # Adjusted size for better layout

        # --- Font Definitions ---
        self.app_font_family = theme.FONT_FAMILY_PRIMARY # "Roboto"
        self.font_body = tkFont.Font(family=self.app_font_family, size=theme.FONT_SIZE_NORMAL, weight=theme.FONT_WEIGHT_NORMAL)
        self.font_body_bold = tkFont.Font(family=self.app_font_family, size=theme.FONT_SIZE_NORMAL, weight=theme.FONT_WEIGHT_BOLD)
        self.font_small = tkFont.Font(family=self.app_font_family, size=theme.FONT_SIZE_SMALL, weight=theme.FONT_WEIGHT_NORMAL)
        self.font_button = self.font_body_bold # Buttons use bold body font

        # --- Icon Loading ---
        self.download_icon_image = None # Initialize
        try:
            # Ensure theme.DOWNLOAD_ICON_BASE64 is valid base64 string for PhotoImage
            self.download_icon_image = tk.PhotoImage(data=theme.DOWNLOAD_ICON_BASE64)
        except tk.TclError:
            print("Warning: Could not load download icon from base64 data. Check icon data and Tkinter/PhotoImage compatibility.")
        except AttributeError:
             print("Warning: DOWNLOAD_ICON_BASE64 not found in theme.py or theme module not imported correctly.")


        # --- Style Configuration ---
        style = ttk.Style(self)
        # default_font = ("Helvetica", 10) # Using Helvetica as a common sans-serif # Old

        # Global style configurations
        style.configure('.', 
                        font=self.font_body, # Apply new font_body
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY_ON_LIGHT, 
                        padding=(5, 5))

        # Labels (TLabel)
        style.configure('TLabel', 
                        font=self.font_body, # Apply new font_body
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY_ON_LIGHT, 
                        padding=(5,5))
        # Specific label for URL/Format description, now on the "card" (input_frame)
        style.configure('InputDescription.TLabel', 
                        font=self.font_body, # Apply new font_body
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY_ON_LIGHT)

        # Frame style for card-like appearance
        style.configure('Card.TFrame', background=theme.BACKGROUND_CONTENT, relief='raised', borderwidth=1)


        # Buttons (TButton)
        style.configure('TButton',
                        font=self.font_button, # Apply new font_button
                        background=theme.COLOR_ACCENT,
                        foreground=theme.TEXT_PRIMARY_ON_DARK,
                        borderwidth=0,
                        relief='flat',
                        padding=(10, 8)) 
        style.map('TButton',
                  background=[('active', theme.COLOR_ACCENT_DARK), 
                              ('disabled', theme.BACKGROUND_INPUT)],
                  foreground=[('disabled', theme.TEXT_SECONDARY_ON_LIGHT)])

        # Input Fields (TEntry)
        style.configure('TEntry',
                        font=self.font_body, # Apply new font_body
                        fieldbackground=theme.BACKGROUND_CONTENT,
                        foreground=theme.TEXT_PRIMARY_ON_LIGHT,
                        borderwidth=1, 
                        relief='solid',
                        padding=(5,5))
        # TODO: Set insertcolor directly on widget instance for TEntry
        # self.url_entry.configure(insertbackground=theme.TEXT_PRIMARY_ON_LIGHT)
        style.map('TEntry',
                  bordercolor=[('focus', theme.COLOR_ACCENT)],
                  relief=[('focus', 'solid')])


        # OptionMenu (TMenubutton)
        style.configure('TMenubutton',
                        font=self.font_body, # Apply new font_body
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY_ON_LIGHT,
                        relief='flat', 
                        padding=(5,5),
                        borderwidth=1) 

        # Progress Bar (Horizontal.TProgressbar)
        style.configure('Horizontal.TProgressbar',
                        background=theme.COLOR_ACCENT, # Color of the bar itself
                        troughcolor=theme.BACKGROUND_INPUT, # Background of the trough
                        borderwidth=0,
                        relief='flat')
        
        # Core components
        self.downloader = Downloader()
        self.converter = Converter()
        self.download_dir = "downloads"
        os.makedirs(self.download_dir, exist_ok=True)

        # --- UI Elements ---
        self.grid_columnconfigure(0, weight=1) # Main content frame column
        self.grid_rowconfigure(3, weight=1) # Status area row

        # --- Main Content Frame ---
        main_content_frame = ttk.Frame(self, padding=(10,10))
        main_content_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10,0)) # Pad X, and Top only for main frame
        main_content_frame.grid_columnconfigure(0, weight=1) # Allow content within to expand

        # --- Input Frame for URL and Format (Card-like) ---
        input_frame = ttk.Frame(main_content_frame, padding=(15,15), style='Card.TFrame')
        input_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,10)) # Spacing below input card
        input_frame.grid_columnconfigure(1, weight=1) # Allow entry and menu to expand within this frame

        # Media URL
        self.url_label = ttk.Label(input_frame, text="Media URL:", style='InputDescription.TLabel')
        self.url_label.grid(row=0, column=0, padx=(0,10), pady=(0,10), sticky="w") # Increased internal padding
        self.url_entry = ttk.Entry(input_frame, width=60) 
        self.url_entry.grid(row=0, column=1, pady=(0,10), sticky="ew")

        # Output Format
        self.format_label = ttk.Label(input_frame, text="Output Format:", style='InputDescription.TLabel')
        self.format_label.grid(row=1, column=0, padx=(0,10), pady=(0,5), sticky="w") # Increased internal padding
        self.format_options = ["mp4", "mp3", "avi", "mov", "webm"] 
        self.format_var = tk.StringVar(self)
        self.format_var.set(self.format_options[0]) 
        self.format_menu = ttk.OptionMenu(input_frame, self.format_var, self.format_options[0], *self.format_options) 
        self.format_menu.grid(row=1, column=1, pady=(0,5), sticky="ew")

        # Download & Convert Button - Centered below input_frame
        button_config = {
            "text": "Download & Convert",
            "command": self.start_download_and_convert,
            "style": 'TButton'
        }
        if self.download_icon_image:
            button_config["image"] = self.download_icon_image
            button_config["compound"] = 'left'
        
        self.download_button = ttk.Button(main_content_frame, **button_config)
        self.download_button.grid(row=1, column=0, columnspan=2, pady=15) 

        # Progress Bar - Placed below the button
        self.progress_bar = ttk.Progressbar(main_content_frame, orient="horizontal", length=400, mode="determinate") 
        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10) # Increased pady

        # Status Messages - Frame and Text widget
        # This frame will also be part of main_content_frame for consistent padding from window edges
        self.status_text_frame = ttk.Frame(main_content_frame) 
        self.status_text_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(0,5)) # pady adjusted
        self.status_text_frame.grid_rowconfigure(0, weight=1)
        self.status_text_frame.grid_columnconfigure(0, weight=1)
        
        main_content_frame.grid_rowconfigure(3, weight=1) # Allow status_text_frame to expand within main_content_frame

        self.status_text = tk.Text(self.status_text_frame, 
                                 height=10, width=80, # Width might be less critical if it expands
                                 state="disabled", wrap=tk.WORD,
                                 bg=theme.BACKGROUND_CONTENT, 
                                 fg=theme.TEXT_SECONDARY_ON_LIGHT,
                                 font=self.font_small, # Apply new font_small
                                 relief='solid', 
                                 borderwidth=1,
                                 padx=10, pady=10) 
        self.status_text.grid(row=0, column=0, sticky="nsew")
        # TODO: Set insertcolor for status_text if it becomes editable
        
        self.scrollbar = ttk.Scrollbar(self.status_text_frame, orient=tk.VERTICAL, command=self.status_text.yview)
        self.status_text.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.update_status("Ready. Enter a URL and select a format.")

    # --- Formatting Helper Methods ---
    def _format_bytes(self, size_bytes):
        if size_bytes is None or size_bytes < 0: return "N/A"
        if size_bytes == 0: return "0 B"
        import math
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        if i >= len(size_name): i = len(size_name) - 1 # Cap at TB to avoid index error
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def _format_eta(self, seconds):
        if seconds is None or seconds < 0: return "--:--"
        try:
            seconds = int(seconds)
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            if h > 0:
                return f"{h:02d}:{m:02d}:{s:02d}"
            return f"{m:02d}:{s:02d}"
        except (ValueError, TypeError):
            return "--:--"

    def _format_speed(self, speed_bytes_sec):
        if speed_bytes_sec is None or speed_bytes_sec < 0: return "N/A"
        if speed_bytes_sec == 0: return "0 B/s"
        # Re-use _format_bytes logic for unit conversion
        formatted_size = self._format_bytes(speed_bytes_sec)
        if formatted_size == "N/A": return "N/A" # Should not happen if input is valid
        return f"{formatted_size}/s"

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

    def _gui_progress_hook(self, data): # Renamed 'd' to 'data' for clarity
        if data['status'] == 'downloading':
            percentage = data.get('percentage', 0.0)
            downloaded_bytes = data.get('downloaded_bytes', 0)
            total_bytes = data.get('total_bytes', 0)
            speed_bytes_sec = data.get('speed', 0)
            eta_seconds = data.get('eta', 0)

            downloaded_str = self._format_bytes(downloaded_bytes)
            total_str = self._format_bytes(total_bytes)
            speed_str = self._format_speed(speed_bytes_sec)
            eta_str = self._format_eta(eta_seconds)
            
            # Update progress bar (thread-safe)
            final_percentage = max(0.0, min(100.0, percentage))
            self.after(0, lambda: self.progress_bar.config(value=final_percentage))
            
            status_message = f"Downloading: {final_percentage:.1f}% ({downloaded_str} / {total_str}) at {speed_str}, ETA: {eta_str}"
            self.update_status(status_message)

        elif data['status'] == 'finished':
            filename = data.get('filename', 'Unknown file')
            self.after(0, lambda: self.progress_bar.config(value=100))
            self.update_status(f"Download finished: {os.path.basename(filename)}. Preparing for conversion...")
        
        elif data['status'] == 'error':
            error_message = data.get('message', 'Unknown download error')
            self.update_status(f"Download Error: {error_message}")
            # Reset progress bar on error
            self.after(0, lambda: self.progress_bar.config(value=0))


    def _download_and_convert_thread(self, url, output_format_selected):
        downloaded_file_path = None
        try:
            self.update_status(f"Fetching URL: {url}")
            
            # Construct preferred_format_info based on user's selection
            preferred_format_info = {'format_id': output_format_selected.lower()}
            self.update_status(f"Requesting format '{output_format_selected.lower()}' from downloader.")

            # Note: The progress_callback is called by yt-dlp from its own thread context.
            # The _gui_progress_hook uses self.after to marshal GUI updates to the main Tk thread.
            downloaded_file_path = self.downloader.download_media(
                url, 
                self.download_dir, 
                preferred_format_info=preferred_format_info, # Pass the preferred format
                progress_callback=self._gui_progress_hook
            )
            
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
