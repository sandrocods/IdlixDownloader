import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import subprocess
import os
import time
import webbrowser
from io import BytesIO
import platform

# Check if vlc is installed
try:
    import vlc
except ImportError:
    vlc = None

from PIL import Image, ImageTk
import requests
from bs4 import BeautifulSoup

from src.idlixHelper import IdlixHelper, logger
from src.vlc_player import VLCPlayerWindow

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
        self.root.title("IDLIX Downloader & Player GUI")
        self.root.geometry("1400x650")

        self.idlix = IdlixHelper()
        self.featured_movies = []
        self.poster_images = []
        self.ffplay_process = None

        # Check VLC
        if vlc is None:
            messagebox.showwarning("VLC Missing", "python-vlc module not found. Player will fall back to ffplay.")

        # Main container
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill="both", expand=True)

        # LEFT = poster grid
        left_panel = ttk.Frame(main_frame)
        left_panel.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        
        # Header + scrollable canvas... same as before...
        # ... Recreating the layout ...
        ttk.Label(left_panel, text="Featured Movies", font=("Arial", 16, "bold")).pack(anchor="w")

        self.poster_canvas = tk.Canvas(left_panel, bg="#181818")
        scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=self.poster_canvas.yview)
        self.poster_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.poster_canvas.pack(side="left", fill="both", expand=True)
        self.poster_frame = ttk.Frame(self.poster_canvas)
        self.poster_canvas.create_window((0, 0), window=self.poster_frame, anchor="nw")
        self.poster_canvas.bind("<Configure>", lambda e: self.poster_canvas.configure(scrollregion=self.poster_canvas.bbox("all")))

        # RIGHT = controls + log
        right_panel = ttk.Frame(main_frame, padding=(10, 0))
        right_panel.grid(row=0, column=1, sticky="ns")
        right_panel.grid_propagate(False)

        ttk.Label(right_panel, text="Controls", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 10))

        ttk.Button(right_panel, text="Refresh Featured", command=self.refresh_featured).pack(fill="x", pady=4)
        ttk.Button(right_panel, text="Download by URL", command=self.download_by_url).pack(fill="x", pady=4)
        ttk.Button(right_panel, text="Play by URL", command=self.play_by_url).pack(fill="x", pady=4)
        # Stop Player btn is less relevant for VLC window, but kept for ffplay fallback
        ttk.Button(right_panel, text="Stop Player (FFplay)", command=self.stop_player).pack(fill="x", pady=4)
        ttk.Button(right_panel, text="Open Downloads Folder", command=self.open_download_folder).pack(fill="x", pady=4)
        ttk.Button(right_panel, text="Clear Log", command=self.clear_log).pack(fill="x", pady=4)

        ttk.Label(right_panel, text="Log Output", font=("Arial", 14, "bold")).pack(anchor="w", pady=(20, 5))
        self.log_box = tk.Text(right_panel, height=28, state='disabled', bg="#111", fg="#0f0")
        self.log_box.pack(fill="both", expand=True)

        logger.remove()
        logger.add(GuiLogger(self.log_box), format="{time:HH:mm:ss} | {level} | {message}")

        self.refresh_featured()

    # Reuse methods that didn't change much
    def show_poster_grid(self):
        for w in self.poster_frame.winfo_children():
            w.destroy()
        self.poster_images.clear()
        posters_per_row = 4
        size = (150, 210)
        row = col = 0
        for movie in self.featured_movies:
            try:
                img_raw = requests.get(movie["poster"], timeout=8).content
                img = Image.open(BytesIO(img_raw)).resize(size)
                tk_img = ImageTk.PhotoImage(img)
            except:
                continue
            self.poster_images.append(tk_img)
            frame = ttk.Frame(self.poster_frame)
            frame.grid(row=row, column=col, padx=10, pady=10)
            tk.Button(frame, image=tk_img, relief="flat", command=lambda m=movie: self.on_poster_click(m)).pack()
            ttk.Label(frame, text=movie["title"], wraplength=150, justify="center").pack()
            col += 1
            if col >= posters_per_row:
                col = 0
                row += 1

    def on_poster_click(self, movie):
        popup = tk.Toplevel(self.root)
        popup.title(movie["title"])
        popup.geometry("350x220")
        ttk.Label(popup, text=movie["title"], font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Button(popup, text="Play", width=20, command=lambda: [popup.destroy(), self.process_movie(movie["url"], "play")]).pack(pady=5)
        ttk.Button(popup, text="Download", width=20, command=lambda: [popup.destroy(), self.process_movie(movie["url"], "download")]).pack(pady=5)
        ttk.Button(popup, text="Cancel", width=20, command=popup.destroy).pack(pady=10)

    def ask_variant(self, choices):
        popup = tk.Toplevel(self.root)
        popup.title("Select Resolution")
        popup.geometry("300x350")
        ttk.Label(popup, text="Select Variant", font=("Arial", 12, "bold")).pack(pady=10)
        listbox = tk.Listbox(popup, width=30, height=12)
        for c in choices:
            listbox.insert(tk.END, c)
        listbox.pack()
        result = {"res": None}
        def choose():
            sel = listbox.curselection()
            if sel:
                result["res"] = listbox.get(sel[0])
            popup.destroy()
        ttk.Button(popup, text="OK", command=choose).pack(pady=10)
        popup.grab_set()
        self.root.wait_window(popup)
        return result["res"]

    def refresh_featured(self):
        def task():
            logger.info("Loading featured movies...")
            home = retry(self.idlix.get_home)
            if not home.get("status"):
                logger.error(f"Failed: {home.get('message')}")
                return
            self.featured_movies = home["featured_movie"]
            self.root.after(0, self.show_poster_grid)
            logger.success("Featured loaded.")
        threading.Thread(target=task, daemon=True).start()

    def download_by_url(self):
        url = simpledialog.askstring("Download Movie", "Enter movie URL:")
        if url:
            self.process_movie(url.strip(), "download")

    def play_by_url(self):
        url = simpledialog.askstring("Play Movie", "Enter movie URL:")
        if url:
            self.process_movie(url.strip(), "play")

    def process_movie(self, url: str, mode: str):
        def task():
            idlix = self.idlix
            video_data = retry(idlix.get_video_data, url)
            if not video_data.get("status"):
                logger.error("Error getting video data")
                return
            logger.info(f"Video ID: {video_data['video_id']} | Name: {video_data['video_name']}")
            embed = retry(idlix.get_embed_url)
            if not embed.get("status"):
                logger.error("Error getting embed URL")
                return
            logger.success(f"Embed: {embed['embed_url']}")
            m3u8 = retry(idlix.get_m3u8_url)
            if not m3u8.get("status"):
                logger.error("Error getting M3U8 URL")
                return
            logger.success(f"M3U8: {m3u8['m3u8_url']}")
            
            if m3u8.get("is_variant_playlist"):
                choices = [f"{v['id']} - {v['resolution']}" for v in m3u8["variant_playlist"]]
                selected = None
                def ask():
                    nonlocal selected
                    selected = self.ask_variant(choices)
                self.root.after(0, ask)
                while selected is None:
                    self.root.update()
                selected_id = selected.split(" - ")[0]
                for v in m3u8["variant_playlist"]:
                    if str(v["id"]) == selected_id:
                        idlix.set_m3u8_url(v["uri"])
                        logger.success(f"Variant selected: {v['resolution']}")
                        break
            else:
                logger.warning("No variant playlist.")

            if mode == "play":
                subtitle = idlix.get_subtitle()
                subtitle_file = subtitle["subtitle"] if subtitle.get("status") else None
                
                # Check VLC, if present use it, otherwise fallback
                if vlc:
                    logger.info("Opening VLC Player...")
                    self.root.after(0, lambda: VLCPlayerWindow(self.root, idlix, idlix.m3u8_url, subtitle_file, video_data['video_name']))
                else:
                    self.start_ffplay(idlix.m3u8_url, subtitle_file)
            else:
                result = idlix.download_m3u8()
                if result.get("status"):
                    logger.success(f"Downloaded: {result['path']}")
                else:
                    logger.error("Download failed.")

        threading.Thread(target=task, daemon=True).start()

    def start_ffplay(self, m3u8_url, subtitle=None):
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
        logger.info(f"Opening ffplay... Command: {' '.join(args)}")
        try:
            self.ffplay_process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Daemon to log logging disabled here to avoid complexity, relying on clean output
        except FileNotFoundError:
            logger.error("FFplay not found! Please install FFMPEG.")
        except Exception as e:
            logger.error(f"Error starting player: {e}")

    def stop_player(self):
        if self.ffplay_process and self.ffplay_process.poll() is None:
            try:
                self.ffplay_process.terminate()
                logger.info("ffplay terminated.")
            except:
                pass

    def open_download_folder(self):
        webbrowser.open(os.getcwd())

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete(1.0, tk.END)
        self.log_box.configure(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = IdlixGUI(root)
    root.mainloop()
