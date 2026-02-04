# IDLIX Video Downloader & Player

CLI + GUI Version (Tkinter + VLC / FFplay)

IDLIX Video Downloader & Player adalah program berbasis CLI dan GUI yang dirancang untuk mengunduh dan memutar video dari platform IDLIX. Program ini mendukung **Movies** dan **TV Series** dengan fitur lengkap termasuk pemilihan episode, multi-subtitle, dan player modern bergaya YouTube.

## ✨ Highlights

- 🎬 **Movies & TV Series** - Browse dan putar film atau serial TV
- 📺 **Episode Browser** - Pilih season dan episode dengan mudah
- 🗣️ **Multi-Subtitle** - Pilih bahasa subtitle yang tersedia
- 🎨 **Modern Dark UI** - Tampilan Netflix-style dengan tema gelap
- ▶️ **YouTube-style Player** - Loading animation, progress bar, auto-hide controls
- 📥 **Multithread Download** - Download cepat dengan M3U8-To-MP4
- 🔄 **Auto Retry** - Logic retry 3x untuk koneksi stabil

Program mendukung Windows dan Linux.

---

# Fitur Utama

| Nama                     | Deskripsi                                               | Status |
| ------------------------ | ------------------------------------------------------- | ------ |
| Featured Movies          | Menampilkan daftar film unggulan                        | ✔      |
| Featured TV Series       | Menampilkan daftar serial TV unggulan                   | ✔      |
| Episode Browser          | Browse season dan episode untuk serial TV               | ✔      |
| Poster Grid GUI          | Menampilkan poster dalam grid dengan dark theme         | ✔      |
| Play/Download Movie      | Memutar atau unduh film                                 | ✔      |
| Play/Download Episode    | Memutar atau unduh episode serial                       | ✔      |
| Play by URL              | Memutar berdasarkan URL (movie/series/episode)          | ✔      |
| Download by URL          | Mengunduh berdasarkan URL                               | ✔      |
| Select Resolution        | Memilih resolusi (variant playlist)                     | ✔      |
| Multi-Subtitle Support   | Pilih dari beberapa bahasa subtitle yang tersedia       | ✔      |
| YouTube-style VLC Player | Player modern dengan loading animation dan progress bar | ✔      |
| Auto-hide Controls       | Controls tersembunyi otomatis saat fullscreen           | ✔      |
| FFplay Fallback          | Fallback ke FFplay jika VLC tidak tersedia              | ✔      |
| Download Folder Button   | Membuka folder hasil download                           | ✔      |
| Log Console GUI          | Log real-time dengan warna                              | ✔      |
| Batch Download           | Download semua episode dalam satu season                | ✔      |
| Subtitle Mode Options    | Separate (.srt), Softcode (MKV), Hardcode (burn-in)     | ✔      |
| Organized Folder         | Series download ke folder terorganisir                  | ✔      |
| Plex Compatible          | Subtitle metadata dengan language code                  | ✔      |

---

# Package Utama

- cloudscraper
- requests
- m3u8-To-MP4
- beautifulsoup4
- pycryptodomex
- pillow
- python-vlc
- loguru
- inquirer
- prettytable
- vtt-to-srt
- FFmpeg / FFplay

---

# 🔽 Download (Rekomendasi)

Untuk pengguna Windows **tidak perlu Python**.  
Cukup download file `.exe` di halaman Release:

👉 https://github.com/sandrocods/IdlixDownloader/releases/latest

# 🔧 Instalasi dari Source (Opsional)

Prasyarat:

- Python 3.x
- VLC Media Player (wajib terinstall untuk fitur player GUI)
- FFmpeg (untuk fitur download dan fallback player)

1. Clone repository:
   git clone https://github.com/sandrocods/IdlixDownloader
   cd IdlixDownloader

2. Install requirements:
   pip install -r requirements.txt

3. Jalankan GUI:
   python main_gui.py

4. Jalankan CLI:
   python main.py

5. Jalankan Unit Tests:
   python -m unittest discover tests

---

# Cara Penggunaan (GUI)

1. Jalankan `python main_gui.py`
2. GUI menampilkan tab **Movies** dan **TV Series**
3. Klik poster untuk melihat opsi:
   - **Movie**: Play atau Download
   - **Series**: Browse Episodes → Pilih Season → Pilih Episode
4. Pilih resolusi dari dialog yang muncul
5. Pilih subtitle (jika tersedia multiple bahasa)
6. Player VLC akan terbuka dengan kontrol modern:

### Keyboard Shortcuts (VLC Player)

| Shortcut           | Fungsi                 |
| ------------------ | ---------------------- |
| `Spasi`            | Play/Pause             |
| `F` / Double Click | Toggle Fullscreen      |
| `←` / `→`          | Seek -/+ 10 detik      |
| `↑` / `↓`          | Volume +/- 5           |
| `G` / `H`          | Subtitle Sync -/+ 50ms |
| `M`                | Mute/Unmute            |
| `Esc`              | Exit Fullscreen        |

### Fitur Player

- **Loading Animation** - Spinner animasi saat buffering
- **Progress Bar** - Klik untuk seek ke posisi tertentu
- **Auto-hide Controls** - Controls tersembunyi saat fullscreen (muncul saat mouse bergerak)
- **Time Display** - Menampilkan waktu saat ini dan durasi total
- **Volume Slider** - Kontrol volume dengan slider

7. Tombol tersedia di header:
   - 🔄 Refresh - Muat ulang daftar
   - 📂 Downloads - Buka folder download
   - 🔗 URL - Play/Download dari URL langsung

---

# Screenshots (GUI Version)

![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/gui1.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/gui2.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/gui3.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/gui4.jpg?raw=true)

---

# Fitur CLI

Menu CLI interaktif dengan `inquirer`:

1. 🎬 Movies
   - Browse Featured Movies
   - Play atau Download
2. 📺 TV Series
   - Browse Featured Series
   - Pilih Season → Pilih Episode
   - Download All Episodes (batch download)
3. 🔗 Play/Download by URL
   - Support URL movie, series, atau episode
4. ❌ Exit

Dengan retry logic 3x dan output tabel PrettyTable.

---

# Screenshots (CLI Version)

![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/1.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/2.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/3.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/4.jpg?raw=true)

---

---

# 📁 Struktur Folder Download

### Movies

File movie disimpan di folder kerja saat ini:

```
Movie Title.mp4
Movie Title.srt  (jika pilih Separate)
```

### TV Series (Organized)

Series otomatis terorganisir dalam folder:

```
Series Name (Year)/
├── Season 01/
│   ├── Series Name - s01e01.mkv
│   ├── Series Name - s01e02.mkv
│   └── ...
└── Season 02/
    └── ...
```

### Subtitle Mode Options

| Mode         | Output          | Kecepatan | Keterangan                               |
| ------------ | --------------- | --------- | ---------------------------------------- |
| **Separate** | `.mp4` + `.srt` | ⚡ Cepat  | File subtitle terpisah                   |
| **Softcode** | `.mkv`          | ⚡ Cepat  | Subtitle track di dalam MKV, bisa on/off |
| **Hardcode** | `.mp4`          | 🐢 Lambat | Subtitle burn-in permanen, re-encode     |

> 💡 **Untuk Plex**: Pilih **Softcode** agar subtitle terdeteksi otomatis dan bisa di-toggle on/off.

---

# Auto Install FFmpeg (Windows Only)

Program akan otomatis:

1. Mengunduh ffmpeg-release-essentials.zip
2. Mengekstrak ke folder src/ffmpeg
3. Menambahkan PATH secara otomatis

---

# Roadmap

- [x] ~~Support TV series / episode~~ ✅
- [x] ~~Multi-subtitle selection~~ ✅
- [x] ~~Modern dark theme UI~~ ✅
- [x] ~~YouTube-style player~~ ✅
- [ ] Search movie (GUI)
- [ ] History (watch & download)
- [ ] Download progress bar
- [ ] Watchlist / Favorites

---

# Changelog

## 2026-02-04 — TV Series, Subtitle Modes & Organized Download

Added:

- **TV Series Support** - Browse featured series, seasons, dan episodes
- **Episode Browser** - Dialog untuk pilih season dan episode
- **Multi-Subtitle Selection** - Pilih dari beberapa bahasa subtitle
- **Subtitle Mode Options** - Separate (.srt), Softcode (embed MKV), Hardcode (burn-in)
- **Organized Folder Structure** - Series download ke `Series (Year)/Season XX/`
- **Batch Episode Download** - Download semua episode dalam season (CLI + GUI)
- **Plex Compatible** - Subtitle dengan metadata language code (ISO 639-2)
- **Modern Dark Theme** - Netflix-style UI dengan warna gelap
- **YouTube-style VLC Player** - Loading spinner, modern controls
- **Auto-hide Controls** - Controls tersembunyi di fullscreen, muncul saat mouse bergerak
- **Bigger Progress Bar** - Lebih mudah diklik untuk seeking

Updated:

- GUI sepenuhnya didesain ulang dengan tema gelap
- Tab Movies/Series untuk navigasi mudah
- Dialog resolution dan subtitle dengan style modern
- VLC Player dengan animasi loading dan buffering indicator
- FFmpeg dengan `-allowed_segment_extensions ALL` untuk HLS obfuscation
- VTT to SRT dengan X-TIMESTAMP-MAP offset handling
- Fixed error "invalid command name" saat close player
- Semua after callbacks di-cancel dengan benar saat window ditutup

---

## 2025-12-31

Added:

- VLC Player Integration (GUI)
- Unit Tests (Crypto, Helper, Player)
- Keyboard shortcuts untuk player (Seek, Volume, Subtitle Sync)

Updated:

- Refactored IdlixHelper & CryptoJsAesHelper
- Player sekarang menggunakan VLC sebagai utama, ffplay sebagai fallback
- Dokumentasi lengkap untuk fitur baru

---

## 2025-11-28 — BIG UPDATE

Added:

- GUI lengkap Tkinter
- Poster grid scrollable
- Play & Download by URL
- Popup menu per movie
- Stop player
- Open folder
- Clear log
- Log GUI
- Retry logic 3x
- Perbaikan helper
- Subtitle & m3u8 handling lebih robust

Updated:

- Struktur process movie
- UI lebih intuitif
- Logger lebih clean

---

## 2024-11-27

Updated API untuk server baru

---

## 2024-08-21

Added:

- README.md
- requirements.txt
- Screenshots

Updated:

- Subtitle & resolusi
- Helper Linux
- Optimasi project

---

## 2023-03-28

General improvements

---

## 2022-09-09

Added worker threads  
Updated logging  
Cleaned code  
Removed redundant logs

---

## 2022-09-08

Fixed API update issues

---

## 2022-08-17

Added ffmpeg integration  
Fixed exe issues  
Added tutorial images

---

## 2022-08-12 — Initial Commit

---

# Disclaimer

Program ini dibuat untuk pembelajaran.  
Segala penyalahgunaan di luar tanggung jawab pembuat.
