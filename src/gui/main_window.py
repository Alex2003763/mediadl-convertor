import customtkinter as ctk
import tkinter as tk # Keep tk for PhotoImage and messagebox
from tkinter import messagebox # Keep messagebox
import os
import threading
import json 
import re 
from tkinter import filedialog 
from PIL import Image, ImageTk # Import Pillow modules
import io # For handling image data
import base64 # Import the base64 module
import ffmpeg # Import ffmpeg for thumbnail generation
import sys
import subprocess # For _play_video_file fallback and vlc process check
try:
    import vlc
except ImportError:
    vlc = None # Will be checked later

# Ensure the script can find the core package when run directly
if __name__ == "__main__" and __package__ is None:
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from src.core.downloader import Downloader, DownloadError
from src.core.converter import Converter, ConversionError
from . import theme 

SETTINGS_FILE = "settings.json" 

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.selected_theme_var = ctk.StringVar(value="System") # Default to System theme
        self.video_download_dir_var = ctk.StringVar()
        self.image_download_dir_var = ctk.StringVar()
        self.default_format_var = ctk.StringVar(value="mp4") 

        self.title("Media Downloader & Converter")
        self.geometry("750x650") # Slightly taller for playback controls

        # Set CustomTkinter default theme and color scheme
        ctk.set_appearance_mode("System") # Default to system theme
        ctk.set_default_color_theme("blue") # Default color theme

        # --- Icon Loading ---
        self.download_icon_image = None 
        self.fetch_icon_image = None 
        self.app_icon_image_tk = None 
        self._app_icon_pil_ref = None 
        self.update_status("Loading application icons...")
        
        try:
            download_icon_pil = Image.open(io.BytesIO(base64.b64decode(theme.DOWNLOAD_ICON_BASE64)))
            fetch_icon_pil = Image.open(io.BytesIO(base64.b64decode(theme.FETCH_ICON_BASE64)))
            self._app_icon_pil_ref = Image.open("assets/icons8-video-download-64.png")
            
            if self._app_icon_pil_ref.mode != 'RGBA':
                self._app_icon_pil_ref = self._app_icon_pil_ref.convert('RGBA')
            app_icon_resized_pil = self._app_icon_pil_ref.resize((64, 64), Image.LANCZOS)
            ico_path = "assets/app_icon.ico"
            try:
                app_icon_resized_pil.save(ico_path, format="ICO")
            except Exception as e:
                self.update_status(f"Error saving ICO file: {e}")
                ico_path = None

            self.download_icon_image = ctk.CTkImage(light_image=download_icon_pil, dark_image=download_icon_pil, size=(16, 16))
            self.fetch_icon_image = ctk.CTkImage(light_image=fetch_icon_pil, dark_image=fetch_icon_pil, size=(16, 16))
            
            if ico_path:
                self.after(201, lambda: self._set_window_icon_from_file(ico_path))
            else:
                self.app_icon_image_tk = ImageTk.PhotoImage(app_icon_resized_pil)
                self.after_idle(lambda: self._set_window_icon_from_photo(self.app_icon_image_tk))
            self.update_status("Application icons loaded successfully")
        except Exception as e:
            self.update_status(f"Error loading icons: {str(e)}")

        # --- Core components & UI Variables ---
        self.downloader = Downloader()
        self.converter = Converter()
        self.format_options = ["mp4", "mp3", "webm", "avi", "mov", "gif"] # Initialized before _load_settings
        self._load_settings() 
        for dir_var in [self.video_download_dir_var, self.image_download_dir_var]:
            if dir_var.get(): os.makedirs(dir_var.get(), exist_ok=True)

        self.url_var = ctk.StringVar()
        self.image_url_var = ctk.StringVar()
        self.resolution_var = ctk.StringVar()
        self.available_resolutions_data = []
        self.converter_input_file_var = ctk.StringVar()
        self.converter_output_format_var = ctk.StringVar()
        self.download_thread = None
        self.conversion_thread = None
        
        self.trim_start_seconds_var = ctk.DoubleVar(value=0.0)
        self.trim_end_seconds_var = ctk.DoubleVar(value=0.0)
        self.video_duration_seconds = 0.0
        self.gif_fps_var = ctk.StringVar(value="10")
        self.gif_scale_width_var = ctk.StringVar(value="480")

        # VLC Player related attributes
        self.vlc_instance = None
        self.vlc_player = None
        self.vlc_media = None
        self.is_vlc_available = False
        self._init_vlc() 
        if self.is_vlc_available:
            self._setup_vlc_event_handlers()
        self.protocol("WM_DELETE_WINDOW", self._on_app_closing)

        # --- Main Layout ---
        self.grid_columnconfigure(0, weight=1) 
        self.grid_rowconfigure(0, weight=1) 
        main_content_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main_content_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10) 
        main_content_frame.grid_columnconfigure(0, weight=1) 
        main_content_frame.grid_rowconfigure(0, weight=1) 
        main_content_frame.grid_rowconfigure(1, weight=0) 
        main_content_frame.grid_rowconfigure(2, weight=2)

        self.tabview = ctk.CTkTabview(main_content_frame)
        self.tabview.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(0, 15))
        
        self._create_media_download_tab()
        self._create_image_download_tab()
        self._create_video_converter_tab()
        self._create_settings_tab() 

        self.progress_bar = ctk.CTkProgressBar(main_content_frame, orientation="horizontal") 
        self.progress_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(15, 10))
        self.progress_bar.set(0)

        self.status_text = ctk.CTkTextbox(main_content_frame, height=10, state="disabled", wrap="word") 
        self.status_text.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(10,0))
            
        self.after_idle(lambda: self.update_status("Ready."))
        self.after_idle(lambda: self.apply_theme(self.selected_theme_var.get()))
        self.after_idle(lambda: self.url_var.trace_add("write", self._on_url_changed))
        self.after_idle(lambda: self.default_format_var.trace_add("write", self._on_setting_changed))

        self.tabview.configure(segmented_button_fg_color=self.tabview._apply_appearance_mode(self.tabview.cget("fg_color")))
        for i in range(4): self.tabview._segmented_button.grid_columnconfigure(i, weight=0)
        self.tabview._segmented_button.grid_columnconfigure(4, weight=1)

    def _set_window_icon_from_file(self, icon_path):
        try:
            full_icon_path = os.path.abspath(icon_path)
            self.iconbitmap(full_icon_path)
        except Exception as e:
            self.update_status(f"Error setting window icon from file: {str(e)}")

    def _set_window_icon_from_photo(self, photo_image):
        try:
            self.iconphoto(True, photo_image)
        except Exception as e:
            self.update_status(f"Error setting window icon from PhotoImage: {str(e)}")

    def _create_media_download_tab(self):
        self.media_tab_frame = self.tabview.add("Media Download")
        self.tabview.tab("Media Download").grid_columnconfigure(0, weight=1) 
        input_frame = ctk.CTkFrame(self.tabview.tab("Media Download"))
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0,15)) 
        input_frame.grid_columnconfigure(1, weight=1) 
        input_frame.grid_columnconfigure(2, weight=0) 
        ctk.CTkLabel(input_frame, text="Media URL:").grid(row=0, column=0, padx=(0,10), pady=(5,10), sticky="w")
        self.url_entry = ctk.CTkEntry(input_frame, textvariable=self.url_var) 
        self.url_entry.grid(row=0, column=1, padx=(0,10), pady=(5,10), sticky="ew")
        fetch_button_config = {"text": "Fetch Resolutions", "command": self._start_fetch_resolutions_thread}
        if self.fetch_icon_image: fetch_button_config.update({"image": self.fetch_icon_image, "compound": 'left'})
        self.fetch_resolutions_button = ctk.CTkButton(input_frame, **fetch_button_config)
        self.fetch_resolutions_button.grid(row=0, column=2, pady=(5,10), sticky="e")
        ctk.CTkLabel(input_frame, text="Resolution:").grid(row=1, column=0, padx=(0,10), pady=(5,10), sticky="w")
        self.resolution_combobox = ctk.CTkComboBox(input_frame, variable=self.resolution_var, state="disabled", values=["Fetch resolutions first"])
        self.resolution_combobox.grid(row=1, column=1, columnspan=2, pady=(5,10), sticky="ew")
        self.resolution_combobox.set("Fetch resolutions first")
        media_button_config = {"text": "Download", "command": self._start_download_thread}
        if self.download_icon_image: media_button_config.update({"image": self.download_icon_image, "compound": 'left'})
        self.download_media_button = ctk.CTkButton(self.tabview.tab("Media Download"), **media_button_config) 
        self.download_media_button.grid(row=1, column=0, pady=(20,10), sticky="w") 
        self.stop_download_button = ctk.CTkButton(self.tabview.tab("Media Download"), text="Stop Download", command=self._stop_download, state="disabled")
        self.stop_download_button.grid(row=1, column=0, pady=(20,10), padx=(150,0), sticky="w") 

    def _start_download_thread(self):
        url = self.url_var.get().strip()
        if not url: self.update_status("Please enter a media URL."); return
        self.download_media_button.configure(state='disabled')
        self.stop_download_button.configure(state='normal') 
        selected_resolution_display_text = self.resolution_var.get()
        preferred_download_format = next((res.get('ext') for res in self.available_resolutions_data if res['display_text'] == selected_resolution_display_text), None) if selected_resolution_display_text != "Auto (Best for selected format)" else None
        self.update_status(f"Starting download for URL: {url}")
        format_id_for_download = preferred_download_format
        status_msg = f"Selected stream: {selected_resolution_display_text}" if selected_resolution_display_text != "Auto (Best for selected format)" and preferred_download_format else "Auto stream selection (best quality)."
        self.update_status(status_msg)
        self.download_thread = threading.Thread(target=self._download_and_convert_thread, args=(url, format_id_for_download, selected_resolution_display_text, False, True)) 
        self.download_thread.daemon = True 
        self.download_thread.start()

    def _stop_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.downloader.stop_download() 
            self.update_status("Stopping download...")
            self.download_media_button.configure(state='normal')
            self.stop_download_button.configure(state='disabled')
        else: self.update_status("No active download to stop.")

    def _create_image_download_tab(self):
        self.image_tab_frame = self.tabview.add("Image Download")
        self.tabview.tab("Image Download").grid_columnconfigure(0, weight=1) 
        image_input_frame = ctk.CTkFrame(self.tabview.tab("Image Download"))
        image_input_frame.grid(row=0, column=0, sticky="ew", pady=(0,15))
        image_input_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(image_input_frame, text="Image URL:").grid(row=0, column=0, padx=(0,10), pady=(5,10), sticky="w")
        self.image_url_entry = ctk.CTkEntry(image_input_frame, textvariable=self.image_url_var)
        self.image_url_entry.grid(row=0, column=1, pady=(5,10), sticky="ew")
        image_button_config = {"text": "Download Image", "command": self._start_image_download}
        if self.download_icon_image: image_button_config.update({"image": self.download_icon_image, "compound": 'left'})
        self.download_image_button = ctk.CTkButton(self.tabview.tab("Image Download"), **image_button_config)
        self.download_image_button.grid(row=1, column=0, pady=(20,10))

    def _create_video_converter_tab(self):
        converter_tab = self.tabview.add("Video Converter")
        converter_tab.grid_columnconfigure(0, weight=1)
        converter_main_frame = ctk.CTkFrame(converter_tab, fg_color="transparent")
        converter_main_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 15))
        converter_main_frame.grid_columnconfigure(0, weight=3) 
        converter_main_frame.grid_columnconfigure(1, weight=2) 
        converter_main_frame.grid_rowconfigure(0, weight=1) 
        options_area_frame = ctk.CTkFrame(converter_main_frame, fg_color="transparent")
        options_area_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15)) 
        options_area_frame.grid_columnconfigure(1, weight=1) 
        options_area_frame.grid_columnconfigure(2, weight=0) 
        ctk.CTkLabel(options_area_frame, text="Input File:").grid(row=0, column=0, padx=(0,10), pady=(5,10), sticky="w")
        self.converter_input_entry = ctk.CTkEntry(options_area_frame, textvariable=self.converter_input_file_var, state="readonly")
        self.converter_input_entry.grid(row=0, column=1, padx=(0,10), pady=(5,10), sticky="ew")
        ctk.CTkButton(options_area_frame, text="Browse...", command=self._browse_input_file_for_conversion).grid(row=0, column=2, pady=(5,10), sticky="e")
        self.converter_input_file_var.trace_add("write", self._on_converter_input_file_changed)
        self.play_video_button = ctk.CTkButton(options_area_frame, text="Play Video", command=self._play_video_file, state="disabled")
        self.play_video_button.grid(row=0, column=3, padx=(10,0), pady=(5,10), sticky="e") 
        ctk.CTkLabel(options_area_frame, text="Output Format:").grid(row=1, column=0, padx=(0,10), pady=(5,10), sticky="w")
        self.converter_format_menu = ctk.CTkOptionMenu(options_area_frame, variable=self.converter_output_format_var, values=self.format_options, command=self._on_converter_format_changed)
        self.converter_format_menu.grid(row=1, column=1, columnspan=2, pady=(5,10), sticky="ew")
        if self.format_options: self.converter_output_format_var.set(self.format_options[0])
        trim_sliders_frame = ctk.CTkFrame(options_area_frame, fg_color="transparent")
        trim_sliders_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 5)) 
        trim_sliders_frame.grid_columnconfigure(1, weight=1) 
        trim_sliders_frame.grid_columnconfigure(2, weight=0) 
        ctk.CTkLabel(trim_sliders_frame, text="Start Time:").grid(row=0, column=0, padx=(0, 5), pady=(5,2), sticky="w")
        self.trim_start_slider = ctk.CTkSlider(trim_sliders_frame, from_=0, to=100, variable=self.trim_start_seconds_var, command=self._on_start_trim_slider_changed, state="disabled")
        self.trim_start_slider.grid(row=0, column=1, padx=(0,5), pady=(5,2), sticky="ew")
        self.trim_start_display_label = ctk.CTkLabel(trim_sliders_frame, text="00:00:00", width=60) 
        self.trim_start_display_label.grid(row=0, column=2, padx=(0,10), pady=(5,2), sticky="w")
        ctk.CTkLabel(trim_sliders_frame, text="End Time:").grid(row=1, column=0, padx=(0, 5), pady=(2,5), sticky="w")
        self.trim_end_slider = ctk.CTkSlider(trim_sliders_frame, from_=0, to=100, variable=self.trim_end_seconds_var, command=self._on_end_trim_slider_changed, state="disabled")
        self.trim_end_slider.grid(row=1, column=1, padx=(0,5), pady=(2,5), sticky="ew")
        self.trim_end_display_label = ctk.CTkLabel(trim_sliders_frame, text="00:00:00", width=60) 
        self.trim_end_display_label.grid(row=1, column=2, padx=(0,10), pady=(2,5), sticky="w")
        self.gif_options_frame = ctk.CTkFrame(options_area_frame, fg_color="transparent")
        self.gif_options_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0,0)) 
        self.gif_options_frame.grid_columnconfigure(1, weight=1) 
        self.gif_fps_label = ctk.CTkLabel(self.gif_options_frame, text="GIF FPS:")
        self.gif_fps_label.grid(row=0, column=0, padx=(0,10), pady=(5,5), sticky="w") 
        self.gif_fps_entry = ctk.CTkEntry(self.gif_options_frame, textvariable=self.gif_fps_var)
        self.gif_fps_entry.grid(row=0, column=1, columnspan=2, pady=(5,5), sticky="ew")
        self.gif_scale_label = ctk.CTkLabel(self.gif_options_frame, text="GIF Scale Width (px):")
        self.gif_scale_label.grid(row=1, column=0, padx=(0,10), pady=(5,5), sticky="w") 
        self.gif_scale_entry = ctk.CTkEntry(self.gif_options_frame, textvariable=self.gif_scale_width_var)
        self.gif_scale_entry.grid(row=1, column=1, columnspan=2, pady=(5,5), sticky="ew")
        self._toggle_gif_options_visibility(False) 
        ctk.CTkLabel(options_area_frame, text="Threads:").grid(row=4, column=0, padx=(0,10), pady=(5,10), sticky="w")
        self.converter_threads_var = ctk.StringVar(value="0") 
        self.converter_threads_entry = ctk.CTkEntry(options_area_frame, textvariable=self.converter_threads_var)
        self.converter_threads_entry.grid(row=4, column=1, columnspan=2, pady=(5,10), sticky="ew")
        ctk.CTkLabel(options_area_frame, text="Preset (Video):").grid(row=5, column=0, padx=(0,10), pady=(5,10), sticky="w")
        self.converter_preset_var = ctk.StringVar(value="fast") 
        self.converter_preset_options = ["ultrafast", "superfast", "fast", "medium", "slow", "slower", "veryslow"]
        self.converter_preset_menu = ctk.CTkOptionMenu(options_area_frame, variable=self.converter_preset_var, values=self.converter_preset_options)
        self.converter_preset_menu.grid(row=5, column=1, columnspan=2, pady=(5,10), sticky="ew")
        self.video_preview_frame = ctk.CTkFrame(converter_main_frame, width=250, height=180, fg_color="gray25") 
        self.video_preview_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=(5,0)) 
        self.video_preview_frame.grid_propagate(False) 
        self.video_preview_frame.grid_columnconfigure(0, weight=1)
        self.video_preview_frame.grid_rowconfigure(0, weight=1)
        self.preview_image_label = ctk.CTkLabel(self.video_preview_frame, text="No Video Selected", text_color="gray70", wraplength=230)
        self.preview_image_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.preview_image_tk = None 
        self.playback_controls_frame = ctk.CTkFrame(converter_main_frame, fg_color="transparent")
        self.playback_controls_frame.grid(row=1, column=1, sticky="ew", padx=(0,0), pady=(5,0))
        self.playback_controls_frame.grid_columnconfigure(0, weight=1) 
        self._create_playback_controls() 
        conversion_buttons_frame = ctk.CTkFrame(converter_tab, fg_color="transparent")
        conversion_buttons_frame.grid(row=1, column=0, sticky="ew", pady=(20,10)) 
        convert_button_config = { "text": "Convert File", "command": self._start_conversion_thread }
        self.convert_file_button = ctk.CTkButton(conversion_buttons_frame, **convert_button_config)
        self.convert_file_button.pack(side="left", padx=(0,10))
        self.stop_conversion_button = ctk.CTkButton(conversion_buttons_frame, text="Stop Conversion", command=self._stop_conversion, state="disabled")
        self.stop_conversion_button.pack(side="left")

    def _init_vlc(self):
        if vlc:
            try:
                vlc_args = []
                if sys.platform == "win32": vlc_args.extend(['--no-qt-error-dialogs', '--no-skins2-error-dialogs', '--ignore-config'])
                self.vlc_instance = vlc.Instance(vlc_args)
                self.vlc_player = self.vlc_instance.media_player_new()
                self.is_vlc_available = True
                self.update_status("VLC initialized successfully for in-app playback.")
                if not self.vlc_instance.vlc_version(): raise vlc.VLCException("VLC version check failed.")
            except vlc.VLCException as e:
                self.vlc_instance = self.vlc_player = None; self.is_vlc_available = False
                self.update_status(f"Warning: VLC not found or failed to initialize: {e}. In-app playback disabled.")
            except Exception as e:
                self.vlc_instance = self.vlc_player = None; self.is_vlc_available = False
                self.update_status(f"Unexpected error initializing VLC: {e}. In-app playback disabled.")
        else:
            self.is_vlc_available = False
            self.update_status("VLC library (python-vlc) not installed. In-app playback disabled.")

    def _create_playback_controls(self):
        self.vlc_seek_slider_var = ctk.DoubleVar(value=0.0)
        self.vlc_seek_slider = ctk.CTkSlider(self.playback_controls_frame, from_=0, to=100, variable=self.vlc_seek_slider_var, command=self._on_vlc_seek_slider_dragged, state="disabled")
        self.vlc_seek_slider.grid(row=0, column=0, columnspan=4, sticky="ew", padx=5, pady=(0,5))
        buttons_sub_frame = ctk.CTkFrame(self.playback_controls_frame, fg_color="transparent")
        buttons_sub_frame.grid(row=1, column=0, columnspan=4, sticky="ew")
        self.vlc_play_pause_button = ctk.CTkButton(buttons_sub_frame, text="Play", width=70, command=self._on_vlc_play_pause_button_clicked, state="disabled")
        self.vlc_play_pause_button.pack(side="left", padx=(0,5))
        self.vlc_stop_button = ctk.CTkButton(buttons_sub_frame, text="Stop", width=70, command=self._on_vlc_stop_button_clicked, state="disabled")
        self.vlc_stop_button.pack(side="left", padx=5)
        self.vlc_volume_label = ctk.CTkLabel(buttons_sub_frame, text="Vol:")
        self.vlc_volume_label.pack(side="left", padx=(10,0))
        self.vlc_volume_slider_var = ctk.DoubleVar(value=100.0)
        self.vlc_volume_slider = ctk.CTkSlider(buttons_sub_frame, from_=0, to=100, variable=self.vlc_volume_slider_var, command=self._on_vlc_volume_slider_changed, width=100, state="disabled")
        self.vlc_volume_slider.pack(side="left", padx=5)
        if not self.is_vlc_available: self.playback_controls_frame.grid_remove()

    def _on_vlc_play_pause_button_clicked(self):
        if not (self.is_vlc_available and self.vlc_player): return
        if self.vlc_player.is_playing():
            self.vlc_player.pause()
        elif self.vlc_player.get_media() and (self.vlc_player.get_state() in [vlc.State.Paused, vlc.State.Stopped, vlc.State.Ended]):
            self.vlc_player.play()
        elif not self.vlc_player.get_media():
             self._play_video_file()

    def _on_vlc_stop_button_clicked(self):
        if not (self.is_vlc_available and self.vlc_player and (self.vlc_player.is_playing() or self.vlc_player.get_state() == vlc.State.Paused)): return
        self.vlc_player.stop()
        # Event handler _on_vlc_event_stopped will update UI

    def _on_vlc_seek_slider_dragged(self, value_str):
        if not (self.is_vlc_available and self.vlc_player and self.vlc_player.get_media()): return
        value = float(value_str)
        media_duration_ms = self.vlc_player.get_length()
        if media_duration_ms > 0 and self.vlc_player.is_seekable():
            self.vlc_player.set_position(value / 100.0)
        elif not self.vlc_player.is_seekable(): self.update_status("Video is not seekable.")
        else: self.update_status("Cannot seek: media duration unknown.")

    def _on_vlc_volume_slider_changed(self, value_str):
        if not (self.is_vlc_available and self.vlc_player): return
        self.vlc_player.audio_set_volume(int(float(value_str)))

    def _update_vlc_seek_slider(self):
        if not (self.is_vlc_available and self.vlc_player and self.vlc_player.is_playing()): return
        media_duration_ms = self.vlc_player.get_length()
        if media_duration_ms > 0:
            self.vlc_seek_slider_var.set(self.vlc_player.get_position() * 100.0)
        self.after(250, self._update_vlc_seek_slider)

    def _setup_vlc_event_handlers(self):
        if not (self.is_vlc_available and self.vlc_player): return
        event_manager = self.vlc_player.event_manager()
        event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_vlc_event_playing)
        event_manager.event_attach(vlc.EventType.MediaPlayerPaused, self._on_vlc_event_paused)
        event_manager.event_attach(vlc.EventType.MediaPlayerStopped, self._on_vlc_event_stopped)
        event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_vlc_event_end_reached)
        event_manager.event_attach(vlc.EventType.MediaPlayerLengthChanged, self._on_vlc_event_length_changed)

    def _on_vlc_event_playing(self, event):
        self.after(0, lambda: self.vlc_play_pause_button.configure(text="Pause", state="normal"))
        self.after(0, lambda: self.vlc_stop_button.configure(state="normal"))
        self.after(0, lambda: self.vlc_seek_slider.configure(state="normal"))
        self.after(0, lambda: self.vlc_volume_slider.configure(state="normal"))
        self.after(0, self.preview_image_label.grid_remove)
        self.after(0, self._update_vlc_seek_slider)

    def _on_vlc_event_paused(self, event):
        self.after(0, lambda: self.vlc_play_pause_button.configure(text="Play", state="normal"))

    def _on_vlc_event_stopped(self, event):
        self.after(0, lambda: self.vlc_play_pause_button.configure(text="Play", state="normal"))
        self.after(0, lambda: self.vlc_stop_button.configure(state="disabled"))
        self.after(0, lambda: self.vlc_seek_slider.configure(state="disabled"))
        self.after(0, self.vlc_seek_slider_var.set(0))
        if hasattr(self, 'preview_image_label') and not self.preview_image_label.winfo_ismapped():
             self.after(0, self.preview_image_label.grid)

    def _on_vlc_event_end_reached(self, event):
        self.after(0, lambda: self.vlc_play_pause_button.configure(text="Play", state="normal"))
        self.after(0, self.vlc_seek_slider_var.set(0)) # Reset slider to beginning
        if hasattr(self, 'preview_image_label') and not self.preview_image_label.winfo_ismapped():
            self.after(0, self.preview_image_label.grid)
        self.after(0, lambda: self.vlc_stop_button.configure(state="disabled")) # Disable stop as it's already at end
        self.after(0, lambda: self.vlc_seek_slider.configure(state="disabled")) # Disable seek as it's at end

    def _on_vlc_event_length_changed(self, event):
        pass # Slider is percentage based (0-100)

    def _on_app_closing(self):
        if self.is_vlc_available and self.vlc_player:
            if self.vlc_player.is_playing(): self.vlc_player.stop()
            if self.vlc_media: self.vlc_media.release()
            if self.vlc_player: self.vlc_player.release()
            if self.vlc_instance: self.vlc_instance.release()
        self.destroy()

    def _on_converter_format_changed(self, selected_format):
        is_gif = selected_format.lower() == "gif"
        self._toggle_gif_options_visibility(is_gif)
        is_video_format = selected_format.lower() in ["mp4", "mov", "avi", "webm", "gif"]
        if hasattr(self, 'converter_preset_menu'):
            self.converter_preset_menu.configure(state="normal" if is_video_format else "disabled")

    def _toggle_gif_options_visibility(self, show: bool):
        if not hasattr(self, 'gif_options_frame'): return
        if show: self.gif_options_frame.grid()
        else: self.gif_options_frame.grid_remove()

    def _browse_input_file_for_conversion(self):
        initial_dir = self.video_download_dir_var.get() if os.path.isdir(self.video_download_dir_var.get()) else os.path.expanduser("~")
        file_types = [("Media Files", "*.mp4 *.webm *.mkv *.avi *.mov *.flv *.wmv *.mp3 *.wav *.aac *.ogg *.flac"), ("Video Files", "*.mp4 *.webm *.mkv *.avi *.mov *.flv *.wmv"), ("Audio Files", "*.mp3 *.wav *.aac *.ogg *.flac"), ("All Files", "*.*")]
        chosen_file = filedialog.askopenfilename(initialdir=initial_dir, title="Select Media File to Convert", filetypes=file_types)
        if chosen_file:
            self.converter_input_file_var.set(chosen_file)
            self.update_status(f"Selected for conversion: {os.path.basename(chosen_file)}")

    def _on_converter_input_file_changed(self, *args):
        file_path = self.converter_input_file_var.get()
        if self.is_vlc_available and self.vlc_player and self.vlc_player.is_playing():
            self.vlc_player.stop()
            # UI updates for controls will be handled by _on_vlc_event_stopped
        
        if hasattr(self, 'playback_controls_frame'): # Ensure frame exists
            self.playback_controls_frame.grid_remove() # Hide controls until new video is ready for VLC
        if hasattr(self, 'preview_image_label') and not self.preview_image_label.winfo_ismapped():
            self.preview_image_label.grid()


        if file_path and os.path.exists(file_path):
            self.update_status(f"Processing file: {os.path.basename(file_path)}...")
            self.play_video_button.configure(state="normal")
            try:
                probe = ffmpeg.probe(file_path)
                video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
                if video_stream and 'duration' in video_stream:
                    self.video_duration_seconds = float(video_stream['duration'])
                    if self.video_duration_seconds <= 0: self.video_duration_seconds = 1.0
                else: self.video_duration_seconds = 100.0
                self.trim_start_slider.configure(to=self.video_duration_seconds, state="normal")
                self.trim_end_slider.configure(to=self.video_duration_seconds, state="normal")
                self.trim_start_seconds_var.set(0.0)
                self.trim_end_seconds_var.set(self.video_duration_seconds)
                self.trim_start_slider.set(0.0)
                self.trim_end_slider.set(self.video_duration_seconds)
                self.trim_start_display_label.configure(text=self._seconds_to_hhmmss(0.0))
                self.trim_end_display_label.configure(text=self._seconds_to_hhmmss(self.video_duration_seconds))
                self.update_status(f"Video duration: {self._seconds_to_hhmmss(self.video_duration_seconds)}. Sliders enabled.")
                threading.Thread(target=self._generate_video_thumbnail, args=(file_path, self.trim_start_seconds_var.get())).start()
            except Exception as e:
                self.update_status(f"Error processing video: {str(e)}. Sliders disabled.")
                self._disable_trim_sliders()
        else:
            if hasattr(self, 'preview_image_label'): self.after(0, lambda: self.preview_image_label.configure(image=None, text="No Video Selected"))
            self.preview_image_tk = None
            self.play_video_button.configure(state="disabled")
            self._disable_trim_sliders()
            self.video_duration_seconds = 0.0

    def _disable_trim_sliders(self):
        self.trim_start_slider.configure(state="disabled", to=100)
        self.trim_end_slider.configure(state="disabled", to=100)
        self.trim_start_seconds_var.set(0.0); self.trim_end_seconds_var.set(0.0)
        self.trim_start_slider.set(0.0); self.trim_end_slider.set(0.0)
        self.trim_start_display_label.configure(text="00:00:00")
        self.trim_end_display_label.configure(text="00:00:00")

    def _play_video_file(self):
        file_path = self.converter_input_file_var.get()
        if not (file_path and os.path.exists(file_path)):
            self.update_status("No valid file selected to play."); return

        if self.is_vlc_available and self.vlc_player:
            self.update_status(f"Attempting to play {os.path.basename(file_path)} in-app...")
            try:
                if self.vlc_player.is_playing() or self.vlc_player.get_state() == vlc.State.Paused : self.vlc_player.stop()
                
                # Release previous media if any
                if self.vlc_media: self.vlc_media.release()

                self.vlc_media = self.vlc_instance.media_new(file_path)
                start_sec, end_sec = self.trim_start_seconds_var.get(), self.trim_end_seconds_var.get()
                options = []
                if start_sec > 0: options.append(f":start-time={start_sec}")
                if end_sec > 0 and end_sec < self.video_duration_seconds: options.append(f":stop-time={end_sec}")
                for opt in options: self.vlc_media.add_option(opt)
                
                self.vlc_player.set_media(self.vlc_media)
                
                # Set window handle
                if sys.platform == "win32": self.vlc_player.set_hwnd(self.video_preview_frame.winfo_id())
                else: self.vlc_player.set_xwindow(self.video_preview_frame.winfo_id()) # macOS/Linux
                
                self.preview_image_label.grid_remove()
                self.playback_controls_frame.grid() # Ensure controls are visible
                self.vlc_player.play()
                # Event handlers will manage UI updates for controls
            except Exception as e:
                self.update_status(f"Error playing video with VLC: {e}")
                self._play_video_external(file_path) # Fallback
        else:
            self._play_video_external(file_path)

    def _play_video_external(self, file_path):
        self.update_status(f"Opening {os.path.basename(file_path)} in default external player.")
        try:
            if sys.platform == "win32": os.startfile(file_path)
            elif sys.platform == "darwin": subprocess.Popen(["open", file_path])
            else: subprocess.Popen(["xdg-open", file_path])
        except Exception as e: self.update_status(f"Error opening video externally: {e}")

    def _generate_video_thumbnail(self, video_path, seek_time_seconds=None):
        try:
            max_width = self.video_preview_frame.winfo_width() - 10 
            max_height = self.video_preview_frame.winfo_height() - 10
            thumbnail_width = min(240, max_width) if max_width > 0 else 240
            thumbnail_height = -1 
            actual_seek_time = seek_time_seconds
            if seek_time_seconds is None:
                probe = ffmpeg.probe(video_path)
                video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
                if not video_stream: 
                    self.after(0, lambda: self.preview_image_label.configure(image=None, text="No Video Stream"))
                    return
                duration = float(video_stream.get('duration', 0))
                actual_seek_time = duration / 3 if duration > 0 else 1
            
            popen_kwargs = {}
            if sys.platform == "win32":
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            stream = ffmpeg.input(video_path, ss=actual_seek_time).output(
                'pipe:', vframes=1, format='image2pipe', vcodec='mjpeg', 
                vf=f'scale={thumbnail_width}:{thumbnail_height}'
            )
            cmd_args = stream.compile()
            
            process = subprocess.Popen(
                cmd_args, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                **popen_kwargs
            )
            out, err = process.communicate()

            if process.returncode != 0:
                raise ffmpeg.Error(' '.join(cmd_args), out, err)

            pil_image = Image.open(io.BytesIO(out))
            
            # Create and immediately store the CTkImage on the instance
            self.preview_image_tk = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, 
                                                 size=(pil_image.width, pil_image.height))
            
            # Configure the label using the instance attribute
            def update_label():
                if hasattr(self, 'preview_image_label') and self.preview_image_label.winfo_exists():
                    if not self.preview_image_label.winfo_ismapped():
                        self.preview_image_label.grid() # Ensure it's visible
                    self.preview_image_label.configure(image=self.preview_image_tk, text="")
            self.after(0, update_label)
            self.update_status(f"Thumbnail generated for {os.path.basename(video_path)}")
        except ffmpeg.Error as e:
            self.preview_image_tk = None # Clear the reference
            error_details = e.stderr.decode(errors='replace') if e.stderr else str(e)
            def update_label_error():
                if hasattr(self, 'preview_image_label') and self.preview_image_label.winfo_exists():
                    if not self.preview_image_label.winfo_ismapped():
                        self.preview_image_label.grid()
                    self.preview_image_label.configure(image=None, text="Preview Error")
            self.after(0, update_label_error)
            self.update_status(f"Thumbnail ffmpeg error: {error_details}")
        except Exception as e:
            self.preview_image_tk = None # Clear the reference
            def update_label_error():
                if hasattr(self, 'preview_image_label') and self.preview_image_label.winfo_exists():
                    if not self.preview_image_label.winfo_ismapped():
                        self.preview_image_label.grid()
                    self.preview_image_label.configure(image=None, text="Preview Error")
            self.after(0, update_label_error)
            self.update_status(f"Thumbnail error: {e}")

    def _start_conversion_thread(self):
        input_file, output_format = self.converter_input_file_var.get(), self.converter_output_format_var.get()
        if not (input_file and os.path.exists(input_file) and output_format):
            self.update_status("Input file or output format missing/invalid."); return
        start_seconds, end_seconds = self.trim_start_seconds_var.get(), self.trim_end_seconds_var.get()
        start_time_str = self._seconds_to_hhmmss(start_seconds) if start_seconds > 0 else None
        end_time_str = self._seconds_to_hhmmss(end_seconds) if (0 < end_seconds < self.video_duration_seconds) else None
        if start_seconds == 0 and (end_seconds == self.video_duration_seconds or end_seconds == 0): start_time_str = end_time_str = None
        gif_fps, gif_scale_width = 10, 480
        if output_format.lower() == "gif":
            try: gif_fps = int(self.gif_fps_var.get()); assert gif_fps > 0
            except: self.update_status("Invalid GIF FPS."); return
            try: gif_scale_width = int(self.gif_scale_width_var.get()); assert gif_scale_width > 0 or gif_scale_width == -1
            except: self.update_status("Invalid GIF Scale Width."); return
        self.convert_file_button.configure(state="disabled"); self.stop_conversion_button.configure(state="normal")
        self.update_status(f"Starting conversion of {os.path.basename(input_file)} to {output_format}...")
        try: threads = int(self.converter_threads_var.get())
        except ValueError: self.update_status("Invalid Threads value."); self.convert_file_button.configure(state="normal"); self.stop_conversion_button.configure(state="disabled"); return
        preset = self.converter_preset_var.get()
        if preset not in self.converter_preset_options: preset = 'fast'
        self.conversion_thread = threading.Thread(target=self._conversion_worker_thread, args=(input_file, output_format, threads, preset, start_time_str, end_time_str, gif_fps, gif_scale_width))
        self.conversion_thread.daemon = True; self.conversion_thread.start()

    def _stop_conversion(self):
        if self.conversion_thread and self.conversion_thread.is_alive():
            self.converter.stop_conversion(); self.update_status("Stopping conversion...")
            self.convert_file_button.configure(state='normal'); self.stop_conversion_button.configure(state='disabled')
        else: self.update_status("No active conversion to stop.")

    def _conversion_worker_thread(self, input_file_path, output_format_ext, threads, preset, start_time, end_time, gif_fps, gif_scale_width):
        try:
            base, _ = os.path.splitext(os.path.basename(input_file_path))
            output_dir = self.video_download_dir_var.get()
            os.makedirs(output_dir, exist_ok=True)
            output_file_path = self._get_unique_filepath(os.path.join(output_dir, f"{base}_converted.{output_format_ext.lower()}"))
            converted_file = self.converter.convert_media(input_file_path, output_file_path, output_format_ext, threads=threads, preset=preset, progress_callback=self._gui_progress_hook, start_time=start_time, end_time=end_time, gif_fps=gif_fps, gif_scale_width=gif_scale_width)
            self.update_status(f"Successfully converted: {os.path.basename(converted_file)}")
        except Exception as e:
            self.update_status(f"Conversion Error: {type(e).__name__} - {str(e)}.")
            self.after(0, lambda: self.progress_bar.set(0))
        finally:
            self.after(0, lambda: self.convert_file_button.configure(state='normal'))
            self.after(0, lambda: self.stop_conversion_button.configure(state='disabled'))
            self.after(0, lambda: self.progress_bar.configure(mode='determinate'))

    def _seconds_to_hhmmss(self, total_seconds):
        total_seconds = int(round(total_seconds))
        h, m, s = total_seconds // 3600, (total_seconds % 3600) // 60, total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _on_start_trim_slider_changed(self, value):
        self.trim_start_display_label.configure(text=self._seconds_to_hhmmss(value))
        if value > self.trim_end_seconds_var.get():
            self.trim_end_seconds_var.set(value); self.trim_end_slider.set(value)
            self.trim_end_display_label.configure(text=self._seconds_to_hhmmss(value))
        file_path = self.converter_input_file_var.get()
        if file_path and os.path.exists(file_path) and self.video_duration_seconds > 0:
            threading.Thread(target=self._generate_video_thumbnail, args=(file_path, value)).start()

    def _on_end_trim_slider_changed(self, value):
        self.trim_end_display_label.configure(text=self._seconds_to_hhmmss(value))
        if value < self.trim_start_seconds_var.get():
            self.trim_start_seconds_var.set(value); self.trim_start_slider.set(value)
            self.trim_start_display_label.configure(text=self._seconds_to_hhmmss(value))

    def _create_settings_tab(self):
        self.settings_tab_frame = self.tabview.add("Settings")
        self.tabview.tab("Settings").grid_columnconfigure(0, weight=1)
        self.tabview.tab("Settings").grid_rowconfigure(0, weight=1) 
        settings_content_frame = ctk.CTkFrame(self.tabview.tab("Settings"))
        settings_content_frame.grid(row=0, column=0, sticky="nsew")
        settings_content_frame.grid_columnconfigure(1, weight=1) 
        ctk.CTkLabel(settings_content_frame, text="Theme:").grid(row=0, column=0, padx=(0,10), pady=(5,10), sticky="w")
        theme_options_frame = ctk.CTkFrame(settings_content_frame) 
        theme_options_frame.grid(row=0, column=1, sticky="ew", pady=(5,10))
        for val, txt in [("System", "System"), ("Light", "Light"), ("Dark", "Dark")]:
            ctk.CTkRadioButton(theme_options_frame, text=txt, variable=self.selected_theme_var, value=val, command=self._on_setting_changed).pack(side=tk.LEFT, padx=5)
        for i, (label_text, var, cmd_var) in enumerate([
            ("Video Download Dir:", self.video_download_dir_var, self.video_download_dir_var),
            ("Image Download Dir:", self.image_download_dir_var, self.image_download_dir_var)
        ], start=1):
            ctk.CTkLabel(settings_content_frame, text=label_text).grid(row=i, column=0, padx=(0,10), pady=(5,10), sticky="w")
            dir_frame = ctk.CTkFrame(settings_content_frame)
            dir_frame.grid(row=i, column=1, sticky="ew", pady=(5,10)); dir_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkEntry(dir_frame, textvariable=var).grid(row=0, column=0, sticky="ew", padx=(0,5))
            ctk.CTkButton(dir_frame, text="Browse...", command=lambda v=cmd_var: self._browse_directory(v)).grid(row=0, column=1, sticky="e")
            var.trace_add("write", self._on_setting_changed)
        ctk.CTkLabel(settings_content_frame, text="Default Media Format:").grid(row=3, column=0, padx=(0,10), pady=(5,10), sticky="w")
        self.default_format_menu = ctk.CTkOptionMenu(settings_content_frame, variable=self.default_format_var, values=self.format_options, command=lambda *args: self._on_setting_changed())
        self.default_format_menu.grid(row=3, column=1, sticky="ew", pady=(5,10))

    def _load_settings(self):
        defaults = {"theme": "System", "video_download_directory": os.path.join(os.path.expanduser("~"), "Videos", "MediaDL"), "image_download_directory": os.path.join(os.path.expanduser("~"), "Pictures", "MediaDL"), "default_media_format": "mp4"}
        settings = defaults.copy()
        try:
            with open(SETTINGS_FILE, 'r') as f: settings.update(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError): os.makedirs(defaults["video_download_directory"], exist_ok=True); os.makedirs(defaults["image_download_directory"], exist_ok=True)
        self.selected_theme_var.set(settings["theme"])
        self.video_download_dir_var.set(settings["video_download_directory"])
        self.image_download_dir_var.set(settings["image_download_directory"])
        self.default_format_var.set(settings["default_media_format"] if settings["default_media_format"] in self.format_options else self.format_options[0])

    def _save_settings(self):
        settings = {"theme": self.selected_theme_var.get(), "video_download_directory": self.video_download_dir_var.get(), "image_download_directory": self.image_download_dir_var.get(), "default_media_format": self.default_format_var.get()}
        try:
            with open(SETTINGS_FILE, 'w') as f: json.dump(settings, f, indent=4)
        except IOError as e: self.update_status(f"Error saving settings: {e}") 

    def _on_setting_changed(self, *args):
        ctk.set_appearance_mode(self.selected_theme_var.get())
        self._save_settings()

    def _browse_directory(self, ctk_string_var):
        chosen_dir = filedialog.askdirectory(initialdir=ctk_string_var.get() if os.path.isdir(ctk_string_var.get()) else os.path.expanduser("~"))
        if chosen_dir: ctk_string_var.set(chosen_dir)

    def _start_fetch_resolutions_thread(self):
        url = self.url_var.get().strip()
        if not url: self.update_status("Please enter a media URL first."); return
        self.fetch_resolutions_button.configure(state="disabled", text="Fetching...")
        self.resolution_combobox.set("Fetching..."); self.resolution_combobox.configure(state="disabled")
        threading.Thread(target=self._fetch_resolutions_worker_thread, args=(url,), daemon=True).start()

    def _fetch_resolutions_worker_thread(self, url):
        try:
            self.available_resolutions_data = self.downloader.get_available_resolutions(url)
            self.after(0, self._populate_resolutions_dropdown)
        except Exception as e:
            self.after(0, lambda: self.update_status(f"Error fetching resolutions: {e}"))
            self.after(0, lambda: self.resolution_combobox.set("Error fetching"))
        finally:
            self.after(0, lambda: self.fetch_resolutions_button.configure(state="normal", text="Fetch Resolutions"))

    def _populate_resolutions_dropdown(self):
        self.resolution_combobox.configure(state="readonly")
        if not self.available_resolutions_data:
            self.resolution_combobox.configure(values=["No resolutions found"]); self.resolution_var.set("No resolutions found")
            return
        display_values = ["Auto (Best for selected format)"] + [res['display_text'] for res in self.available_resolutions_data]
        self.resolution_combobox.configure(values=display_values); self.resolution_var.set(display_values[0])

    def _download_and_convert_thread(self, url, target_container_format, selected_resolution_display_text, is_direct_image_download=False, is_download_only=False): 
        active_button = self.download_image_button if is_direct_image_download else (self.download_media_button if is_download_only else self.convert_file_button)
        download_target_dir = self.image_download_dir_var.get() if is_direct_image_download else self.video_download_dir_var.get()
        downloaded_file_path = output_file_path = None
        preferred_format_info = {'format_id': target_container_format.lower()} if target_container_format else {}
        if not is_direct_image_download and selected_resolution_display_text != "Auto (Best for selected format)":
            selected_res_data = next((res for res in self.available_resolutions_data if res['display_text'] == selected_resolution_display_text), None)
            if selected_res_data:
                format_code = selected_res_data['id']
                if selected_res_data['is_video_only'] and target_container_format and target_container_format.lower() != 'mp3': format_code += "+bestaudio"
                preferred_format_info['format_code'] = format_code
        try:
            os.makedirs(download_target_dir, exist_ok=True)
            downloaded_file_path = self.downloader.download_media(url, download_target_dir, preferred_format_info=preferred_format_info, progress_callback=self._gui_progress_hook)
            if not (downloaded_file_path and os.path.exists(downloaded_file_path)): self.update_status(f"Download failed: File not found."); return
            output_file_path = downloaded_file_path
            if is_direct_image_download: self.update_status(f"Image downloaded: {os.path.basename(output_file_path)}")
            elif is_download_only: self.update_status(f"Download complete: {os.path.basename(downloaded_file_path)}")
            else: self.after(0, lambda: self.converter_input_file_var.set(downloaded_file_path)); self.update_status(f"File ready for conversion: {os.path.basename(output_file_path)}")
        except Exception as e: self.update_status(f"Error: {type(e).__name__} - {str(e)}.")
        finally:
            if active_button: self.after(0, lambda: active_button.configure(state='normal'))
            self.after(0, lambda: self.progress_bar.stop())
            self.after(0, lambda: self.progress_bar.configure(mode='determinate'))
            self.after(0, lambda: self.progress_bar.set(1 if output_file_path and os.path.exists(output_file_path) else 0))

    def update_status(self, message):
        def _update():
            if not hasattr(self, 'status_text') or not self.status_text.winfo_exists(): print(f"Status (GUI not ready): {message}"); return
            self.status_text.configure(state="normal")
            if message == "": self.status_text.delete('1.0', tk.END)
            else: self.status_text.insert(tk.END, str(message) + "\n") 
            self.status_text.see(tk.END); self.status_text.configure(state="disabled")
        self.after(0, _update)

    def _start_image_download(self):
        url = self.image_url_var.get().strip()
        if not url: self.update_status("Please enter an image URL."); return
        self.download_image_button.configure(state='disabled')
        threading.Thread(target=self._download_and_convert_thread, args=(url, None, None, True, False), daemon=True).start()

    def _on_url_changed(self, *args): 
        url = self.url_var.get().strip()
        is_direct_image = self.downloader._is_direct_image_url(url)
        self.fetch_resolutions_button.configure(state="disabled" if not url or is_direct_image else "normal")
        self.resolution_combobox.configure(state="disabled")
        if not url: self.resolution_combobox.set("Enter URL first")
        elif is_direct_image: self.resolution_combobox.set("N/A for direct image")
        else: self.resolution_combobox.set("Fetch resolutions")
        self.available_resolutions_data = []
        self.download_media_button.configure(text="Image URL? Use Image Tab" if is_direct_image else "Download")

    def _gui_progress_hook(self, data): 
        if not (hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists()): return 
        status = data.get('status')
        if status == 'downloading':
            percentage, total_bytes = data.get('percentage', 0.0), data.get('total_bytes', 0) or data.get('total_bytes_estimate', 0)
            if data.get('message') and (percentage == 0 and total_bytes == 0 and not data.get('speed')):
                self.update_status(data['message'])
                # Indeterminate progress for pre-processing or unknown size
                if data.get('downloaded_bytes', 0) > 0 and self.progress_bar.cget("mode") != 'indeterminate':
                    self.progress_bar.configure(mode='indeterminate'); self.progress_bar.start()
                elif not (data.get('downloaded_bytes', 0) > 0) and self.progress_bar.cget("mode") == 'indeterminate':
                    self.progress_bar.stop(); self.progress_bar.set(0); self.progress_bar.configure(mode='determinate')
            else:
                if self.progress_bar.cget("mode") == 'indeterminate': self.progress_bar.stop(); self.progress_bar.configure(mode='determinate')
                dl_bytes, speed, eta = data.get('downloaded_bytes',0), data.get('speed',0), data.get('eta',0)
                status_msg = f"Downloading: {max(0.0, min(100.0, percentage)):.1f}% ({self._format_bytes(dl_bytes)}/{self._format_bytes(total_bytes)}) at {self._format_speed(speed)}, ETA: {self._format_eta(eta)}" if total_bytes > 0 else f"Downloading: {self._format_bytes(dl_bytes)} at {self._format_speed(speed)}"
                self.update_status(status_msg)
                if total_bytes > 0: self.after(0, lambda p=percentage: self.progress_bar.set(max(0.0, min(1.0, p / 100.0))))
                elif dl_bytes > 0 and self.progress_bar.cget("mode") != 'indeterminate': # Unknown total size but downloading
                     self.progress_bar.configure(mode='indeterminate'); self.progress_bar.start()

        elif status == 'converting':
            if self.progress_bar.cget("mode") == 'indeterminate': self.progress_bar.stop()
            self.progress_bar.configure(mode='determinate') 
            percentage, time_str, speed = data.get('percentage'), data.get('time_str', 'N/A'), data.get('speed', 'N/A')
            if percentage is not None:
                self.after(0, lambda p=percentage: self.progress_bar.set(float(p) / 100.0))
                self.update_status(f"Converting: {percentage:.1f}% (Time: {time_str}, Speed: {speed})")
            elif self.progress_bar.cget("mode") != 'indeterminate': # Indeterminate if no percentage
                self.progress_bar.configure(mode='indeterminate'); self.progress_bar.start()
                self.update_status(f"Converting... (Time: {time_str}, Speed: {speed})")
        elif status in ['finished', 'finished_conversion']:
            if self.progress_bar.cget("mode") == 'indeterminate': self.progress_bar.stop()
            self.progress_bar.configure(mode='determinate'); self.after(0, lambda: self.progress_bar.set(1))
            if status == 'finished_conversion': self.update_status(f"Successfully converted: {os.path.basename(data.get('filename', ''))}")
        elif status == 'error':
            if self.progress_bar.cget("mode") == 'indeterminate': self.progress_bar.stop()
            self.progress_bar.configure(mode='determinate'); self.after(0, lambda: self.progress_bar.set(0))
            self.update_status(f"Error (hook): {data.get('message', 'Unknown error')}")

    def apply_theme(self, theme_name): ctk.set_appearance_mode(theme_name) 
    def _format_bytes(self, b): 
        if b is None or not isinstance(b, (int,float)) or b < 0: return "N/A"
        if b == 0: return "0 B"; import math; s=("B","KB","MB","GB","TB"); i=min(int(math.log(b,1024)//1),len(s)-1); return f"{b/math.pow(1024,i):.2f} {s[i]}"
    def _format_eta(self, s):
        if s is None or not isinstance(s,(int,float)) or s < 0: return "--:--"
        try: s=int(s); m,s=divmod(s,60); h,m=divmod(m,60); return f"{h:02d}:{m:02d}:{s:02d}" if h>0 else f"{m:02d}:{s:02d}"
        except: return "--:--"
    def _format_speed(self, sp): return "N/A" if sp is None or not isinstance(sp,(int,float)) or sp<0 else f"{self._format_bytes(sp)}/s"
    def _get_unique_filepath(self, fp):
        if not os.path.exists(fp): return fp
        base, ext = os.path.splitext(fp); i = 1
        while os.path.exists(f"{base}_{i}{ext}"): i += 1
        return f"{base}_{i}{ext}"

if __name__ == "__main__":
    app = App()
    app.mainloop()
