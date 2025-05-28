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

SETTINGS_FILE = "settings.json" # Will be used when settings UI is re-added

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # self._load_theme_preference() # Will be re-enabled when settings UI is integrated
        self.selected_theme_var = tk.StringVar(value="Light") # Default, will be updated by loaded preference

        # self.configure(bg=theme.BACKGROUND_WINDOW) # Moved to apply_theme
        self.title("Media Downloader and Converter")
        self.geometry("700x500")  # Adjusted size for tabs and shared elements

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
        self.grid_columnconfigure(0, weight=1) 
        self.grid_rowconfigure(0, weight=1) 

        # --- Main Content Frame ---
        main_content_frame = ttk.Frame(self, padding=(10,10)) 
        main_content_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10) 
        main_content_frame.grid_columnconfigure(0, weight=1) 
        # Row configuration for main_content_frame elements:
        # Row 0: self.notebook (tabs) - give some weight for tab area if window very wide
        # Row 1: self.progress_bar
        # Row 2: self.settings_toggle_button (to be added)
        # Row 3: self.settings_frame (collapsible, to be added)
        # Row 4: self.status_text_frame (this should expand most)
        main_content_frame.grid_rowconfigure(0, weight=1) # Notebook will contain expanding cards
        main_content_frame.grid_rowconfigure(1, weight=0) # Progress bar fixed height
        main_content_frame.grid_rowconfigure(2, weight=0) # Settings button fixed height
        main_content_frame.grid_rowconfigure(3, weight=0) # Settings frame (when visible) fixed height
        main_content_frame.grid_rowconfigure(4, weight=1) # Status text area expands

        # --- Notebook for Tabs ---
        self.notebook = ttk.Notebook(main_content_frame)
        self.notebook.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0,10))
        
        # --- Media Download Tab ---
        self.media_tab_frame = ttk.Frame(self.notebook, padding=(10,10))
        self.media_tab_frame.columnconfigure(0, weight=1) # Allow input_frame to expand
        self.notebook.add(self.media_tab_frame, text="Media Download")

        input_frame = ttk.Frame(self.media_tab_frame, padding=(15,15), style='Card.TFrame')
        input_frame.grid(row=0, column=0, sticky="ew") 
        input_frame.columnconfigure(1, weight=1) 

        self.url_label = ttk.Label(input_frame, text="Media URL:", style='InputDescription.TLabel')
        self.url_label.grid(row=0, column=0, padx=(0,10), pady=(0,10), sticky="w")
        
        self.url_var = tk.StringVar() 
        self.url_var.trace_add("write", self._check_url_type)
        self.url_entry = ttk.Entry(input_frame, width=60, textvariable=self.url_var) 
        self.url_entry.grid(row=0, column=1, pady=(0,10), sticky="ew")

        self.format_label = ttk.Label(input_frame, text="Output Format:", style='InputDescription.TLabel')
        self.format_label.grid(row=1, column=0, padx=(0,10), pady=(0,5), sticky="w")
        self.format_options = ["mp4", "mp3", "avi", "mov", "webm"] 
        self.format_var = tk.StringVar(self)
        self.format_var.set(self.format_options[0]) 
        self.format_menu = ttk.OptionMenu(input_frame, self.format_var, self.format_options[0], *self.format_options) 
        self.format_menu.grid(row=1, column=1, pady=(0,5), sticky="ew")

        media_button_config = {
            "text": "Download & Convert",
            "command": self.start_download_and_convert, 
            "style": 'TButton'
        }
        if self.download_icon_image: 
            media_button_config["image"] = self.download_icon_image
            media_button_config["compound"] = 'left'
        
        self.download_media_button = ttk.Button(self.media_tab_frame, **media_button_config) 
        self.download_media_button.grid(row=1, column=0, columnspan=2, pady=15)

        # --- Image Download Tab ---
        self.image_tab_frame = ttk.Frame(self.notebook, padding=(10,10))
        self.image_tab_frame.columnconfigure(0, weight=1) 
        self.notebook.add(self.image_tab_frame, text="Image Download")

        image_input_frame = ttk.Frame(self.image_tab_frame, padding=(15,15), style='Card.TFrame')
        image_input_frame.grid(row=0, column=0, sticky="ew")
        image_input_frame.columnconfigure(1, weight=1)

        self.image_url_label = ttk.Label(image_input_frame, text="Image URL:", style='InputDescription.TLabel')
        self.image_url_label.grid(row=0, column=0, padx=(0,10), pady=(0,10), sticky="w")

        self.image_url_var = tk.StringVar() 
        self.image_url_entry = ttk.Entry(image_input_frame, width=60, textvariable=self.image_url_var)
        self.image_url_entry.grid(row=0, column=1, pady=(0,10), sticky="ew")

        image_button_config = {
            "text": "Download Image",
            "command": self._start_image_download,
            "style": 'TButton'
        }
        if self.download_icon_image: 
            image_button_config["image"] = self.download_icon_image
            image_button_config["compound"] = 'left'

        self.download_image_button = ttk.Button(self.image_tab_frame, **image_button_config)
        self.download_image_button.grid(row=1, column=0, columnspan=2, pady=15)

        # --- Progress Bar (Shared, below notebook) ---
        self.progress_bar = ttk.Progressbar(main_content_frame, orient="horizontal", length=400, mode="determinate") 
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10) 

        # --- Settings UI (placeholder, will be refined) ---
        self.settings_toggle_button = ttk.Button(main_content_frame, text="Settings (Placeholder)", command=self._toggle_settings_frame)
        self.settings_toggle_button.grid(row=2, column=0, columnspan=2, pady=5)
        self.settings_frame = ttk.Frame(main_content_frame, style='Card.TFrame')
        # Settings frame content will be added later. For now, a placeholder label.
        ttk.Label(self.settings_frame, text="Theme selection will go here.").pack(padx=10, pady=10)


        # --- Status Text Frame (Shared, at the bottom) ---
        self.status_text_frame = ttk.Frame(main_content_frame) 
        self.status_text_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0,5)) 
        self.status_text_frame.grid_rowconfigure(0, weight=1)
        self.status_text_frame.grid_columnconfigure(0, weight=1)
        
        self.status_text = tk.Text(self.status_text_frame, 
                                 height=8, # Adjusted height slightly
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
        
        # Apply theme now that all base widgets are created
        self.apply_theme(self.selected_theme_var.get())


    def _load_theme_preference(self): # To be re-enabled when settings UI is complete
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                theme_name = settings.get("theme", "Light")
                if theme_name not in theme.THEMES: # Make sure it's a valid theme
                    theme_name = "Light" 
        except (FileNotFoundError, json.JSONDecodeError):
            theme_name = "Light" # Default if file not found or corrupt
        self.selected_theme_var.set(theme_name)
        # theme.set_current_theme(theme_name) # apply_theme will call this

    def _save_theme_preference(self, theme_name): # To be re-enabled
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump({"theme": theme_name}, f)
        except IOError as e:
            self.update_status(f"Error saving theme: {e}")

    def _toggle_settings_frame(self): # Basic toggle for now
        if self.settings_frame.winfo_ismapped():
            self.settings_frame.grid_remove()
        else:
            self.settings_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 10), padx=0)
            # self.settings_frame.configure(style='Card.TFrame') # Ensure style

    def _on_theme_selected(self): # To be re-enabled and connected
        # selected_theme_name = self.selected_theme_var.get()
        # self.apply_theme(selected_theme_name)
        # self._save_theme_preference(selected_theme_name)
        pass


    def apply_theme(self, theme_name):
        theme.set_current_theme(theme_name)
        self.configure(bg=theme.BACKGROUND_WINDOW)

        style = ttk.Style(self)
        style.configure('.', 
                        font=self.font_body, 
                        background=theme.BACKGROUND_WINDOW, # Default background for widgets
                        foreground=theme.TEXT_PRIMARY)
        style.configure('TLabel', 
                        background=theme.BACKGROUND_WINDOW, # Labels on general background
                        foreground=theme.TEXT_PRIMARY)
        style.configure('InputDescription.TLabel', 
                        background=theme.BACKGROUND_CONTENT, # Labels on card background
                        foreground=theme.TEXT_PRIMARY)
        style.configure('Card.TFrame', 
                        background=theme.BACKGROUND_CONTENT, 
                        relief='raised', borderwidth=1)
        
        # Notebook specific styling
        style.configure('TNotebook', background=theme.BACKGROUND_WINDOW, borderwidth=0)
        style.configure('TNotebook.Tab', 
                        font=self.font_body_bold, 
                        padding=(10, 5),
                        foreground=theme.TEXT_SECONDARY)
        style.map('TNotebook.Tab',
                  background=[('selected', theme.BACKGROUND_CONTENT), ('!selected', theme.BACKGROUND_INPUT)],
                  foreground=[('selected', theme.COLOR_ACCENT), ('!selected', theme.TEXT_SECONDARY)],
                  bordercolor=[('selected', theme.DIVIDER_COLOR), ('!selected', theme.BACKGROUND_INPUT)],
                  lightcolor=[('selected', theme.BACKGROUND_CONTENT)])
        
        style.configure('Tab.TFrame', background=theme.BACKGROUND_WINDOW) # For tab content frames
        if hasattr(self, 'media_tab_frame') and self.media_tab_frame:
            self.media_tab_frame.configure(style='Tab.TFrame')
        if hasattr(self, 'image_tab_frame') and self.image_tab_frame:
            self.image_tab_frame.configure(style='Tab.TFrame')


        style.configure('TButton',
                        font=self.font_button,
                        background=theme.COLOR_ACCENT,
                        foreground=theme.TEXT_ON_ACCENT_COLOR, # Updated variable
                        borderwidth=0, relief='flat', padding=(10, 8))
        style.map('TButton',
                  background=[('active', theme.COLOR_ACCENT_DARK), 
                              ('disabled', theme.BACKGROUND_INPUT)],
                  foreground=[('disabled', theme.TEXT_SECONDARY)]) # Updated variable

        style.configure('TEntry',
                        font=self.font_body,
                        fieldbackground=theme.BACKGROUND_CONTENT,
                        foreground=theme.TEXT_PRIMARY, # Updated variable
                        borderwidth=1, 
                        relief='solid', padding=(5,5))
        if hasattr(self, 'url_entry') and self.url_entry: self.url_entry.configure(insertbackground=theme.TEXT_PRIMARY)
        if hasattr(self, 'image_url_entry') and self.image_url_entry: self.image_url_entry.configure(insertbackground=theme.TEXT_PRIMARY)
        
        style.map('TEntry',
                  bordercolor=[('focus', theme.COLOR_ACCENT)],
                  relief=[('focus', 'solid')])
        style.configure('TMenubutton',
                        font=self.font_body,
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY, # Updated variable
                        relief='flat', padding=(5,5), borderwidth=1)
        style.configure('Horizontal.TProgressbar',
                        background=theme.COLOR_ACCENT,
                        troughcolor=theme.BACKGROUND_INPUT,
                        borderwidth=0, relief='flat')
        
        if hasattr(self, 'status_text'):
            self.status_text.config(bg=theme.BACKGROUND_CONTENT, fg=theme.TEXT_SECONDARY,
                                    insertbackground=theme.TEXT_PRIMARY)
        
        # Settings frame and its contents will be styled via Card.TFrame, TButton, TRadiobutton, etc.
        # if hasattr(self, 'settings_frame'): self.settings_frame.configure(style='Card.TFrame')
        # (Assuming settings_theme_label and radio buttons are styled by their generic types or specific styles)


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


    def start_download_and_convert(self): # For Media Download Tab
        url = self.url_var.get().strip()
        if not url:
            self.update_status("Please enter a media URL in the 'Media Download' tab.")
            self.download_media_button['state'] = 'normal' 
            return

        self.download_media_button['state'] = 'disabled'
        output_format = self.format_var.get()

        # Clear previous status messages
        self.status_text.config(state="normal")
        self.status_text.delete('1.0', tk.END)
        self.status_text.config(state="disabled")
        
        self.progress_bar['value'] = 0
        self.update_status(f"Starting process for URL: {url} to format: {output_format}")

        thread = threading.Thread(target=self._download_and_convert_thread, args=(url, output_format, False))
        thread.daemon = True 
        thread.start()

    def _start_image_download(self):
        url = self.image_url_var.get().strip() 
        if not url:
            self.update_status("Please enter an image URL in the 'Image Download' tab.")
            return

        if not self.downloader._is_direct_image_url(url):
             self.update_status("This URL doesn't look like a direct image. Try the 'Media Download' tab.")
             return

        self.download_image_button['state'] = 'disabled' 

        self.status_text.config(state="normal")
        self.status_text.delete('1.0', tk.END)
        self.status_text.config(state="disabled")
        
        self.progress_bar['value'] = 0
        self.update_status(f"Starting image download: {url}")

        thread = threading.Thread(target=self._download_and_convert_thread, args=(url, None, True))
        thread.daemon = True
        thread.start()

    def _check_url_type(self, *args): # Tied to self.url_var (Media Download Tab)
        url = self.url_var.get().strip()
        if not hasattr(self, 'format_menu') or not hasattr(self, 'download_media_button'): 
            return 

        if not url: 
            self.format_menu.config(state="normal")
            self.download_media_button.config(text="Download & Convert")
            return

        is_image = self.downloader._is_direct_image_url(url)
        
        if is_image:
            self.format_menu.config(state="disabled")
            self.download_media_button.config(text="Image URL? Use Image Tab") 
        else:
            self.format_menu.config(state="normal")
            self.download_media_button.config(text="Download & Convert")


    def _gui_progress_hook(self, data): 
        if data['status'] == 'downloading':
            message_override = data.get('message')
            percentage = data.get('percentage', 0.0)
            total_bytes = data.get('total_bytes', 0) or data.get('total_bytes_estimate', 0)

            if message_override and (percentage == 0 and total_bytes == 0 and not data.get('speed')):
                self.update_status(message_override)
                if data.get('downloaded_bytes') is not None: 
                    self.progress_bar.config(mode='indeterminate')
                    self.progress_bar.start(10)
                else: 
                    self.progress_bar.config(value=0, mode='determinate')
            else: 
                self.progress_bar.config(mode='determinate') 
                self.progress_bar.stop() 

                downloaded_bytes = data.get('downloaded_bytes', 0)
                speed_bytes_sec = data.get('speed', 0)
                eta_seconds = data.get('eta', 0)

                downloaded_str = self._format_bytes(downloaded_bytes)
                total_str = self._format_bytes(total_bytes)
                speed_str = self._format_speed(speed_bytes_sec)
                eta_str = self._format_eta(eta_seconds)
                
                final_percentage = max(0.0, min(100.0, percentage if total_bytes > 0 else 0.0))
                if total_bytes == 0 and downloaded_bytes > 0:
                    status_message = f"Downloading: {downloaded_str} at {speed_str}"
                    self.progress_bar.config(mode='indeterminate') 
                    self.progress_bar.start(10)
                elif total_bytes > 0 :
                     status_message = f"Downloading: {final_percentage:.1f}% ({downloaded_str} / {total_str}) at {speed_str}, ETA: {eta_str}"
                     self.after(0, lambda: self.progress_bar.config(value=final_percentage))
                else: 
                    status_message = "Downloading: Initializing..." 
                    self.after(0, lambda: self.progress_bar.config(value=0))
                self.update_status(status_message)

        elif data['status'] == 'finished':
            self.progress_bar.stop() 
            self.progress_bar.config(mode='determinate')
            # filename = data.get('filename', 'Unknown file') # Filename now used in thread
            self.after(0, lambda: self.progress_bar.config(value=100))
            # Final status message handled by the calling thread method
            pass 

        elif data['status'] == 'error':
            self.progress_bar.stop() 
            self.progress_bar.config(mode='determinate')
            error_message = data.get('message', 'Unknown download error')
            self.update_status(f"Download Error: {error_message}")
            self.after(0, lambda: self.progress_bar.config(value=0))


    def _download_and_convert_thread(self, url, output_format_selected, is_direct_image_download=False):
        active_button = None
        if is_direct_image_download:
            active_button = self.download_image_button 
        else:
            active_button = self.download_media_button
        
        downloaded_file_path = None
        output_file_path = None 
        try:
            self.update_status(f"Fetching URL: {url}")
            
            preferred_format_info = None
            if not is_direct_image_download: 
                preferred_format_info = {'format_id': output_format_selected.lower()}
                self.update_status(f"Requesting format '{output_format_selected.lower()}' from downloader.")

            downloaded_file_path = self.downloader.download_media(
                url, 
                self.download_dir, 
                preferred_format_info=preferred_format_info, 
                progress_callback=self._gui_progress_hook
            )
            
            if not downloaded_file_path or not os.path.exists(downloaded_file_path):
                self.update_status(f"Download failed: File not found at path '{downloaded_file_path}'.")
                # Button re-enabling is handled in finally
                return 

            output_file_path = downloaded_file_path # Default to this if no conversion
            
            if is_direct_image_download:
                self.update_status(f"Image downloaded successfully: {os.path.basename(output_file_path)}")
                # For direct images, this is the final message.
            else:
                # For media downloads, this indicates download part is done, conversion might follow.
                self.update_status(f"Download complete: {os.path.basename(downloaded_file_path)}. Preparing for conversion...")
                self.after(0, lambda: self.progress_bar.config(value=0)) # Reset for conversion
                
                base, orig_ext = os.path.splitext(os.path.basename(downloaded_file_path))
                output_filename_candidate = f"{base}.{output_format_selected.lower()}"
                potential_output_path = os.path.join(self.download_dir, output_filename_candidate)
                
                final_output_path_for_conversion = self._get_unique_filepath(potential_output_path) 
                if final_output_path_for_conversion != potential_output_path: 
                    self.update_status(f"Note: Output file will be saved as {os.path.basename(final_output_path_for_conversion)}.")
                
                output_file_path = final_output_path_for_conversion # This is the path for the *final* output, post-conversion

                if orig_ext.lower().strip('.') == output_format_selected.lower() and \
                   os.path.abspath(downloaded_file_path).lower() == os.path.abspath(final_output_path_for_conversion).lower():
                    self.update_status(f"File is already in {output_format_selected} format.")
                elif orig_ext.lower().strip('.') == output_format_selected.lower(): # Correct format, but maybe renamed
                    self.update_status(f"File is already in {output_format_selected} format. Renaming if necessary...")
                    if os.path.abspath(downloaded_file_path) != os.path.abspath(final_output_path_for_conversion):
                         os.rename(downloaded_file_path, final_output_path_for_conversion)
                         self.update_status(f"File renamed to: {os.path.basename(final_output_path_for_conversion)}")
                else: # Conversion is needed
                    self.update_status(f"Converting {os.path.basename(downloaded_file_path)} to {output_format_selected}...")
                    self.after(0, lambda: self.progress_bar.config(mode='indeterminate'))
                    self.after(0, lambda: self.progress_bar.start(10))

                    converted_file = self.converter.convert_media(downloaded_file_path, final_output_path_for_conversion, output_format_selected)
                    output_file_path = converted_file # Update output_file_path to the path of the converted file
                    
                    self.after(0, lambda: self.progress_bar.stop())
                    self.after(0, lambda: self.progress_bar.config(mode='determinate', value=100))
                    self.update_status(f"Successfully converted to: {os.path.basename(converted_file)}")

                    if os.path.abspath(converted_file) != os.path.abspath(downloaded_file_path) and \
                       os.path.exists(downloaded_file_path): 
                        try:
                            os.remove(downloaded_file_path) 
                            self.update_status(f"Removed temporary downloaded file: {os.path.basename(downloaded_file_path)}")
                        except OSError as e:
                            self.update_status(f"Error removing temporary file: {str(e)}")
                
                # This is the final message for the media download path, after any conversion/renaming.
                self.update_status(f"Process completed. Final file: {os.path.basename(output_file_path)}")

        except DownloadError as e:
            self.update_status(f"Download Error: {str(e)}.")
        except ConversionError as e:
            self.update_status(f"Conversion Error: {str(e)}.")
            if downloaded_file_path and os.path.exists(downloaded_file_path): 
                 self.update_status(f"Original downloaded file kept: {os.path.basename(downloaded_file_path)}")
        except FileNotFoundError as e: 
            self.update_status(f"Error: File not found. {str(e)}")
        except Exception as e:
            self.update_status(f"An unexpected error occurred: {type(e).__name__} - {str(e)}.")
        finally:
            if active_button:
                self.after(0, lambda: active_button.config(state='normal'))
            
            self.after(0, lambda: self.progress_bar.stop()) 
            final_progress_val = 0
            if output_file_path and os.path.exists(output_file_path): 
                final_progress_val = 100
            self.after(0, lambda: self.progress_bar.config(mode='determinate', value=final_progress_val))


if __name__ == "__main__":
    app = App()
    app.mainloop()
