import tkinter as tk
from tkinter import ttk, PhotoImage
import os
import threading
import json # For theme persistence
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

SETTINGS_FILE = "settings.json"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self._load_theme_preference() # Load theme before any UI is built

        # Initialize self.settings_window to None
        self.settings_window = None
        self.settings_theme_frame = None
        self.settings_theme_label = None
        self.settings_light_theme_rb = None
        self.settings_dark_theme_rb = None

        # self.configure(bg=theme.BACKGROUND_WINDOW) # Moved to apply_theme
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
        self.grid_rowconfigure(0, weight=1) # main_content_frame is in row 0 and should expand

        # --- Main Content Frame ---
        # Adjusted main_content_frame pady to (10,10) for some bottom padding as well
        main_content_frame = ttk.Frame(self, padding=(10,10)) 
        main_content_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10) 
        main_content_frame.grid_columnconfigure(0, weight=1) # Allow content within to expand
        # Row configuration for main_content_frame elements:
        # Row 0: input_frame
        # Row 1: download_button
        # Row 2: progress_bar
        # Row 3: settings_button
        # Row 4: status_text_frame (this should expand)
        main_content_frame.grid_rowconfigure(4, weight=1) # Ensure status area (row 4) expands

        # --- Input Frame for URL and Format (Card-like) ---
        input_frame = ttk.Frame(main_content_frame, padding=(15,15), style='Card.TFrame')
        # Added pady=10 for consistent vertical spacing around this card
        input_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=10) 
        input_frame.grid_columnconfigure(1, weight=1) # Allow entry and menu to expand within this frame

        # Media URL
        self.url_label = ttk.Label(input_frame, text="Media URL:", style='InputDescription.TLabel')
        self.url_label.grid(row=0, column=0, padx=(0,10), pady=(0,10), sticky="w")
        
        self.url_var = tk.StringVar()
        self.url_var.trace_add("write", self._check_url_type)
        self.url_entry = ttk.Entry(input_frame, width=60, textvariable=self.url_var) 
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
        # Row index for status_text_frame is 4, set by settings_button addition. pady is fine.
        self.status_text_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0,5)) 
        self.status_text_frame.grid_rowconfigure(0, weight=1)
        self.status_text_frame.grid_columnconfigure(0, weight=1)
        
        # main_content_frame.grid_rowconfigure(4, weight=1) is now set above where main_content_frame rows are listed

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

        # --- Settings Button ---
        self.settings_button = ttk.Button(
            main_content_frame, # Placed in main_content_frame for similar padding
            text="Settings",
            command=self.open_settings_window,
            style='TButton' # Apply standard button styling
        )
        # Place it below the progress bar and above the status text area.
        # Adjust row numbers for elements below if necessary (e.g. status_text_frame)
        self.settings_button.grid(row=3, column=0, columnspan=2, pady=10) # This is row 3 of main_content_frame

        # status_text_frame is already correctly placed at row 4 after settings_button by prior diffs
        # self.status_text_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0,5))
        # main_content_frame.grid_rowconfigure(4, weight=1) is set where main_content_frame rows are defined
        
        # Apply initial theme to all components after they are created
        self.apply_theme(theme._current_theme_name) 
        self.update_status("Ready. Enter a URL and select a format.")

    def _load_theme_preference(self):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                theme_name = settings.get("theme", "Light")
                if theme_name not in theme.THEMES:
                    theme_name = "Light" # Fallback for invalid theme name
        except (FileNotFoundError, json.JSONDecodeError):
            theme_name = "Light" # Default if file not found or corrupt
        theme.set_current_theme(theme_name)

    def _save_theme_preference(self, theme_name):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump({"theme": theme_name}, f)
        except IOError as e:
            self.update_status(f"Error saving theme: {e}")

    def apply_theme(self, theme_name):
        theme.set_current_theme(theme_name)
        
        # Re-configure main window
        self.configure(bg=theme.BACKGROUND_WINDOW)

        # Re-configure ttk styles
        style = ttk.Style(self)
        style.configure('.', 
                        font=self.font_body,
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY, # Changed from TEXT_PRIMARY_ON_LIGHT
                        padding=(5, 5))
        style.configure('TLabel', 
                        font=self.font_body,
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY, # Changed
                        padding=(5,5))
        style.configure('InputDescription.TLabel', 
                        font=self.font_body,
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY) # Changed
        style.configure('Card.TFrame', 
                        background=theme.BACKGROUND_CONTENT, 
                        relief='raised', borderwidth=1)
        style.configure('TButton',
                        font=self.font_button,
                        background=theme.COLOR_ACCENT,
                        foreground=theme.TEXT_ON_ACCENT_COLOR, # Using new theme var
                        borderwidth=0, relief='flat', padding=(10, 8))
        style.map('TButton',
                  background=[('active', theme.COLOR_ACCENT_DARK), 
                              ('disabled', theme.BACKGROUND_INPUT)],
                  foreground=[('disabled', theme.TEXT_SECONDARY)]) # Changed
        style.configure('TEntry',
                        font=self.font_body,
                        fieldbackground=theme.BACKGROUND_CONTENT,
                        foreground=theme.TEXT_PRIMARY, # Changed
                        borderwidth=1, relief='solid', padding=(5,5))
        self.url_entry.configure(insertbackground=theme.TEXT_PRIMARY) # Update insert color
        # TODO: Apply insertbackground for other TEntry widgets if any are added
        style.map('TEntry',
                  bordercolor=[('focus', theme.COLOR_ACCENT)],
                  relief=[('focus', 'solid')])
        style.configure('TMenubutton',
                        font=self.font_body,
                        background=theme.BACKGROUND_CONTENT, 
                        foreground=theme.TEXT_PRIMARY, # Changed
                        relief='flat', padding=(5,5), borderwidth=1)
        style.configure('Horizontal.TProgressbar',
                        background=theme.COLOR_ACCENT,
                        troughcolor=theme.BACKGROUND_INPUT,
                        borderwidth=0, relief='flat')
        
        # Re-configure specific tk widgets
        if hasattr(self, 'status_text'): # Check if status_text is initialized
            self.status_text.config(bg=theme.BACKGROUND_CONTENT, fg=theme.TEXT_SECONDARY,
                                    insertbackground=theme.TEXT_PRIMARY) # Added insertbackground
        
        # Update Settings Window if it's open
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.configure(bg=theme.BACKGROUND_WINDOW)
            # Need a specific style for settings window card frame if it differs from main Card.TFrame
            style.configure('SettingsWindow.Card.TFrame', background=theme.BACKGROUND_CONTENT)
            if self.settings_theme_frame:
                 self.settings_theme_frame.configure(style='SettingsWindow.Card.TFrame')
            if self.settings_theme_label:
                self.settings_theme_label.configure(background=theme.BACKGROUND_CONTENT, foreground=theme.TEXT_PRIMARY)
            
            # Update Radiobuttons style
            # This is important for indicator color and text
            style.configure('TRadiobutton', 
                            font=self.font_body,
                            background=theme.BACKGROUND_CONTENT, 
                            foreground=theme.TEXT_PRIMARY)
            style.map('TRadiobutton',
                  background=[('active', theme.BACKGROUND_CONTENT)], 
                  indicatorcolor=[('selected', theme.COLOR_ACCENT), ('!selected', theme.TEXT_SECONDARY)])
            # Force refresh on radiobuttons if needed (sometimes style changes don't auto-propagate)
            if self.settings_light_theme_rb: self.settings_light_theme_rb.style = 'TRadiobutton'
            if self.settings_dark_theme_rb: self.settings_dark_theme_rb.style = 'TRadiobutton'

    def _check_url_type(self, *args):
        url = self.url_var.get().strip()
        if not url: # Empty URL, reset to default state
            self.format_menu.config(state="normal")
            self.download_button.config(text="Download & Convert")
            # Optionally clear any specific status messages related to URL type
            return

        is_image = self.downloader._is_direct_image_url(url) # Use the method from Downloader
        
        if is_image:
            self.format_menu.config(state="disabled")
            self.download_button.config(text="Download Image")
            # self.update_status("Image URL detected. Output format will be its original format.")
        else:
            self.format_menu.config(state="normal")
            self.download_button.config(text="Download & Convert")
            # self.update_status("URL type recognized for general media processing.")


    def _on_theme_selected(self):
        selected_theme_name = self.selected_theme_var.get()
        self.apply_theme(selected_theme_name)
        self._save_theme_preference(selected_theme_name)


    def _on_settings_window_destroy(self, event):
        # Check if the event is for the settings_window itself
        if event.widget == self.settings_window:
            self.settings_window = None
            self.settings_theme_frame = None
            self.settings_theme_label = None
            self.settings_light_theme_rb = None
            self.settings_dark_theme_rb = None

    def open_settings_window(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return

        self.settings_window = tk.Toplevel(self)
        self.settings_window.title("Settings")
        self.settings_window.geometry("400x300")
        self.settings_window.configure(bg=theme.BACKGROUND_WINDOW)
        self.settings_window.grab_set()
        self.settings_window.transient(self)
        self.settings_window.bind("<Destroy>", self._on_settings_window_destroy)


        # --- Theme Selection UI ---
        self.settings_theme_frame = ttk.Frame(self.settings_window, padding=(10, 10), style='SettingsWindow.Card.TFrame')
        self.settings_theme_frame.pack(padx=20, pady=20, fill="x", expand=False)
        
        # Ensure SettingsWindow.Card.TFrame is configured with current theme colors when window opens
        s = ttk.Style(self) # Use existing style instance from App
        s.configure('SettingsWindow.Card.TFrame', background=theme.BACKGROUND_CONTENT)
        self.settings_theme_frame.configure(style='SettingsWindow.Card.TFrame')


        self.settings_theme_label = ttk.Label(
            self.settings_theme_frame, 
            text="Select Theme:",
            font=self.font_body_bold,
            background=theme.BACKGROUND_CONTENT,
            foreground=theme.TEXT_PRIMARY
        )
        self.settings_theme_label.pack(pady=(0, 10), anchor="w")

        self.selected_theme_var = tk.StringVar(value=theme._current_theme_name) 

        self.settings_light_theme_rb = ttk.Radiobutton(
            self.settings_theme_frame,
            text="Light Theme",
            variable=self.selected_theme_var,
            value="Light",
            command=self._on_theme_selected, 
            style='TRadiobutton'
        )
        self.settings_light_theme_rb.pack(anchor="w", padx=10)

        self.settings_dark_theme_rb = ttk.Radiobutton(
            self.settings_theme_frame,
            text="Dark Theme",
            variable=self.selected_theme_var,
            value="Dark",
            command=self._on_theme_selected, 
            style='TRadiobutton'
        )
        self.settings_dark_theme_rb.pack(anchor="w", padx=10, pady=(0,5))
        
        # Apply current theme to radio buttons inside settings
        s.configure('TRadiobutton', 
                    font=self.font_body,
                    background=theme.BACKGROUND_CONTENT, 
                    foreground=theme.TEXT_PRIMARY)
        s.map('TRadiobutton',
              background=[('active', theme.BACKGROUND_CONTENT)],
              indicatorcolor=[('selected', theme.COLOR_ACCENT), ('!selected', theme.TEXT_SECONDARY)])

        # Center the settings window relative to the main app window
        self.settings_window.update_idletasks() 
        main_x = self.winfo_x()
        main_y = self.winfo_y()
        main_width = self.winfo_width()
        main_height = self.winfo_height()

        s_width = self.settings_window.winfo_width()
        s_height = self.settings_window.winfo_height()
        
        if s_width == 1 or s_height == 1: # Window not drawn yet, use requested size
            try:
                geom_parts = self.settings_window.geometry().split('x') # "400x300" or "400x300+X+Y"
                s_width = int(geom_parts[0])
                s_height = int(geom_parts[1].split('+')[0])
            except (ValueError, IndexError):
                 s_width, s_height = 400, 300 # Fallback

        center_x = main_x + (main_width - s_width) // 2
        center_y = main_y + (main_height - s_height) // 2
        self.settings_window.geometry(f"+{center_x}+{center_y}")


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
            # Handle specific messages for simple downloads (like images)
            message_override = data.get('message')
            percentage = data.get('percentage', 0.0)
            total_bytes = data.get('total_bytes', 0) or data.get('total_bytes_estimate', 0) # yt-dlp might use estimate

            if message_override and (percentage == 0 and total_bytes == 0 and not data.get('speed')):
                # This is likely a simple status message (e.g., "Downloading image...")
                self.update_status(message_override)
                if data.get('downloaded_bytes') is not None: # If we have downloaded bytes info, show indeterminate progress
                    self.progress_bar.config(mode='indeterminate')
                    self.progress_bar.start(10)
                else: # For the very first message without byte info yet
                    self.progress_bar.config(value=0, mode='determinate')

            else: # Standard detailed progress for yt-dlp or image download with byte counts
                self.progress_bar.config(mode='determinate') # Ensure determinate mode
                self.progress_bar.stop() # Stop if it was indeterminate

                downloaded_bytes = data.get('downloaded_bytes', 0)
                speed_bytes_sec = data.get('speed', 0)
                eta_seconds = data.get('eta', 0)

                downloaded_str = self._format_bytes(downloaded_bytes)
                total_str = self._format_bytes(total_bytes)
                speed_str = self._format_speed(speed_bytes_sec)
                eta_str = self._format_eta(eta_seconds)
                
                final_percentage = max(0.0, min(100.0, percentage if total_bytes > 0 else 0.0))
                # If total_bytes is 0 but downloaded_bytes is positive (e.g. direct image chunk download without total size initially)
                # we can't show a real percentage. Show indeterminate or just downloaded amount.
                if total_bytes == 0 and downloaded_bytes > 0:
                    status_message = f"Downloading: {downloaded_str} at {speed_str}"
                    self.progress_bar.config(mode='indeterminate') # Or keep it determinate at 0 if preferred
                    self.progress_bar.start(10)
                elif total_bytes > 0 :
                     status_message = f"Downloading: {final_percentage:.1f}% ({downloaded_str} / {total_str}) at {speed_str}, ETA: {eta_str}"
                     self.after(0, lambda: self.progress_bar.config(value=final_percentage))
                else: # total_bytes and downloaded_bytes are 0, but not a simple message_override
                    status_message = "Downloading: Initializing..." # Or some other generic message
                    self.after(0, lambda: self.progress_bar.config(value=0))
                
                self.update_status(status_message)

        elif data['status'] == 'finished':
            self.progress_bar.stop() # Stop if it was indeterminate
            self.progress_bar.config(mode='determinate')
            filename = data.get('filename', 'Unknown file')
            self.after(0, lambda: self.progress_bar.config(value=100))
            
            # Determine if it was an image download to adjust message
            if self.downloader._is_direct_image_url(self.url_var.get().strip()): # Check current URL
                self.update_status(f"Image downloaded: {os.path.basename(filename)}")
            else:
                self.update_status(f"Download finished: {os.path.basename(filename)}. Preparing for conversion...")
        
        elif data['status'] == 'error':
            self.progress_bar.stop() # Stop if it was indeterminate
            self.progress_bar.config(mode='determinate')
            error_message = data.get('message', 'Unknown download error')
            self.update_status(f"Download Error: {error_message}")
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
