"""
Modern VLC Player - YouTube-style UI
"""
import tkinter as tk
from tkinter import ttk
import os
import platform

try:
    import vlc
except ImportError:
    vlc = None

try:
    from loguru import logger
    LOG_FILE = "vlc_player.log"
    logger.add(LOG_FILE, rotation="1 MB", level="DEBUG",
               format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {message}")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ModernVLCPlayer(tk.Toplevel):
    """YouTube-style VLC Player with modern UI"""
    
    # Colors
    BG_COLOR = "#0f0f0f"
    CONTROLS_BG = "#1a1a1a"
    ACCENT_COLOR = "#ff0000"  # YouTube red
    TEXT_COLOR = "#ffffff"
    TEXT_DIM = "#aaaaaa"
    HOVER_COLOR = "#333333"
    
    def __init__(self, parent, idlix, m3u8_url, subtitle=None, title="Video Player"):
        super().__init__(parent)
        
        self.title(title)
        self.geometry("1100x650")
        self.configure(bg=self.BG_COLOR)
        self.minsize(800, 500)
        
        self.idlix = idlix
        self.m3u8_url = m3u8_url
        self.subtitle = subtitle
        self.is_loading = True
        self.controls_visible = True
        self.hide_controls_id = None
        self.update_ui_id = None
        self.animate_loading_id = None
        self.log_state_id = None
        self.loading_dots = 0
        self._closed = False
        
        logger.debug(f"Player init - URL: {m3u8_url}")
        logger.debug(f"Player init - Subtitle: {subtitle}")
        
        # VLC Setup
        vlc_args = ["--no-xlib", "--network-caching=2000"]
        self.instance = vlc.Instance(vlc_args)
        self.player = self.instance.media_player_new()
        
        logger.debug(f"VLC Instance: {self.instance}")
        
        # Subtitle delay tracking
        self.spu_delay = 0
        
        self._create_ui()
        self._bind_events()
        self._start_playback()
        
        # Start UI updates
        self.update_ui_id = self.after(100, self._update_ui)
        self.animate_loading_id = self.after(300, self._animate_loading)
        self.focus_force()
    
    def _create_ui(self):
        """Create the modern UI layout"""
        
        # Main container
        self.main_container = tk.Frame(self, bg=self.BG_COLOR)
        self.main_container.pack(fill="both", expand=True)
        
        # Video frame (VLC renders here)
        self.video_frame = tk.Frame(self.main_container, bg="black")
        self.video_frame.pack(fill="both", expand=True)
        
        # Loading overlay (centered on video)
        self.loading_overlay = tk.Frame(self.video_frame, bg=self.BG_COLOR)
        self.loading_overlay.place(relx=0.5, rely=0.5, anchor="center")
        
        # Spinner animation (using unicode)
        self.spinner_label = tk.Label(
            self.loading_overlay,
            text="◐",
            font=("Arial", 48),
            fg=self.ACCENT_COLOR,
            bg=self.BG_COLOR
        )
        self.spinner_label.pack()
        
        self.loading_text = tk.Label(
            self.loading_overlay,
            text="Loading",
            font=("Segoe UI", 14),
            fg=self.TEXT_COLOR,
            bg=self.BG_COLOR
        )
        self.loading_text.pack(pady=(10, 0))
        
        self.loading_status = tk.Label(
            self.loading_overlay,
            text="Connecting to stream...",
            font=("Segoe UI", 10),
            fg=self.TEXT_DIM,
            bg=self.BG_COLOR
        )
        self.loading_status.pack(pady=(5, 0))
        
        # Buffering indicator (shown during playback)
        self.buffering_label = tk.Label(
            self.video_frame,
            text="◐ Buffering...",
            font=("Segoe UI", 12),
            fg="yellow",
            bg=self.BG_COLOR
        )
        
        # --- Controls Overlay (YouTube-style) ---
        self.controls_overlay = tk.Frame(self.main_container, bg=self.CONTROLS_BG, height=90)
        self.controls_overlay.pack(fill="x", side="bottom")
        self.controls_overlay.pack_propagate(False)
        
        # Progress bar container
        progress_container = tk.Frame(self.controls_overlay, bg=self.CONTROLS_BG)
        progress_container.pack(fill="x", padx=10, pady=(10, 5))
        
        # Custom progress bar using Canvas (taller for easier clicking)
        self.progress_canvas = tk.Canvas(
            progress_container,
            height=12,
            bg="#404040",
            highlightthickness=0,
            cursor="hand2"
        )
        self.progress_canvas.pack(fill="x", ipady=3)
        
        # Progress fill (red bar)
        self.progress_fill = self.progress_canvas.create_rectangle(
            0, 0, 0, 12, fill=self.ACCENT_COLOR, outline=""
        )
        
        # Buffered indicator (gray)
        self.progress_buffered = self.progress_canvas.create_rectangle(
            0, 0, 0, 12, fill="#606060", outline=""
        )
        
        # Controls row
        controls_row = tk.Frame(self.controls_overlay, bg=self.CONTROLS_BG)
        controls_row.pack(fill="x", padx=10, pady=5)
        
        # Left controls
        left_controls = tk.Frame(controls_row, bg=self.CONTROLS_BG)
        left_controls.pack(side="left")
        
        # Play/Pause button
        self.btn_play = self._create_icon_button(left_controls, "▶", self._toggle_play)
        self.btn_play.pack(side="left", padx=(0, 5))
        
        # Skip backward 10s
        self.btn_skip_back = self._create_icon_button(left_controls, "⏪", lambda: self._seek_relative(-10000))
        self.btn_skip_back.pack(side="left", padx=2)
        
        # Skip forward 10s  
        self.btn_skip_fwd = self._create_icon_button(left_controls, "⏩", lambda: self._seek_relative(10000))
        self.btn_skip_fwd.pack(side="left", padx=2)
        
        # Volume container
        vol_frame = tk.Frame(left_controls, bg=self.CONTROLS_BG)
        vol_frame.pack(side="left", padx=(15, 0))
        
        self.btn_mute = self._create_icon_button(vol_frame, "🔊", self._toggle_mute)
        self.btn_mute.pack(side="left")
        
        self.vol_scale = ttk.Scale(vol_frame, from_=0, to=100, orient="horizontal", 
                                    length=80, command=self._on_volume)
        self.vol_scale.set(100)
        self.vol_scale.pack(side="left", padx=5)
        
        # Time display
        self.time_label = tk.Label(
            left_controls,
            text="0:00 / 0:00",
            font=("Segoe UI", 10),
            fg=self.TEXT_COLOR,
            bg=self.CONTROLS_BG
        )
        self.time_label.pack(side="left", padx=(15, 0))
        
        # Right controls
        right_controls = tk.Frame(controls_row, bg=self.CONTROLS_BG)
        right_controls.pack(side="right")
        
        # Subtitle sync indicator
        self.sub_label = tk.Label(
            right_controls,
            text="",
            font=("Segoe UI", 9),
            fg=self.TEXT_DIM,
            bg=self.CONTROLS_BG
        )
        self.sub_label.pack(side="left", padx=10)
        
        # Fullscreen button
        self.btn_fullscreen = self._create_icon_button(right_controls, "⛶", self._toggle_fullscreen)
        self.btn_fullscreen.pack(side="right")
        
        # Keyboard shortcuts hint
        hint_label = tk.Label(
            self.controls_overlay,
            text="Space: Play/Pause | ←→: Seek 10s | ↑↓: Volume | F: Fullscreen | G/H: Subtitle sync ±50ms",
            font=("Segoe UI", 8),
            fg="#666666",
            bg=self.CONTROLS_BG
        )
        hint_label.pack(side="bottom", pady=(0, 5))
        
        # Embed VLC into video frame
        self.update_idletasks()
        if platform.system() == "Windows":
            self.player.set_hwnd(self.video_frame.winfo_id())
        else:
            self.player.set_xwindow(self.video_frame.winfo_id())
    
    def _create_icon_button(self, parent, text, command):
        """Create a modern icon button"""
        btn = tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 16),
            fg=self.TEXT_COLOR,
            bg=self.CONTROLS_BG,
            cursor="hand2",
            padx=8,
            pady=2
        )
        btn.bind("<Button-1>", lambda e: command())
        btn.bind("<Enter>", lambda e: btn.config(bg=self.HOVER_COLOR))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.CONTROLS_BG))
        return btn
    
    def _bind_events(self):
        """Bind keyboard and mouse events"""
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Keyboard
        self.bind("<space>", lambda e: self._toggle_play())
        self.bind("<Left>", lambda e: self._seek_relative(-10000))
        self.bind("<Right>", lambda e: self._seek_relative(10000))
        self.bind("<Up>", lambda e: self._change_volume(5))
        self.bind("<Down>", lambda e: self._change_volume(-5))
        self.bind("<f>", lambda e: self._toggle_fullscreen())
        self.bind("<F>", lambda e: self._toggle_fullscreen())
        self.bind("<Escape>", lambda e: self._exit_fullscreen())
        self.bind("<g>", lambda e: self._sync_subtitle(-50000))
        self.bind("<G>", lambda e: self._sync_subtitle(-50000))
        self.bind("<h>", lambda e: self._sync_subtitle(50000))
        self.bind("<H>", lambda e: self._sync_subtitle(50000))
        self.bind("<m>", lambda e: self._toggle_mute())
        
        # Mouse - progress bar click
        self.progress_canvas.bind("<Button-1>", self._on_progress_click)
        
        # Double-click for fullscreen
        self.video_frame.bind("<Double-Button-1>", lambda e: self._toggle_fullscreen())
        
        # Auto-hide controls on mouse leave
        self.bind("<Motion>", self._on_mouse_motion)
    
    def _start_playback(self):
        """Initialize and start media playback"""
        logger.debug(f"Starting playback: {self.m3u8_url}")
        
        media = self.instance.media_new(self.m3u8_url)
        
        # Add HTTP options
        user_agent = self.idlix.request.headers.get("User-Agent", "Mozilla/5.0")
        media.add_option(f":http-user-agent={user_agent}")
        
        referer = self.idlix.BASE_STATIC_HEADERS.get("Referer")
        if referer:
            media.add_option(f":http-referrer={referer}")
        
        cookies = self.idlix.request.cookies.get_dict()
        if cookies:
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            media.add_option(f":http-cookie={cookie_str}")
        
        if self.subtitle:
            sub_path = os.path.abspath(self.subtitle)
            media.add_option(f":sub-file={sub_path}")
            logger.debug(f"Subtitle: {sub_path}")
        
        self.player.set_media(media)
        self.player.play()
        
        logger.debug("Playback started")
        self.log_state_id = self.after(1000, self._log_state)
    
    def _log_state(self):
        """Log player state for debugging"""
        if self._closed or not self.winfo_exists():
            return
        state = self.player.get_state()
        length = self.player.get_length()
        logger.debug(f"State: {state}, Length: {length}ms")
        if self.is_loading:
            self.log_state_id = self.after(2000, self._log_state)
    
    def _animate_loading(self):
        """Animate the loading spinner"""
        if self._closed or not self.winfo_exists() or not self.is_loading:
            return
        
        spinners = ["◐", "◓", "◑", "◒"]
        self.loading_dots = (self.loading_dots + 1) % 4
        self.spinner_label.config(text=spinners[self.loading_dots])
        
        # Update loading text with dots
        dots = "." * ((self.loading_dots % 3) + 1)
        self.loading_text.config(text=f"Loading{dots}")
        
        self.animate_loading_id = self.after(200, self._animate_loading)
    
    def _update_ui(self):
        """Update UI elements"""
        if self._closed or not self.winfo_exists():
            return
        
        state = self.player.get_state()
        
        # Handle loading state
        if self.is_loading:
            if state == vlc.State.Opening:
                self.loading_status.config(text="Opening stream...")
            elif state == vlc.State.Buffering:
                self.loading_status.config(text="Buffering...")
            elif state == vlc.State.Playing:
                self.is_loading = False
                self.loading_overlay.place_forget()
                self.btn_play.config(text="⏸")
                logger.info("Playback started")
            elif state == vlc.State.Error:
                self.loading_status.config(text="Error loading!", fg="red")
                logger.error("VLC error")
        
        # Buffering during playback
        if not self.is_loading:
            if state == vlc.State.Buffering:
                self.buffering_label.place(relx=0.5, rely=0.1, anchor="center")
            else:
                self.buffering_label.place_forget()
        
        # Update progress bar and time
        length = self.player.get_length()
        current = self.player.get_time()
        
        if length > 0:
            # Update progress bar
            canvas_width = self.progress_canvas.winfo_width()
            canvas_height = self.progress_canvas.winfo_height()
            progress_width = int((current / length) * canvas_width)
            self.progress_canvas.coords(self.progress_fill, 0, 0, progress_width, canvas_height)
            
            # Update time label
            self.time_label.config(text=f"{self._format_time(current)} / {self._format_time(length)}")
        
        self.update_ui_id = self.after(250, self._update_ui)
    
    def _format_time(self, ms):
        """Format milliseconds to readable time"""
        if ms < 0:
            return "0:00"
        seconds = ms // 1000
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02}:{s:02}"
        return f"{m}:{s:02}"
    
    def _toggle_play(self):
        """Toggle play/pause"""
        if self.player.is_playing():
            self.player.pause()
            self.btn_play.config(text="▶")
        else:
            self.player.play()
            self.btn_play.config(text="⏸")
    
    def _seek_relative(self, ms):
        """Seek relative to current position"""
        length = self.player.get_length()
        if length > 0:
            current = self.player.get_time()
            new_time = max(0, min(length, current + ms))
            self.player.set_time(int(new_time))
    
    def _on_progress_click(self, event):
        """Handle click on progress bar"""
        length = self.player.get_length()
        if length > 0:
            width = self.progress_canvas.winfo_width()
            pct = event.x / width
            self.player.set_position(max(0, min(1, pct)))
    
    def _on_volume(self, val):
        """Handle volume change"""
        vol = int(float(val))
        self.player.audio_set_volume(vol)
        self._update_volume_icon(vol)
    
    def _change_volume(self, delta):
        """Change volume by delta"""
        current = self.player.audio_get_volume()
        new_vol = max(0, min(100, current + delta))
        self.player.audio_set_volume(new_vol)
        self.vol_scale.set(new_vol)
        self._update_volume_icon(new_vol)
    
    def _toggle_mute(self):
        """Toggle mute"""
        self.player.audio_toggle_mute()
        if self.player.audio_get_mute():
            self.btn_mute.config(text="🔇")
        else:
            self._update_volume_icon(self.player.audio_get_volume())
    
    def _update_volume_icon(self, vol):
        """Update volume button icon based on level"""
        if vol == 0:
            self.btn_mute.config(text="🔇")
        elif vol < 50:
            self.btn_mute.config(text="🔉")
        else:
            self.btn_mute.config(text="🔊")
    
    def _sync_subtitle(self, delta_microseconds):
        """Adjust subtitle sync"""
        self.spu_delay += delta_microseconds
        self.player.video_set_spu_delay(self.spu_delay)
        ms = self.spu_delay // 1000
        self.sub_label.config(
            text=f"Sub: {ms:+}ms" if ms != 0 else "",
            fg="yellow" if ms != 0 else self.TEXT_DIM
        )
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        is_fs = self.attributes("-fullscreen")
        self.attributes("-fullscreen", not is_fs)
    
    def _exit_fullscreen(self):
        """Exit fullscreen"""
        self.attributes("-fullscreen", False)
    
    def _on_mouse_motion(self, event):
        """Show controls on mouse motion (fullscreen mode)"""
        if self._closed:
            return
        
        # In fullscreen: show controls on mouse move, hide after 3s
        if self.attributes("-fullscreen"):
            if not self.controls_visible:
                self.controls_overlay.pack(fill="x", side="bottom")
                self.controls_visible = True
            
            # Reset hide timer
            if self.hide_controls_id:
                try:
                    self.after_cancel(self.hide_controls_id)
                except:
                    pass
            self.hide_controls_id = self.after(3000, self._hide_controls)
    
    def _hide_controls(self):
        """Hide controls overlay (only in fullscreen)"""
        if self._closed or not self.winfo_exists():
            return
        
        # Only hide in fullscreen and when playing
        if self.attributes("-fullscreen") and self.player.is_playing():
            self.controls_overlay.pack_forget()
            self.controls_visible = False
    
    def _on_close(self):
        """Clean up on close"""
        # Mark as closed to stop all after callbacks
        self._closed = True
        
        # Cancel all pending after callbacks
        for after_id in [self.update_ui_id, self.animate_loading_id, self.hide_controls_id, self.log_state_id]:
            if after_id:
                try:
                    self.after_cancel(after_id)
                except:
                    pass
        
        if self.player:
            self.player.stop()
            self.player.release()
        
        # Cleanup subtitle files
        if self.subtitle and os.path.exists(self.subtitle):
            try:
                os.remove(self.subtitle)
                vtt = self.subtitle.rsplit('.', 1)[0] + '.vtt'
                if os.path.exists(vtt):
                    os.remove(vtt)
                logger.info("Subtitle files cleaned up")
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")
        
        self.destroy()


# Alias for backwards compatibility
VLCPlayerWindow = ModernVLCPlayer


def play_video_standalone(idlix, m3u8_url, subtitle=None, title="Video Player"):
    """Launch standalone VLC player"""
    if vlc is None:
        logger.error("python-vlc not found")
        return False
    
    root = tk.Tk()
    root.withdraw()
    
    player = ModernVLCPlayer(root, idlix, m3u8_url, subtitle, title)
    
    def on_close():
        player._on_close()
        root.destroy()
    
    player.protocol("WM_DELETE_WINDOW", on_close)
    root.wait_window(player)
    return True
