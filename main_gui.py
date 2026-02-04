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
        self.refresh_content()

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
            
            for ep in season["episodes"]:
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
                
                play_btn = ModernButton(ep_frame, "▶️", 
                    lambda e=ep: [popup.destroy(), self.process_episode(e["url"], "play")],
                    style="primary")
                play_btn.pack(side="right", padx=2)
                
                dl_btn = ModernButton(ep_frame, "📥", 
                    lambda e=ep: [popup.destroy(), self.process_episode(e["url"], "download")],
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

    def process_movie(self, url: str, mode: str):
        """Process movie for play/download"""
        def task():
            idlix = self.idlix
            
            # Get video data
            video_data = retry(idlix.get_video_data, url)
            if not video_data.get("status"):
                logger.error("Error getting video data")
                return
            logger.info(f"📽️ {video_data['video_name']}")
            
            # Get embed URL
            embed = retry(idlix.get_embed_url)
            if not embed.get("status"):
                logger.error("Error getting embed URL")
                return
            logger.success("Embed URL obtained")
            
            # Get M3U8 URL
            m3u8 = retry(idlix.get_m3u8_url)
            if not m3u8.get("status"):
                logger.error("Error getting M3U8 URL")
                return
            logger.success("M3U8 URL obtained")
            
            # Select resolution
            if m3u8.get("is_variant_playlist"):
                selected_id = None
                def ask():
                    nonlocal selected_id
                    selected_id = self.select_resolution_dialog(m3u8["variant_playlist"])
                self.root.after(0, ask)
                while selected_id is None:
                    time.sleep(0.1)
                
                for v in m3u8["variant_playlist"]:
                    if str(v["id"]) == selected_id:
                        idlix.set_m3u8_url(v["uri"])
                        logger.success(f"Resolution: {v['resolution']}")
                        break
            
            # Select subtitle
            subtitle_file = None
            subs = idlix.get_available_subtitles()
            if subs.get("status") and subs.get("subtitles"):
                subtitle_id = None
                def ask_sub():
                    nonlocal subtitle_id
                    subtitle_id = self.select_subtitle_dialog(subs["subtitles"])
                self.root.after(0, ask_sub)
                while subtitle_id is None:
                    time.sleep(0.1)
                
                if subtitle_id:
                    sub_result = idlix.download_selected_subtitle(subtitle_id)
                    if sub_result.get("status"):
                        subtitle_file = sub_result.get("subtitle")
                        logger.success(f"Subtitle: {sub_result.get('label')}")
            
            # Play or download
            if mode == "play":
                if vlc:
                    logger.info("Opening VLC Player...")
                    self.root.after(0, lambda: VLCPlayerWindow(
                        self.root, idlix, idlix.m3u8_url, subtitle_file, video_data['video_name']
                    ))
                else:
                    self.start_ffplay(idlix.m3u8_url, subtitle_file)
            else:
                logger.info("Starting download...")
                result = idlix.download_m3u8()
                if result.get("status"):
                    logger.success(f"✅ Downloaded: {video_data['video_name']}")
                else:
                    logger.error(f"Download failed: {result.get('message')}")
        
        threading.Thread(target=task, daemon=True).start()

    def process_episode(self, url: str, mode: str):
        """Process episode for play/download"""
        def task():
            idlix = IdlixHelper()  # New instance for episode
            
            # Get episode data
            video_data = retry(idlix.get_episode_data, url)
            if not video_data.get("status"):
                logger.error("Error getting episode data")
                return
            logger.info(f"📺 {video_data['video_name']}")
            
            # Get embed URL (episode uses type=tv)
            embed = retry(idlix.get_embed_url_episode)
            if not embed.get("status"):
                logger.error("Error getting embed URL")
                return
            logger.success("Embed URL obtained")
            
            # Get M3U8 URL
            m3u8 = retry(idlix.get_m3u8_url)
            if not m3u8.get("status"):
                logger.error("Error getting M3U8 URL")
                return
            logger.success("M3U8 URL obtained")
            
            # Select resolution
            if m3u8.get("is_variant_playlist"):
                selected_id = None
                def ask():
                    nonlocal selected_id
                    selected_id = self.select_resolution_dialog(m3u8["variant_playlist"])
                self.root.after(0, ask)
                while selected_id is None:
                    time.sleep(0.1)
                
                for v in m3u8["variant_playlist"]:
                    if str(v["id"]) == selected_id:
                        idlix.set_m3u8_url(v["uri"])
                        logger.success(f"Resolution: {v['resolution']}")
                        break
            
            # Select subtitle
            subtitle_file = None
            subs = idlix.get_available_subtitles()
            if subs.get("status") and subs.get("subtitles"):
                subtitle_id = None
                def ask_sub():
                    nonlocal subtitle_id
                    subtitle_id = self.select_subtitle_dialog(subs["subtitles"])
                self.root.after(0, ask_sub)
                while subtitle_id is None:
                    time.sleep(0.1)
                
                if subtitle_id:
                    sub_result = idlix.download_selected_subtitle(subtitle_id)
                    if sub_result.get("status"):
                        subtitle_file = sub_result.get("subtitle")
                        logger.success(f"Subtitle: {sub_result.get('label')}")
            
            # Play or download
            if mode == "play":
                if vlc:
                    logger.info("Opening VLC Player...")
                    self.root.after(0, lambda: VLCPlayerWindow(
                        self.root, idlix, idlix.m3u8_url, subtitle_file, video_data['video_name']
                    ))
                else:
                    self.start_ffplay(idlix.m3u8_url, subtitle_file)
            else:
                logger.info("Starting download...")
                result = idlix.download_m3u8()
                if result.get("status"):
                    logger.success(f"✅ Downloaded: {video_data['video_name']}")
                else:
                    logger.error(f"Download failed: {result.get('message')}")
        
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


if __name__ == "__main__":
    root = tk.Tk()
    app = IdlixGUI(root)
    root.mainloop()
