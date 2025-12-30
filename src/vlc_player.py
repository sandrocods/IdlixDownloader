import tkinter as tk
from tkinter import ttk
import os
import platform
import logging

try:
    import vlc
except ImportError:
    vlc = None

# Configure logger (using standard logging if loguru isn't passed, but better to use loguru if available)
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class VLCPlayerWindow(tk.Toplevel):
    def __init__(self, parent, idlix, m3u8_url, subtitle=None, title="Video Player"):
        super().__init__(parent)
        self.title(title)
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.idlix = idlix
        self.m3u8_url = m3u8_url
        self.subtitle = subtitle
        self.is_playing = True
        
        # --- VLC Setup ---
        vlc_args = [
             "--quiet",
             "--no-xlib", # Linux optimization
        ]
        
        self.instance = vlc.Instance(vlc_args)
        self.player = self.instance.media_player_new()
        
        # --- GUI Setup ---
        self.video_frame = tk.Frame(self, bg="black")
        self.video_frame.pack(fill="both", expand=True)

        self.controls_frame = tk.Frame(self, bg="#222")
        self.controls_frame.pack(fill="x", side="bottom")

        # Play/Pause
        self.btn_play = tk.Button(self.controls_frame, text="Pause", command=self.toggle_play, width=10)
        self.btn_play.pack(side="left", padx=5, pady=5)
        
        # Stop
        self.btn_stop = tk.Button(self.controls_frame, text="Stop", command=self.on_close, width=10)
        self.btn_stop.pack(side="left", padx=5, pady=5)

        # Time Slider
        self.time_var = tk.DoubleVar()
        self.slider = ttk.Scale(self.controls_frame, from_=0, to=1000, orient="horizontal", variable=self.time_var, command=self.on_seek)
        self.slider.pack(side="left", fill="x", expand=True, padx=10)
        
        # Volume
        self.vol_var = tk.DoubleVar(value=100)
        self.vol_slider = ttk.Scale(self.controls_frame, from_=0, to=100, orient="horizontal", variable=self.vol_var, command=self.on_volume, length=100)
        self.vol_slider.pack(side="right", padx=5)
        tk.Label(self.controls_frame, text="Vol", fg="white", bg="#222").pack(side="right")

        # Time Label
        self.time_label = tk.Label(self.controls_frame, text="00:00 / 00:00", fg="white", bg="#222")
        self.time_label.pack(side="right", padx=10)

        # Subtitle Delay Label
        self.sub_label = tk.Label(self.controls_frame, text="Sub: 0ms", fg="#aaa", bg="#222", font=("Tiny", 8))
        self.sub_label.pack(side="right", padx=5)
        
        # Fullscreen Button
        self.btn_fs = tk.Button(self.controls_frame, text="[ ]", command=self.toggle_fullscreen, width=4)
        self.btn_fs.pack(side="right", padx=5)

        # Embed Window
        self.update_idletasks() # Ensure window ID exists
        if platform.system() == "Windows":
            self.player.set_hwnd(self.video_frame.winfo_id())
        else:
            self.player.set_xwindow(self.video_frame.winfo_id())

        # Start Playback
        self.start_playback()
        
        # Bindings
        self.video_frame.bind("<Double-Button-1>", self.toggle_fullscreen)
        self.bind("<Escape>", self.exit_fullscreen)
        self.bind("<f>", self.toggle_fullscreen)
        self.bind("<F>", self.toggle_fullscreen)
        self.bind("<space>", self.toggle_play_key)
        self.slider.bind("<Button-1>", self.on_slider_click)
        
        # Arrow Keys
        self.bind("<Left>", lambda e: self.seek_relative(-5000))  # -5 sec
        self.bind("<Right>", lambda e: self.seek_relative(5000))  # +5 sec
        self.bind("<Up>", lambda e: self.volume_relative(5))      # +5 vol
        self.bind("<Down>", lambda e: self.volume_relative(-5))   # -5 vol

        # Subtitle Sync
        self.spu_delay = 0
        self.bind("<g>", lambda e: self.sync_subtitle(-50000))   # -50 ms
        self.bind("<G>", lambda e: self.sync_subtitle(-50000))
        self.bind("<h>", lambda e: self.sync_subtitle(50000))    # +50 ms
        self.bind("<H>", lambda e: self.sync_subtitle(50000))
        
        # Timer for UI update
        self.after(500, self.update_ui)
        
        # Ensure focus so keys work immediately
        self.focus_force()

    def sync_subtitle(self, delta):
        self.spu_delay += delta
        self.player.video_set_spu_delay(self.spu_delay)
        
        # Update label
        ms_delay = int(self.spu_delay / 1000)
        self.sub_label.config(text=f"Sub: {ms_delay}ms", fg="yellow" if ms_delay != 0 else "#aaa")

    def start_playback(self):
        media = self.instance.media_new(self.m3u8_url)
        
        # Add Headers & Cookies explicitly to the media
        user_agent = self.idlix.request.headers.get("User-Agent", "Mozilla/5.0")
        cookies = self.idlix.request.cookies.get_dict()
        
        media.add_option(f":http-user-agent={user_agent}")
        
        referer = self.idlix.BASE_STATIC_HEADERS.get("Referer")
        if referer:
            media.add_option(f":http-referrer={referer}")

        if cookies:
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            media.add_option(f":http-cookie={cookie_str}")
        
        if self.subtitle:
            media.add_option(f":sub-file={os.path.abspath(self.subtitle)}")

        self.player.set_media(media)
        self.player.play()
    
    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.config(text="Play")
        else:
            self.player.play()
            self.btn_play.config(text="Pause")
            
    def toggle_play_key(self, event):
        self.toggle_play()

    def toggle_fullscreen(self, event=None):
        is_fs = self.attributes("-fullscreen")
        self.attributes("-fullscreen", not is_fs)
        if not is_fs:
            self.controls_frame.pack_forget() 
        else:
            self.controls_frame.pack(fill="x", side="bottom")

    def exit_fullscreen(self, event=None):
        self.attributes("-fullscreen", False)
        self.controls_frame.pack(fill="x", side="bottom")

    def seek_relative(self, ms_offset):
        length = self.player.get_length()
        if length > 0:
            current = self.player.get_time()
            new_time = max(0, min(length, current + ms_offset))
            self.player.set_time(new_time)
            pos = new_time / length
            self.time_var.set(pos * 1000)
    
    def volume_relative(self, amount):
        current_vol = self.player.audio_get_volume()
        new_vol = max(0, min(100, current_vol + amount))
        self.player.audio_set_volume(new_vol)
        self.vol_var.set(new_vol)

    def on_seek(self, val):
        if self.player.get_length() > 0:
            percentage = float(val) / 1000.0
            self.player.set_position(percentage)
    
    def on_slider_click(self, event):
        width = self.slider.winfo_width()
        if width > 0:
            pct = event.x / width
            pct = max(0, min(1, pct))
            self.player.set_position(pct)
            self.time_var.set(pct * 1000)

    def on_volume(self, val):
        vol = int(float(val))
        self.player.audio_set_volume(vol)

    def update_ui(self):
        if not self.winfo_exists():
            return
            
        length = self.player.get_length()
        current = self.player.get_time() 
        
        if length > 0:
            pos = self.player.get_position()
            self.time_var.set(pos * 1000)
            
            def fmt(ms):
                seconds = ms // 1000
                m, s = divmod(seconds, 60)
                h, m = divmod(m, 60)
                if h > 0:
                    return f"{h:02}:{m:02}:{s:02}"
                return f"{m:02}:{s:02}"
            
            self.time_label.config(text=f"{fmt(current)} / {fmt(length)}")
        
        self.after(500, self.update_ui)

    def on_close(self):
        if self.player:
            self.player.stop()
            self.player.release()
        
        # Cleanup subtitle
        if self.subtitle and os.path.exists(self.subtitle):
            try:
                os.remove(self.subtitle)
                vtt_path = self.subtitle.rsplit('.', 1)[0] + '.vtt'
                if os.path.exists(vtt_path):
                    os.remove(vtt_path)
                logger.info("Temporary subtitle files cleaned up.")
            except Exception as e:
                logger.warning(f"Failed to cleanup subtitles: {e}")

        self.destroy()


def play_video_standalone(idlix, m3u8_url, subtitle=None, title="Video Player"):
    """
    Launches the VLC player in a standalone Tkinter root.
    Use this for the CLI application.
    """
    if vlc is None:
        logger.error("python-vlc not found.")
        return False

    root = tk.Tk()
    root.withdraw() # Hide the main root window, we only want the player window
    
    player = VLCPlayerWindow(root, idlix, m3u8_url, subtitle, title)
    
    # When player window closes, destroy root and exit loop
    def on_player_close():
        player.on_close()
        root.destroy()
        
    player.protocol("WM_DELETE_WINDOW", on_player_close)
    
    # Wait for the player window to close
    root.wait_window(player)
    return True
