# IDLIX CLI Video Downloader & Video Player

![image](https://github.com/user-attachments/assets/6f1d736a-c8c8-4af2-9f32-4735dbec45c4)

IDLIX CLI Video Downloader & Video Player adalah program berbasis command-line interface (CLI) yang dirancang untuk mengunduh dan memutar video dari platform IDLIX dengan efisien. program ini memungkinkan pengguna untuk
berinteraksi langsung dengan platform IDLIX, sehingga mereka dapat mengunduh video sesuai dengan preferensi link atau featured movie. Setelah diunduh video dapat diputar dengan lancar menggunakan bantuan FFmpeg / FFplay

## Package

berikut ini adalah Package inti yang digunakan untuk membuat program dapat berjalan dengan lancar

- [curl_cffi](https://pypi.org/project/curl-cffi/)
- [requests](https://pypi.org/project/requests/)
- [m3u8-To-MP4](https://pypi.org/project/m3u8-To-MP4/)
- [beautifulsoup4](https://pypi.org/project/beautifulsoup4/)
- [pycryptodomex](https://pypi.org/project/pycryptodomex/)

## Fitur

Berikut ini adalah fitur fitur yang tersedia di program ini

| Nama                    | Deskripsi                                                          | Status |
|-------------------------|--------------------------------------------------------------------|--------|
| Download Featured Movie | Dapat melakukan download berdasarkan section featured movie        | ✔      |
| Play Featured Movie     | Dapat melakukan pemutaran video berdasarkan section featured movie | ✔      |
| Download Movie by URL   | Dapat melakukan pengunduhan video berdasarkan link                 | ✔      |
| Select Resolution       | Dapat memilih resolusi video yang diinginkan                       | ✔      |
| Subtitle                | Dapat memutar video dengan subtitle                                | ✔      |
| Play Movie by URL       | Dapat melakukan pemutaran video berdasarkan link                   | ✔      |
| Pretty Print            | Menampilkan output dengan format yang rapi                         | ✔      |
| Download Progress       | Menampilkan progress download                                      | ✔      |

## Installasi

Berikut ini adalah cara installasi program versi windows

##### 1. Lakukan git pada repository ini

```bash
  git clone https://github.com/sandrocods/IdlixDownloader
```

##### 2. Install requirements yang dibutuhkan

```bash
  pip3 install -r requirements.txt
```

## Penggunaan

Untuk menggunakan program ini, ikuti langkah-langkah berikut:

##### 1. Jalankan program

```bash
  python3 main.py
```

##### 2. Pilih menu yang tersedia

```bash
  1. Download Featured Movie
  2. Play Featured Movie
  3. Download Movie by URL
  4. Play Movie by URL
  5. Exit
```

#### ❗ Note

```
Program ini akan otomatis mendownload file ( ffmpeg-x.x.x-essentials_build ) berbasis windows yang akan digunakan untuk mendownload dan melakukan pemutaran video secara otomatis
dan akan melakukan ekstraksi file tersebut ke dalam folder src/ffmpeg, setelah itu program akan melakukan setting PATH secara otomatis
```

## Screenshots

#### 1. Tampilan awal program

![App Screenshot](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/1.jpg?raw=true)

#### 2. Download video berdasarkan featured movie

![App Screenshot](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/2.jpg?raw=true)

#### 3. Memutar video secara online

![App Screenshot](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/3.jpg?raw=true)

#### 4. Memutar video subtitle

![App Screenshot](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/4.jpg?raw=true)

#### 5. Memutar video berdasarkan resolusi

![App Screenshot](https://github.com/sandrocods/IdlixDownloader/blob/master/ss/5.jpg?raw=true)

## Roadmap

- Menambahkan type tvseries / episode

# Changelog

<details>
<summary><strong>2024-11-27</strong></summary>

### Updated

- Updated API for new server changes.

</details>

<details>
<summary><strong>2024-08-21</strong></summary>

### Added

- Added `README.md`.
- Added `requirements.txt`.
- Added project screenshots.

### Updated

- Updated resolution and subtitle handling.
- Updated helper scripts for Linux.
- Optimized various aspects of the project.
- Updated `README.md` with new details.

</details>

<details>
<summary><strong>2023-03-28</strong></summary>

### Updated

- General update with changes and improvements.

</details>

<details>
<summary><strong>2022-09-09</strong></summary>

### Added

- Added worker threads for better concurrency.

### Updated

- Cleaned code for better readability ✨.
- Improved logging functionality.

### Removed

- Deleted logging in certain areas to streamline performance.

</details>

<details>
<summary><strong>2022-09-08</strong></summary>

### Fixed

- Fixed API updates during the download process.

</details>

<details>
<summary><strong>2022-08-17</strong></summary>

### Added

- Added `ffmpeg` integration.
- Added tutorial images for better guidance.

### Fixed

- Fixed `.exe` file issues.
- Fixed issues with `ffmpeg` directory handling.

### Updated

- Updated `README.md` with more comprehensive information.
- Updated and improved overall code quality.

</details>

<details>
<summary><strong>2022-08-12</strong></summary>

### Added

- Initial project commit.
- Created the first version of `README.md`.
- Added tutorial images for initial guidance.

</details>

## Note

Program ini dibuat untuk keperluan pembelajaran semata, segala bentuk penyalahgunaan diluar tanggung jawab pembuat program ini

