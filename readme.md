# IDLIX Video Downloader & Player

CLI + GUI Version (Tkinter + VLC / FFplay)

IDLIX CLI Video Downloader & Video Player adalah program berbasis command-line interface (CLI) dan GUI yang dirancang untuk mengunduh dan memutar video dari platform IDLIX dengan efisien. Program ini memungkinkan pengguna untuk berinteraksi langsung dengan platform IDLIX, sehingga mereka dapat mengunduh video sesuai dengan preferensi link atau featured movie. Setelah diunduh video dapat diputar dengan lancar menggunakan VLC Player (utama) atau FFplay (fallback).

- Pemilihan resolusi (variant playlist)
- Subtitle otomatis (VTT → SRT)
- Downloader M3U8 multithread
- Pemutar video via VLC Player (utama) atau FFplay (fallback)
- GUI berbasis Tkinter dengan poster grid
- Unit tests untuk memastikan stabilitas

Program mendukung Windows dan Linux.

---

# Fitur Utama

| Nama                    | Deskripsi                                                   | Status |
| ----------------------- | ----------------------------------------------------------- | ------ |
| Featured Movie List     | Menampilkan daftar film unggulan                            | ✔      |
| Poster Grid GUI         | Menampilkan poster film dalam grid                          | ✔      |
| Play Featured Movie     | Memutar film dari featured                                  | ✔      |
| Download Featured Movie | Mengunduh film dari featured                                | ✔      |
| Play Movie by URL       | Memutar film berdasarkan URL                                | ✔      |
| Download Movie by URL   | Mengunduh film berdasarkan URL                              | ✔      |
| Select Resolution       | Memilih resolusi (variant playlist)                         | ✔      |
| Subtitle Support        | Download dan load subtitle otomatis                         | ✔      |
| VLC Player GUI          | Player terintegrasi dengan kontrol UI (Seek, Vol, Sub Sync) | ✔      |
| FFplay Integration      | Pemutaran video stabil (fallback)                           | ✔      |
| Stop Player Feature     | Menghentikan player                                         | ✔      |
| Download Folder Button  | Membuka folder hasil download                               | ✔      |
| Log Console GUI         | Log real-time seperti terminal                              | ✔      |

---

# Package Utama

- cloudscraper
- requests
- m3u8-To-MP4
- beautifulsoup4
- pycryptodomex
- pillow
- python-vlc
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

1. GUI akan menampilkan poster film dari homepage IDLIX.
2. Klik poster → Play atau Download.
3. Player menggunakan VLC (jendela terpisah dengan kontrol UI):
   - Shortcut keyboard:
     - `Spasi`: Play/Pause
     - `F` / `Double Click`: Fullscreen
     - `Panah Kanan/Kiri`: Seek +/- 5 detik
     - `Panah Atas/Bawah`: Volume +/- 5
     - `G` / `H`: Sinkronisasi Subtitle (-/+ 50ms)
4. Jika VLC tidak ditemukan, otomatis fallback ke ffplay.
5. Tersedia tombol:
   - Play by URL
   - Download by URL
   - Stop Player
   - Open Downloads Folder
   - Clear Log
6. Subtitle otomatis didownload dan dikonversi.

---

# Screenshots (GUI Version)

![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/gui1.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/gui2.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/gui3.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/gui4.jpg?raw=true)

---

# Fitur CLI

Menu CLI:

1. Download Featured Movie
2. Play Featured Movie
3. Download Movie by URL
4. Play Movie by URL
5. Exit

Dengan retry logic dan output tabel PrettyTable.

---

# Screenshots (CLI Version)

![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/1.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/2.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/3.jpg?raw=true)
![](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/4.jpg?raw=true)

---

---

# Auto Install FFmpeg (Windows Only)

Program akan otomatis:

1. Mengunduh ffmpeg-release-essentials.zip
2. Mengekstrak ke folder src/ffmpeg
3. Menambahkan PATH secara otomatis

---

# Roadmap

- Support TV series / episode
- Search movie (GUI)
- History (watch & download)
- Dark/Light Theme
- Download progress bar
- Fullscreen GUI player mode

---

# Changelog

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
