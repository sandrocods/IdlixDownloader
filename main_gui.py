"""
IDLIX Downloader & Player - Modern GUI
Features: Movies, TV Series, Multi-Subtitle Support
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import subprocess
import os
import time
import webbrowser
from io import BytesIO
import platform

try:
    import vlc
except ImportError:
    vlc = None

from PIL import Image, ImageTk
import requests

from src.idlixHelper import IdlixHelper, logger
from src.vlc_player import VLCPlayerWindow
from src.download_manager import DownloadManager

# ============================================================
# THEME COLORS (Dark Mode)
# ============================================================
COLORS = {
    "bg": "#0f0f0f",
    "bg_secondary": "#1a1a1a",
    "bg_tertiary": "#252525",
    "accent": "#e50914",  # Netflix red
    "accent_hover": "#f40612",
    "text": "#ffffff",
    "text_dim": "#b3b3b3",
    "text_muted": "#666666",
    "success": "#46d369",
    "warning": "#f5c518",
    "error": "#e50914",
    "border": "#333333",
}

# ============================================================
# RETRY logic
# ============================================================
RETRY_LIMIT = 3

def retry(func, *args, **kwargs):
    for _ in range(RETRY_LIMIT):
        result = func(*args, **kwargs)
        if result and result.get("status"):
            return result
        time.sleep(1)
    return {"status": False, "message": "Maximum retry reached"}


# ============================================================
# CUSTOM WIDGETS
# ============================================================
class ModernButton(tk.Button):
    """Modern styled button"""
    def __init__(self, parent, text, command=None, style="primary", **kwargs):
        if style == "primary":
            bg = COLORS["accent"]
            fg = COLORS["text"]
            hover_bg = COLORS["accent_hover"]
        elif style == "secondary":
            bg = COLORS["bg_tertiary"]
            fg = COLORS["text"]
            hover_bg = COLORS["border"]
        else:
            bg = COLORS["bg_secondary"]
            fg = COLORS["text_dim"]
            hover_bg = COLORS["bg_tertiary"]
        
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=fg,
            relief="flat",
            font=("Segoe UI", 10),
            cursor="hand2",
            padx=15,
            pady=8,
            **kwargs
        )
        self.default_bg = bg
        self.hover_bg = hover_bg
        self.bind("<Enter>", lambda e: self.config(bg=self.hover_bg))
        self.bind("<Leave>", lambda e: self.config(bg=self.default_bg))


class ModernFrame(tk.Frame):
    """Dark themed frame"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg"], **kwargs)


class ModernLabel(tk.Label):
    """Dark themed label"""
    def __init__(self, parent, text="", style="normal", **kwargs):
        if style == "title":
            font = ("Segoe UI", 18, "bold")
            fg = COLORS["text"]
        elif style == "subtitle":
            font = ("Segoe UI", 14, "bold")
            fg = COLORS["text"]
        elif style == "dim":
            font = ("Segoe UI", 10)
            fg = COLORS["text_dim"]
        else:
            font = ("Segoe UI", 11)
            fg = COLORS["text"]
        
        super().__init__(
            parent,
            text=text,
            bg=COLORS["bg"],
            fg=fg,
            font=font,
            **kwargs
        )


# ============================================================
# GUI LOGGER
# ============================================================
class GuiLogger:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, msg):
        self.textbox.configure(state='normal')
        self.textbox.insert(tk.END, msg)
        self.textbox.see(tk.END)
        self.textbox.configure(state='disabled')

    def flush(self):
        pass


# ============================================================
# MAIN GUI
# ============================================================
class IdlixGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 IDLIX Downloader & Player")
        self.root.geometry("1300x750")
        self.root.configure(bg=COLORS["bg"])
        self.root.minsize(1100, 600)

        self.idlix = IdlixHelper()
        self.active_helper = None  # Track currently downloading helper for cancel
        self.cancel_requested = False  # Global cancel flag
        self.featured_movies = []
        self.featured_series = []
        self.poster_images = []
        self.ffplay_process = None
        self.current_tab = "movies"

        # Check VLC
        if vlc is None:
            messagebox.showwarning("VLC Missing", "python-vlc module not found. Player will fall back to ffplay.")

        self._create_ui()
        self._setup_logger()
        
        # Load content in background to avoid blocking UI
        threading.Thread(target=self.refresh_content, daemon=True).start()

    def _create_ui(self):
        """Create the main UI layout"""
        # Main container
        main_container = ModernFrame(self.root)
        main_container.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Header
        header = ModernFrame(main_container)
        header.pack(fill="x", pady=(0, 15))
        
        ModernLabel(header, text="🎬 IDLIX Downloader & Player", style="title").pack(side="left")
        
        # Header buttons
        btn_frame = ModernFrame(header)
        btn_frame.pack(side="right")
        
        ModernButton(btn_frame, "🔄 Refresh", self.refresh_content, style="secondary").pack(side="left", padx=5)
        ModernButton(btn_frame, "📂 Downloads", self.open_download_folder, style="secondary").pack(side="left", padx=5)
        ModernButton(btn_frame, "🔗 URL", self.play_by_url, style="primary").pack(side="left", padx=5)
        
        # Content area (left = content, right = log)
        content_frame = ModernFrame(main_container)
        content_frame.pack(fill="both", expand=True)
        
        # Left panel - Tabs + Content
        left_panel = ModernFrame(content_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Tab buttons
        tab_frame = ModernFrame(left_panel)
        tab_frame.pack(fill="x", pady=(0, 10))
        
        self.tab_movies_btn = ModernButton(tab_frame, "🎬 Movies", lambda: self.switch_tab("movies"), style="primary")
        self.tab_movies_btn.pack(side="left", padx=(0, 5))
        
        self.tab_series_btn = ModernButton(tab_frame, "📺 TV Series", lambda: self.switch_tab("series"), style="secondary")
        self.tab_series_btn.pack(side="left", padx=5)
        
        # Scrollable content area
        self.content_canvas = tk.Canvas(left_panel, bg=COLORS["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(left_panel, orient="vertical", command=self.content_canvas.yview, 
                                  bg=COLORS["bg_secondary"], troughcolor=COLORS["bg"])
        self.content_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.content_canvas.pack(side="left", fill="both", expand=True)
        
        self.poster_frame = ModernFrame(self.content_canvas)
        self.content_canvas.create_window((0, 0), window=self.poster_frame, anchor="nw")
        
        self.poster_frame.bind("<Configure>", 
            lambda e: self.content_canvas.configure(scrollregion=self.content_canvas.bbox("all")))
        
        # Mouse wheel scrolling
        self.content_canvas.bind_all("<MouseWheel>", 
            lambda e: self.content_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        # Right panel - Log
        right_panel = ModernFrame(content_frame, width=350)
        right_panel.pack(side="right", fill="y")
        right_panel.pack_propagate(False)
        
        ModernLabel(right_panel, text="📋 Log Output", style="subtitle").pack(anchor="w", pady=(0, 10))
        
        # Log text box
        log_frame = tk.Frame(right_panel, bg=COLORS["border"], padx=1, pady=1)
        log_frame.pack(fill="both", expand=True)
        
        self.log_box = tk.Text(
            log_frame, 
            state='disabled', 
            bg=COLORS["bg_secondary"], 
            fg=COLORS["success"],
            font=("Consolas", 9),
            wrap="word",
            relief="flat",
            padx=10,
            pady=10
        )
        self.log_box.pack(fill="both", expand=True)
        
        # Progress bar (hidden by default)
        self.progress_frame = ModernFrame(right_panel)
        
        self.progress_label = ModernLabel(self.progress_frame, text="Downloading...", style="dim")
        self.progress_label.pack(anchor="w", pady=(5, 2))
        
        self.progress_bar = ttk.Progressbar(
            self.progress_frame,
            mode='determinate',
            length=330,
            maximum=100
        )
        self.progress_bar.pack(fill="x", pady=(0, 5))
        
        self.progress_status = ModernLabel(self.progress_frame, text="0%", style="dim")
        self.progress_status.pack(anchor="w")
        
        self.cancel_btn = ModernButton(self.progress_frame, "❌ Cancel", self.cancel_download, style="secondary")
        self.cancel_btn.pack(fill="x", pady=(5, 0))
        
        # Clear log button
        ModernButton(right_panel, "🗑️ Clear Log", self.clear_log, style="secondary").pack(fill="x", pady=(10, 0))

    def _setup_logger(self):
        """Setup loguru to write to GUI"""
        logger.remove()
        logger.add(GuiLogger(self.log_box), format="{time:HH:mm:ss} | {level} | {message}")

    def switch_tab(self, tab):
        """Switch between Movies and Series tabs"""
        self.current_tab = tab
        
        if tab == "movies":
            self.tab_movies_btn.config(bg=COLORS["accent"])
            self.tab_movies_btn.default_bg = COLORS["accent"]
            self.tab_series_btn.config(bg=COLORS["bg_tertiary"])
            self.tab_series_btn.default_bg = COLORS["bg_tertiary"]
            self.show_poster_grid(self.featured_movies, "movie")
        else:
            self.tab_series_btn.config(bg=COLORS["accent"])
            self.tab_series_btn.default_bg = COLORS["accent"]
            self.tab_movies_btn.config(bg=COLORS["bg_tertiary"])
            self.tab_movies_btn.default_bg = COLORS["bg_tertiary"]
            self.show_poster_grid(self.featured_series, "series")

    def show_poster_grid(self, items, content_type):
        """Display poster grid for movies or series"""
        for w in self.poster_frame.winfo_children():
            w.destroy()
        self.poster_images.clear()
        
        if not items:
            ModernLabel(self.poster_frame, text="No content found. Click Refresh.", style="dim").pack(pady=50)
            return
        
        posters_per_row = 5
        size = (160, 240)
        row = col = 0
        
        for item in items:
            try:
                img_raw = requests.get(item["poster"], timeout=8).content
                img = Image.open(BytesIO(img_raw)).resize(size, Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
            except:
                continue
            
            self.poster_images.append(tk_img)
            
            # Card frame
            card = tk.Frame(self.poster_frame, bg=COLORS["bg_secondary"], cursor="hand2")
            card.grid(row=row, column=col, padx=8, pady=8)
            
            # Poster image button
            poster_btn = tk.Button(
                card, 
                image=tk_img, 
                relief="flat", 
                bg=COLORS["bg_secondary"],
                activebackground=COLORS["bg_tertiary"],
                cursor="hand2",
                command=lambda i=item, t=content_type: self.on_poster_click(i, t)
            )
            poster_btn.pack(padx=2, pady=2)
            
            # Title
            title_label = tk.Label(
                card,
                text=item["title"][:25] + "..." if len(item["title"]) > 25 else item["title"],
                bg=COLORS["bg_secondary"],
                fg=COLORS["text"],
                font=("Segoe UI", 9),
                wraplength=155,
                justify="center"
            )
            title_label.pack(pady=(5, 2))
            
            # Year badge
            year_label = tk.Label(
                card,
                text=item.get("year", ""),
                bg=COLORS["bg_secondary"],
                fg=COLORS["text_dim"],
                font=("Segoe UI", 8)
            )
            year_label.pack(pady=(0, 5))
            
            col += 1
            if col >= posters_per_row:
                col = 0
                row += 1

    def on_poster_click(self, item, content_type):
        """Handle poster click - show action popup"""
        popup = tk.Toplevel(self.root)
        popup.title(item["title"])
        popup.geometry("400x280")
        popup.configure(bg=COLORS["bg"])
        popup.resizable(False, False)
        
        # Center popup
        popup.transient(self.root)
        popup.grab_set()
        
        # Content
        ModernLabel(popup, text=item["title"], style="subtitle", wraplength=350).pack(pady=20)
        
        type_text = "📺 TV Series" if content_type == "series" else "🎬 Movie"
        ModernLabel(popup, text=f"{type_text} • {item.get('year', '')}", style="dim").pack()
        
        btn_frame = ModernFrame(popup)
        btn_frame.pack(pady=30)
        
        if content_type == "series":
            ModernButton(btn_frame, "▶️ Browse Episodes", 
                        lambda: [popup.destroy(), self.browse_series(item)], 
                        style="primary").pack(pady=5)
        else:
            ModernButton(btn_frame, "▶️ Play", 
                        lambda: [popup.destroy(), self.process_movie(item["url"], "play")], 
                        style="primary").pack(pady=5)
            ModernButton(btn_frame, "📥 Download", 
                        lambda: [popup.destroy(), self.process_movie(item["url"], "download")], 
                        style="secondary").pack(pady=5)
        
        ModernButton(btn_frame, "❌ Cancel", popup.destroy, style="secondary").pack(pady=5)

    def browse_series(self, series):
        """Browse series seasons and episodes"""
        def task():
            logger.info(f"Loading series: {series['title']}...")
            result = retry(self.idlix.get_series_info, series["url"])
            
            if not result.get("status"):
                logger.error(f"Failed to load series: {result.get('message')}")
                return
            
            series_info = result["series_info"]
            self.root.after(0, lambda: self.show_series_browser(series_info))
        
        threading.Thread(target=task, daemon=True).start()

    def show_series_browser(self, series_info):
        """Show series browser dialog"""
        popup = tk.Toplevel(self.root)
        popup.title(f"📺 {series_info['title']}")
        popup.geometry("600x500")
        popup.configure(bg=COLORS["bg"])
        popup.transient(self.root)
        popup.grab_set()
        
        # Header
        ModernLabel(popup, text=series_info["title"], style="title").pack(pady=(15, 5))
        ModernLabel(popup, text=f"{len(series_info['seasons'])} Seasons", style="dim").pack()
        
        # Main content
        content = ModernFrame(popup)
        content.pack(fill="both", expand=True, padx=15, pady=15)
        
        # Season list (left)
        left = ModernFrame(content)
        left.pack(side="left", fill="y", padx=(0, 10))
        
        ModernLabel(left, text="Seasons", style="subtitle").pack(anchor="w", pady=(0, 10))
        
        season_listbox = tk.Listbox(
            left,
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            font=("Segoe UI", 11),
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text"],
            relief="flat",
            width=15,
            height=15
        )
        season_listbox.pack(fill="y", expand=True)
        
        for s in series_info["seasons"]:
            season_listbox.insert(tk.END, f"Season {s['season']}")
        
        # Episode list (right)
        right = ModernFrame(content)
        right.pack(side="right", fill="both", expand=True)
        
        ModernLabel(right, text="Episodes", style="subtitle").pack(anchor="w", pady=(0, 10))
        
        episode_frame = tk.Frame(right, bg=COLORS["bg"])
        episode_frame.pack(fill="both", expand=True)
        
        episode_canvas = tk.Canvas(episode_frame, bg=COLORS["bg"], highlightthickness=0)
        episode_scrollbar = tk.Scrollbar(episode_frame, orient="vertical", command=episode_canvas.yview)
        episode_canvas.configure(yscrollcommand=episode_scrollbar.set)
        
        episode_scrollbar.pack(side="right", fill="y")
        episode_canvas.pack(side="left", fill="both", expand=True)
        
        episode_list = ModernFrame(episode_canvas)
        episode_canvas.create_window((0, 0), window=episode_list, anchor="nw")
        
        def show_episodes(event=None):
            sel = season_listbox.curselection()
            if not sel:
                return
            
            for w in episode_list.winfo_children():
                w.destroy()
            
            season = series_info["seasons"][sel[0]]
            
            # Download All button at top
            dl_all_frame = tk.Frame(episode_list, bg=COLORS["bg"])
            dl_all_frame.pack(fill="x", pady=(0, 10))
            
            ModernButton(dl_all_frame, f"📥 Download All ({len(season['episodes'])} eps)", 
                lambda s=season: [popup.destroy(), self.batch_download_season(series_info, s)],
                style="primary").pack(fill="x")
            
            for i, ep in enumerate(season["episodes"]):
                ep_frame = tk.Frame(episode_list, bg=COLORS["bg_secondary"], cursor="hand2")
                ep_frame.pack(fill="x", pady=2)
                
                ep_label = tk.Label(
                    ep_frame,
                    text=ep["full_title"],
                    bg=COLORS["bg_secondary"],
                    fg=COLORS["text"],
                    font=("Segoe UI", 10),
                    anchor="w",
                    padx=10,
                    pady=8
                )
                ep_label.pack(side="left", fill="x", expand=True)
                
                # Build episode_info for organized folder
                ep_info = {
                    'series_title': series_info['title'],
                    'series_year': series_info.get('year', '2025'),
                    'season_num': ep.get('season_num', season['season']),
                    'episode_num': ep.get('episode_num', i + 1)
                }
                
                play_btn = ModernButton(ep_frame, "▶️", 
                    lambda e=ep: [popup.destroy(), self.process_episode(e["url"], "play")],
                    style="primary")
                play_btn.pack(side="right", padx=2)
                
                dl_btn = ModernButton(ep_frame, "📥", 
                    lambda e=ep, info=ep_info: [popup.destroy(), self.process_episode(e["url"], "download", info)],
                    style="secondary")
                dl_btn.pack(side="right", padx=2)
            
            episode_list.update_idletasks()
            episode_canvas.configure(scrollregion=episode_canvas.bbox("all"))
        
        season_listbox.bind("<<ListboxSelect>>", show_episodes)
        
        # Select first season
        if series_info["seasons"]:
            season_listbox.selection_set(0)
            show_episodes()
        
        # Close button
        ModernButton(popup, "❌ Close", popup.destroy, style="secondary").pack(pady=10)

    def batch_download_season(self, series_info, season):
        """Download all episodes in a season with preset resolution/subtitle"""
        def task():
            # Reset cancel flags
            self.cancel_requested = False
            self.idlix.cancel_flag = False
            
            total = len(season['episodes'])
            logger.info(f"📥 Batch download: {total} episodes from Season {season['season']}")
            
            # === Pre-select resolution and subtitle for first episode ===
            first_ep = season['episodes'][0]
            logger.info("Setting up resolution and subtitle for all episodes...")
            
            # Get first episode data to determine available resolutions/subtitles
            first_helper = IdlixHelper()
            result = DownloadManager.prepare_episode_download(first_helper, first_ep['url'])
            if not result:
                logger.error("Failed to get first episode data")
                return
            
            video_data, embed, m3u8 = result
            
            # Select resolution once
            preset_resolution = None
            if m3u8.get("is_variant_playlist"):
                logger.info("Select resolution for ALL episodes:")
                selected_id = None
                def ask_res():
                    nonlocal selected_id
                    selected_id = self.select_resolution_dialog(m3u8["variant_playlist"])
                self.root.after(0, ask_res)
                while selected_id is None:
                    time.sleep(0.1)
                preset_resolution = selected_id
                
                for v in m3u8["variant_playlist"]:
                    if str(v["id"]) == preset_resolution:
                        logger.success(f"Resolution {v['resolution']} will be used for all episodes")
                        break
            
            # Select subtitle once
            preset_subtitle = None
            subs_result = first_helper.get_available_subtitles()
            if subs_result.get("status") and subs_result.get("subtitles"):
                logger.info("Select subtitle for ALL episodes:")
                sub_holder = {"value": None, "done": False}
                def ask_sub():
                    sub_holder["value"] = self.select_subtitle_dialog(subs_result["subtitles"])
                    sub_holder["done"] = True
                self.root.after(0, ask_sub)
                while not sub_holder["done"]:
                    time.sleep(0.1)
                
                if sub_holder["value"]:
                    preset_subtitle = sub_holder["value"]
                    for s in subs_result["subtitles"]:
                        if s["id"] == preset_subtitle:
                            logger.success(f"Subtitle {s['label']} will be used for all episodes")
                            break
                else:
                    preset_subtitle = ""  # Empty string = no subtitle
                    logger.info("No subtitle will be downloaded for all episodes")
            
            # Select subtitle mode once (if subtitle selected)
            preset_sub_mode = None
            if preset_subtitle and preset_subtitle != "":
                sub_mode = None
                def ask_mode():
                    nonlocal sub_mode
                    sub_mode = self.select_subtitle_mode_dialog()
                self.root.after(0, ask_mode)
                while sub_mode is None:
                    time.sleep(0.1)
                preset_sub_mode = sub_mode
                logger.success(f"Subtitle mode: {preset_sub_mode}")
            
            logger.info("=" * 50)
            logger.info("Starting batch download...")
            logger.info("=" * 50)
            
            # Show progress bar AFTER all dialogs complete
            self.root.after(0, lambda: self.show_progress("Batch downloading episodes..."))
            
            # Now download all episodes with preset settings
            for i, ep in enumerate(season['episodes']):
                # Check cancel BEFORE any processing
                if self.cancel_requested or self.idlix.cancel_flag:
                    logger.warning("Batch download cancelled by user")
                    break
                
                logger.info(f"\n{'='*50}")
                logger.info(f"Episode {i+1}/{total}: {ep['full_title']}")
                
                # Create new helper for each episode
                ep_helper = IdlixHelper()
                ep_helper.cancel_flag = self.cancel_requested  # Sync cancel state
                self.active_helper = ep_helper  # Register for cancel button
                
                # Build episode info for organized folder structure
                episode_info = {
                    'series_title': series_info['title'],
                    'series_year': series_info.get('year', '2025'),
                    'season_num': ep.get('season_num', season['season']),
                    'episode_num': ep.get('episode_num', i + 1)
                }
                
                # === PREPARE: Get all metadata ===
                result = DownloadManager.prepare_episode_download(ep_helper, ep['url'], episode_info)
                if not result:
                    logger.warning(f"Failed to prepare episode, skipping...")
                    continue
                
                video_data, embed, m3u8 = result
                
                # Apply preset resolution
                if preset_resolution and m3u8.get("is_variant_playlist"):
                    for v in m3u8["variant_playlist"]:
                        if str(v["id"]) == preset_resolution:
                            ep_helper.set_m3u8_url(v["uri"])
                            break
                
                # Set progress callback
                def progress_update(percent, status=""):
                    self.root.after(0, lambda p=percent, s=status: self.update_progress(p, s))
                ep_helper.progress_callback = progress_update
                self.root.after(0, lambda idx=i+1, t=total: self.show_progress(f"Episode {idx}/{t}"))
                
                # Check cancel one more time before download
                if self.cancel_requested or self.idlix.cancel_flag:
                    logger.warning("Batch download cancelled by user")
                    break
                
                # === DOWNLOAD: Use unified logic ===
                download_result = DownloadManager.execute_download(
                    ep_helper, video_data, preset_resolution, preset_subtitle, preset_sub_mode
                )
                
                if not download_result.get("status"):
                    logger.warning(f"Failed to download: {download_result.get('message')}")
                    # Check if error is cancellation
                    if 'cancelled' in download_result.get('message', '').lower():
                        break
            
            self.active_helper = None  # Clear active helper
            logger.success(f"🎉 Season {season['season']} download complete!")
            
            # Hide progress bar after batch complete
            self.root.after(0, self.hide_progress)
        
        threading.Thread(target=task, daemon=True).start()

    def select_subtitle_dialog(self, subtitles):
        """Show subtitle selection dialog"""
        popup = tk.Toplevel(self.root)
        popup.title("Select Subtitle")
        popup.geometry("350x300")
        popup.configure(bg=COLORS["bg"])
        popup.transient(self.root)
        popup.grab_set()
        
        ModernLabel(popup, text="🗣️ Select Subtitle", style="subtitle").pack(pady=15)
        
        result = {"id": None, "done": False}
        
        listbox = tk.Listbox(
            popup,
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            font=("Segoe UI", 11),
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text"],
            relief="flat",
            height=8
        )
        listbox.pack(fill="x", padx=20, pady=10)
        
        for sub in subtitles:
            listbox.insert(tk.END, f"{sub['id']} - {sub['label']}")
        listbox.insert(tk.END, "No Subtitle")
        listbox.selection_set(0)
        
        def confirm():
            sel = listbox.curselection()
            if sel:
                text = listbox.get(sel[0])
                if text != "No Subtitle":
                    result["id"] = text.split(" - ")[0]
            result["done"] = True
            popup.destroy()
        
        def on_close():
            result["done"] = True
            popup.destroy()
        
        popup.protocol("WM_DELETE_WINDOW", on_close)
        ModernButton(popup, "✓ Select", confirm, style="primary").pack(pady=10)
        
        self.root.wait_window(popup)
        return result["id"]

    def select_subtitle_mode_dialog(self):
        """Show subtitle mode selection dialog"""
        popup = tk.Toplevel(self.root)
        popup.title("Subtitle Mode")
        popup.geometry("400x280")
        popup.configure(bg=COLORS["bg"])
        popup.transient(self.root)
        popup.grab_set()
        
        ModernLabel(popup, text="📝 Subtitle Mode", style="subtitle").pack(pady=15)
        
        result = {"mode": "separate", "done": False}
        
        listbox = tk.Listbox(
            popup,
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            font=("Segoe UI", 11),
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text"],
            relief="flat",
            height=5
        )
        listbox.pack(fill="x", padx=20, pady=10)
        
        modes = [
            ("Separate File (.srt) - Fast, file terpisah", "separate"),
            ("Softcode (Embed) - Fast, subtitle track di MKV", "softcode"),
            ("Hardcode (Burn-in) - Slow, permanent di video", "hardcode")
        ]
        
        for label, _ in modes:
            listbox.insert(tk.END, label)
        listbox.selection_set(0)
        
        def confirm():
            sel = listbox.curselection()
            if sel:
                result["mode"] = modes[sel[0]][1]
            result["done"] = True
            popup.destroy()
        
        def on_close():
            result["done"] = True
            popup.destroy()
        
        popup.protocol("WM_DELETE_WINDOW", on_close)
        ModernButton(popup, "✓ Select", confirm, style="primary").pack(pady=10)
        
        self.root.wait_window(popup)
        return result["mode"]

    def select_resolution_dialog(self, variants):
        """Show resolution selection dialog"""
        popup = tk.Toplevel(self.root)
        popup.title("Select Resolution")
        popup.geometry("350x300")
        popup.configure(bg=COLORS["bg"])
        popup.transient(self.root)
        popup.grab_set()
        
        ModernLabel(popup, text="📺 Select Resolution", style="subtitle").pack(pady=15)
        
        result = {"id": None, "done": False}
        
        listbox = tk.Listbox(
            popup,
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            font=("Segoe UI", 11),
            selectbackground=COLORS["accent"],
            selectforeground=COLORS["text"],
            relief="flat",
            height=8
        )
        listbox.pack(fill="x", padx=20, pady=10)
        
        for v in variants:
            listbox.insert(tk.END, f"{v['id']} - {v['resolution']}")
        
        # Select highest resolution by default
        listbox.selection_set(len(variants) - 1)
        
        def confirm():
            sel = listbox.curselection()
            if sel:
                result["id"] = listbox.get(sel[0]).split(" - ")[0]
            result["done"] = True
            popup.destroy()
        
        def on_close():
            result["done"] = True
            popup.destroy()
        
        popup.protocol("WM_DELETE_WINDOW", on_close)
        ModernButton(popup, "✓ Select", confirm, style="primary").pack(pady=10)
        
        self.root.wait_window(popup)
        return result["id"]

    def refresh_content(self):
        """Refresh both movies and series"""
        def task():
            # Clear existing posters first
            self.root.after(0, lambda: self.show_poster_grid([], "movie"))
            logger.info("Loading featured content...")
            
            # Load movies
            home = retry(self.idlix.get_home)
            if home.get("status"):
                self.featured_movies = home.get("featured_movie", [])
                logger.success(f"Loaded {len(self.featured_movies)} movies")
            
            # Load series
            series = retry(self.idlix.get_featured_series)
            if series.get("status"):
                self.featured_series = series.get("featured_series", [])
                logger.success(f"Loaded {len(self.featured_series)} series")
            
            # Update UI
            self.root.after(0, lambda: self.switch_tab(self.current_tab))
        
        threading.Thread(target=task, daemon=True).start()

    def play_by_url(self):
        """Play or download by URL"""
        popup = tk.Toplevel(self.root)
        popup.title("Play/Download by URL")
        popup.geometry("500x200")
        popup.configure(bg=COLORS["bg"])
        popup.transient(self.root)
        popup.grab_set()
        
        ModernLabel(popup, text="🔗 Enter IDLIX URL", style="subtitle").pack(pady=15)
        
        entry = tk.Entry(
            popup,
            bg=COLORS["bg_secondary"],
            fg=COLORS["text"],
            font=("Segoe UI", 11),
            relief="flat",
            insertbackground=COLORS["text"]
        )
        entry.pack(fill="x", padx=30, pady=10, ipady=8)
        entry.focus()
        
        btn_frame = ModernFrame(popup)
        btn_frame.pack(pady=15)
        
        def play():
            url = entry.get().strip()
            if url:
                popup.destroy()
                self.handle_url(url, "play")
        
        def download():
            url = entry.get().strip()
            if url:
                popup.destroy()
                self.handle_url(url, "download")
        
        ModernButton(btn_frame, "▶️ Play", play, style="primary").pack(side="left", padx=5)
        ModernButton(btn_frame, "📥 Download", download, style="secondary").pack(side="left", padx=5)
        ModernButton(btn_frame, "❌ Cancel", popup.destroy, style="secondary").pack(side="left", padx=5)

    def handle_url(self, url, mode):
        """Handle URL - detect type and process"""
        if "/episode/" in url:
            # For episode URL, try to extract series info for folder structure
            if mode == "download":
                self._process_episode_with_folder(url, mode)
            else:
                self.process_episode(url, mode)
        elif "/tvseries/" in url:
            # Browse series
            def task():
                logger.info("Loading series from URL...")
                result = retry(self.idlix.get_series_info, url)
                if result.get("status"):
                    self.root.after(0, lambda: self.show_series_browser(result["series_info"]))
                else:
                    logger.error(f"Failed: {result.get('message')}")
            threading.Thread(target=task, daemon=True).start()
        else:
            self.process_movie(url, mode)

    def _process_episode_with_folder(self, url, mode):
        """Process episode URL and create folder structure by extracting info from URL/page"""
        import re
        
        def task():
            # Create new helper
            idlix = IdlixHelper()
            idlix.cancel_flag = False
            self.active_helper = idlix  # Register for cancel button
            self.cancel_requested = False  # Reset cancel flag
            
            # Try to extract season/episode from URL pattern
            # Example: https://tv12.idlixku.com/episode/series-name-season-1-episode-5/
            match = re.search(r'/episode/(.+)-season-(\d+)-episode-(\d+)', url)
            
            episode_info = None
            if match:
                # Extract from URL first
                season_num = int(match.group(2))
                episode_num = int(match.group(3))
                
                # Get episode data to extract proper series info from page
                video_data = retry(idlix.get_episode_data, url)
                if video_data.get("status") and video_data.get('series_info'):
                    series_info = video_data['series_info']
                    series_title = series_info.get('series_title', match.group(1).replace('-', ' ').title())
                    series_year = series_info.get('series_year', '2025')
                else:
                    # Fallback to URL parsing
                    series_title = match.group(1).replace('-', ' ').title()
                    series_year = '2025'
                
                episode_info = {
                    'series_title': series_title,
                    'series_year': series_year,
                    'season_num': season_num,
                    'episode_num': episode_num
                }
                logger.info(f"📁 Detected: {series_title} ({series_year}) S{season_num:02d}E{episode_num:02d}")
            
            # === PREPARE: Get all metadata ===
            result = DownloadManager.prepare_episode_download(idlix, url, episode_info)
            if not result:
                return
            
            video_data, embed, m3u8 = result
            
            # === DIALOGS: Ask user for preferences ===
            resolution_id = None
            if m3u8.get("is_variant_playlist"):
                result_holder = {"value": None, "done": False}
                def ask():
                    result_holder["value"] = self.select_resolution_dialog(m3u8["variant_playlist"])
                    result_holder["done"] = True
                self.root.after(0, ask)
                while not result_holder["done"]:
                    time.sleep(0.1)
                
                selected_id = result_holder["value"]
                if selected_id:
                    resolution_id = selected_id
                    for v in m3u8["variant_playlist"]:
                        if str(v["id"]) == selected_id:
                            idlix.set_m3u8_url(v["uri"])
                            logger.success(f"Resolution: {v['resolution']}")
                            break
            
            subtitle_id = None
            subtitle_mode = 'separate'
            subs = idlix.get_available_subtitles()
            if subs.get("status") and subs.get("subtitles"):
                result_holder = {"value": None, "done": False}
                def ask_sub():
                    result_holder["value"] = self.select_subtitle_dialog(subs["subtitles"])
                    result_holder["done"] = True
                self.root.after(0, ask_sub)
                while not result_holder["done"]:
                    time.sleep(0.1)
                
                subtitle_id = result_holder["value"] if result_holder["value"] else ""  # "" = no subtitle
                
                # Ask for subtitle mode if subtitle selected
                if subtitle_id and subtitle_id != "":
                    result_holder = {"value": None, "done": False}
                    def ask_mode():
                        result_holder["value"] = self.select_subtitle_mode_dialog()
                        result_holder["done"] = True
                    self.root.after(0, ask_mode)
                    while not result_holder["done"]:
                        time.sleep(0.1)
                    subtitle_mode = result_holder["value"]
            
            # Show progress bar AFTER all dialogs complete
            def progress_update(percent, status=""):
                self.root.after(0, lambda p=percent, s=status: self.update_progress(p, s))
            idlix.progress_callback = progress_update
            self.root.after(0, lambda: self.show_progress("Downloading episode..."))
            
            # === DOWNLOAD: Use unified logic ===
            result = DownloadManager.execute_download(
                idlix, video_data, resolution_id, subtitle_id, subtitle_mode
            )
            
            self.active_helper = None  # Clear active helper
            # Hide progress bar
            self.root.after(0, self.hide_progress)
        
        threading.Thread(target=task, daemon=True).start()

    def process_movie(self, url: str, mode: str):
        """Process movie for play/download"""
        def task():
            idlix = IdlixHelper()  # Create new instance for clean state
            idlix.cancel_flag = False
            self.active_helper = idlix  # Register for cancel button
            self.cancel_requested = False  # Reset cancel flag
            
            # === PREPARE: Get all metadata ===
            result = DownloadManager.prepare_movie_download(idlix, url)
            if not result:
                return
            
            video_data, embed, m3u8 = result
            
            # === DIALOGS: Ask user for preferences ===
            resolution_id = None
            if m3u8.get("is_variant_playlist"):
                selected_id = None
                def ask():
                    nonlocal selected_id
                    selected_id = self.select_resolution_dialog(m3u8["variant_playlist"])
                self.root.after(0, ask)
                while selected_id is None:
                    time.sleep(0.1)
                
                resolution_id = selected_id
                for v in m3u8["variant_playlist"]:
                    if str(v["id"]) == resolution_id:
                        idlix.set_m3u8_url(v["uri"])
                        logger.success(f"Resolution: {v['resolution']}")
                        break
            
            subtitle_id = None
            subtitle_file = None
            subtitle_mode = 'separate'
            
            subs = idlix.get_available_subtitles()
            if subs.get("status") and subs.get("subtitles"):
                sub_holder = {"value": None, "done": False}
                def ask_sub():
                    sub_holder["value"] = self.select_subtitle_dialog(subs["subtitles"])
                    sub_holder["done"] = True
                self.root.after(0, ask_sub)
                while not sub_holder["done"]:
                    time.sleep(0.1)
                
                subtitle_id = sub_holder["value"] if sub_holder["value"] else ""  # "" = no subtitle
                
                # Ask for subtitle mode if subtitle selected
                if subtitle_id and subtitle_id != "":
                    mode_holder = {"value": None, "done": False}
                    def ask_mode():
                        mode_holder["value"] = self.select_subtitle_mode_dialog()
                        mode_holder["done"] = True
                    self.root.after(0, ask_mode)
                    while not mode_holder["done"]:
                        time.sleep(0.1)
                    subtitle_mode = mode_holder["value"]
            
            # === PLAY or DOWNLOAD ===
            if mode == "play":
                # For play: download subtitle separately for VLC
                if subtitle_id and subtitle_id != "":
                    sub_result = idlix.download_selected_subtitle(subtitle_id)
                    if sub_result.get("status"):
                        subtitle_file = sub_result.get("subtitle")
                        logger.success(f"Subtitle: {sub_result.get('label')}")
                
                if vlc:
                    logger.info("Opening VLC Player...")
                    self.root.after(0, lambda: VLCPlayerWindow(
                        self.root, idlix, idlix.m3u8_url, subtitle_file, video_data['video_name']
                    ))
                else:
                    self.start_ffplay(idlix.m3u8_url, subtitle_file)
            else:
                # === DOWNLOAD: Use unified logic ===
                def progress_update(percent, status=""):
                    self.root.after(0, lambda p=percent, s=status: self.update_progress(p, s))
                idlix.progress_callback = progress_update
                self.root.after(0, lambda: self.show_progress("Downloading movie..."))
                
                result = DownloadManager.execute_download(
                    idlix, video_data, resolution_id, subtitle_id, subtitle_mode
                )
                
                self.active_helper = None  # Clear active helper
                # Hide progress bar after download
                self.root.after(0, self.hide_progress)
        
        threading.Thread(target=task, daemon=True).start()

    def process_episode(self, url: str, mode: str, episode_info: dict = None):
        """Process episode for play/download
        
        Args:
            episode_info: Optional dict with series_title, series_year, season_num, episode_num
                          for organized folder structure
        """
        def task():
            idlix = IdlixHelper()  # New instance for episode
            idlix.cancel_flag = False  # Reset cancel flag
            self.active_helper = idlix  # Register for cancel button
            self.cancel_requested = False  # Reset cancel flag
            
            # === PREPARE: Get all metadata ===
            result = DownloadManager.prepare_episode_download(idlix, url, episode_info)
            if not result:
                return
            
            video_data, embed, m3u8 = result
            
            # === DIALOGS: Ask user for preferences ===
            resolution_id = None
            if m3u8.get("is_variant_playlist"):
                selected_id = None
                def ask():
                    nonlocal selected_id
                    selected_id = self.select_resolution_dialog(m3u8["variant_playlist"])
                self.root.after(0, ask)
                while selected_id is None:
                    time.sleep(0.1)
                
                resolution_id = selected_id
                for v in m3u8["variant_playlist"]:
                    if str(v["id"]) == resolution_id:
                        idlix.set_m3u8_url(v["uri"])
                        logger.success(f"Resolution: {v['resolution']}")
                        break
            
            subtitle_id = None
            subtitle_file = None
            subtitle_mode = 'separate'
            
            subs = idlix.get_available_subtitles()
            if subs.get("status") and subs.get("subtitles"):
                sub_holder = {"value": None, "done": False}
                def ask_sub():
                    sub_holder["value"] = self.select_subtitle_dialog(subs["subtitles"])
                    sub_holder["done"] = True
                self.root.after(0, ask_sub)
                while not sub_holder["done"]:
                    time.sleep(0.1)
                
                subtitle_id = sub_holder["value"] if sub_holder["value"] else ""  # "" = no subtitle
                
                # Ask for subtitle mode if subtitle selected
                if subtitle_id and subtitle_id != "":
                    mode_holder = {"value": None, "done": False}
                    def ask_mode():
                        mode_holder["value"] = self.select_subtitle_mode_dialog()
                        mode_holder["done"] = True
                    self.root.after(0, ask_mode)
                    while not mode_holder["done"]:
                        time.sleep(0.1)
                    subtitle_mode = mode_holder["value"]
            
            # === PLAY or DOWNLOAD ===
            if mode == "play":
                # For play: download subtitle separately for VLC
                if subtitle_id and subtitle_id != "":
                    sub_result = idlix.download_selected_subtitle(subtitle_id)
                    if sub_result.get("status"):
                        subtitle_file = sub_result.get("subtitle")
                        logger.success(f"Subtitle: {sub_result.get('label')}")
                
                if vlc:
                    logger.info("Opening VLC Player...")
                    self.root.after(0, lambda: VLCPlayerWindow(
                        self.root, idlix, idlix.m3u8_url, subtitle_file, video_data['video_name']
                    ))
                else:
                    self.start_ffplay(idlix.m3u8_url, subtitle_file)
            else:
                # === DOWNLOAD: Use unified logic ===
                def progress_update(percent, status=""):
                    self.root.after(0, lambda p=percent, s=status: self.update_progress(p, s))
                idlix.progress_callback = progress_update
                self.root.after(0, lambda: self.show_progress("Downloading episode..."))
                
                result = DownloadManager.execute_download(
                    idlix, video_data, resolution_id, subtitle_id, subtitle_mode
                )
                
                self.active_helper = None  # Clear active helper
                # Hide progress bar after download
                self.root.after(0, self.hide_progress)
        
        threading.Thread(target=task, daemon=True).start()

    def start_ffplay(self, m3u8_url, subtitle=None):
        """Start ffplay as fallback player"""
        self.stop_player()
        user_agent = self.idlix.request.headers.get("User-Agent", "Mozilla/5.0")
        headers = ""
        for k, v in self.idlix.BASE_STATIC_HEADERS.items():
            headers += f"{k}: {v}\r\n"
        cookies = self.idlix.request.cookies.get_dict()
        if cookies:
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            headers += f"Cookie: {cookie_str}\r\n"

        args = [
            "ffplay", 
            "-allowed_extensions", "ALL",
            "-allowed_segment_extensions", "ALL",
            "-extension_picky", "0",
            "-i", m3u8_url, 
            "-window_title", "IDLIX Player",
            "-user_agent", user_agent,
            "-headers", headers,
            "-hide_banner",
            "-autoexit"
        ]
        if subtitle:
            args += ["-vf", f"subtitles={subtitle}"]
        
        logger.info("Opening ffplay...")
        try:
            self.ffplay_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except FileNotFoundError:
            logger.error("FFplay not found! Please install FFMPEG.")
        except Exception as e:
            logger.error(f"Error starting player: {e}")

    def stop_player(self):
        """Stop ffplay process"""
        if self.ffplay_process and self.ffplay_process.poll() is None:
            try:
                self.ffplay_process.terminate()
                logger.info("ffplay terminated.")
            except:
                pass

    def open_download_folder(self):
        """Open downloads folder"""
        webbrowser.open(os.getcwd())

    def clear_log(self):
        """Clear log output"""
        self.log_box.configure(state="normal")
        self.log_box.delete(1.0, tk.END)
        self.log_box.configure(state="disabled")
    
    def show_progress(self, title="Downloading..."):
        """Show progress bar"""
        self.progress_label.config(text=title)
        self.progress_bar['value'] = 0
        self.progress_status.config(text="0%")
        self.cancel_btn.config(state="normal", text="❌ Cancel")
        self.progress_frame.pack(fill="x", pady=(10, 0), before=self.log_box.master)
    
    def update_progress(self, percent, status=""):
        """Update progress bar"""
        if self.progress_frame.winfo_ismapped():
            self.progress_bar['value'] = min(100, max(0, percent))
            text = f"{percent:.1f}%" if status == "" else f"{percent:.1f}% - {status}"
            self.progress_status.config(text=text)
    
    def hide_progress(self):
        """Hide progress bar"""
        self.progress_frame.pack_forget()
        # Reset cancel button state
        self.cancel_btn.config(state="normal", text="❌ Cancel")
    
    def cancel_download(self):
        """Cancel ongoing download"""
        self.cancel_requested = True
        logger.warning("⚠️ Cancelling download...")
        self.cancel_btn.config(state="disabled", text="Cancelling...")
        
        # Set cancel flag on active helper
        if self.active_helper:
            self.active_helper.cancel_flag = True
        if hasattr(self, 'idlix') and self.idlix:
            self.idlix.cancel_flag = True


if __name__ == "__main__":
    root = tk.Tk()
    app = IdlixGUI(root)
    root.mainloop()
