# IDLIX Downloader & Player - AI Coding Agent Instructions

## Project Overview

Dual-interface (CLI + GUI) video downloader and player for IDLIX streaming. Features: M3U8 multithread download, multi-subtitle support (VTT→SRT), resolution selection, VLC-based player with YouTube-style UI.

## Architecture

### Core Components

```
main.py          → CLI interface (inquirer prompts)
main_gui.py      → Tkinter GUI with Netflix-style dark theme
src/
├── download_manager.py  → Unified business logic (SINGLE SOURCE OF TRUTH)
├── idlixHelper.py       → Core engine: scraping, M3U8, subtitles, FFmpeg
├── CryptoJsAesHelper.py → AES decryption for protected URLs
└── vlc_player.py        → YouTube-style VLC player (Tkinter Toplevel)
```

- **[src/download_manager.py](../src/download_manager.py)** - Unified business logic layer. Single source of truth for prepare/execute download operations. All download flows (GUI & CLI) MUST use this.
- **[src/idlixHelper.py](../src/idlixHelper.py)** - Core engine. Handles web scraping (cloudscraper + BeautifulSoup), M3U8 playlist parsing, variant resolution selection, subtitle extraction/conversion, and FFmpeg/ffplay integration.
- **[src/CryptoJsAesHelper.py](../src/CryptoJsAesHelper.py)** - CryptoJS-compatible AES encryption/decryption for protected video URLs. Implements custom `dec()` function for IDLIX-specific obfuscation.
- **[src/vlc_player.py](../src/vlc_player.py)** - VLC-based player GUI (Tkinter Toplevel). Embeds VLC using `set_hwnd()` (Windows) or `set_xwindow()` (Linux). Features: YouTube-style controls, subtitle sync adjustment, fullscreen toggle, keyboard shortcuts.
- **[main.py](../main.py)** - CLI interface using `inquirer` for interactive prompts. Uses DownloadManager for all download operations.
- **[main_gui.py](../main_gui.py)** - Tkinter GUI with Netflix-style dark theme, poster grid, integrated log console, progress bar, and action buttons.

### Data Flow

1. **Homepage Scraping** → Featured movies/series list
2. **Video URL Parsing** → Extract video ID and metadata via `get_video_data()` or `get_episode_data()`
3. **Embed URL Extraction** → Decrypt player iframe via `get_embed_url()` (movie) or `get_embed_url_episode()` (TV)
4. **M3U8 URL Discovery** → Parse variant playlist from jeniusplay.com
5. **Variant Selection** → User chooses resolution, apply via `set_m3u8_url(uri)`
6. **Subtitle Handling** → Get available subtitles → User selection → Download selected
7. **Playback/Download** → Stream via VLC or download via `m3u8-To-MP4` with multithread

## Critical Patterns

### DownloadManager (Unified Business Logic)

**ALWAYS use `DownloadManager` for downloads** - ensures consistency between GUI and CLI:

```python
from src.download_manager import DownloadManager

# PREPARE: Get all metadata (returns tuple or None)
result = DownloadManager.prepare_movie_download(idlix_helper, url)
# or for episodes:
result = DownloadManager.prepare_episode_download(idlix_helper, url, episode_info)

if result:
    video_data, embed, m3u8 = result

    # EXECUTE: Download with options
    DownloadManager.execute_download(
        idlix_helper, video_data,
        resolution_id,    # Selected resolution ID
        subtitle_id,      # Subtitle selection (see below)
        subtitle_mode     # 'separate', 'softcode', or 'hardcode'
    )
```

**Subtitle ID Convention:**

- `subtitle_id=None` → Auto-download first available subtitle
- `subtitle_id=""` (empty string) → Explicit skip (user chose "No Subtitle")
- `subtitle_id="1"` → Download specific subtitle by ID

### Retry Logic

Built into DownloadManager's `_retry_operation()` - 3 attempts with 1s delay:

```python
# No need to wrap externally - DownloadManager handles retry internally
result = DownloadManager.prepare_movie_download(idlix_helper, url)  # Already retries
```

### Progress Callback (GUI)

```python
def progress_update(percent, status=""):
    self.root.after(0, lambda p=percent, s=status: self.update_progress(p, s))

idlix_helper.progress_callback = progress_update
```

### Cancel Flag

```python
# Set flag to cancel ongoing download
idlix_helper.cancel_flag = True

# Check in download methods
if self.cancel_flag:
    return {'status': False, 'message': 'Download cancelled by user'}
```

### URL Handling

- Base URL: `https://tv12.idlixku.com/` (hardcoded in `IdlixHelper.BASE_WEB_URL`)
- M3U8 URLs can be relative (`/stream.m3u8`) → auto-expanded to `https://jeniusplay.com/`
- Use `set_m3u8_url()` method which handles relative/absolute URL logic

### TV Series Support

Series and episodes use different URL patterns:

- Series page: `https://tv12.idlixku.com/tvseries/series-name/`
- Episode: `https://tv12.idlixku.com/episode/series-season-X-episode-Y/`

Key methods for series:

- `get_featured_series()` - Get featured series from homepage
- `get_series_info(url)` - Parse seasons and episodes from series page
- `get_episode_data(url)` - Get video metadata for an episode
- `get_embed_url_episode()` - Uses `type: "tv"` instead of `type: "movie"`

### Episode Folder Structure

```python
episode_info = {
    'series_title': 'Vikings',
    'series_year': '2020',
    'season_num': 1,
    'episode_num': 5
}
idlix_helper.set_episode_meta(**episode_info)
# Output: Vikings (2020)/Season 01/Vikings - s01e05.mp4
```

### Multi-Subtitle Support

Subtitles can have multiple languages. Format: `[Indonesian]url,[English]url`

- `get_available_subtitles()` - Returns list of available subtitles with labels
- `download_selected_subtitle(id)` - Download specific subtitle by ID
- User selects subtitle before play/download

### Subtitle Modes

- `'separate'` → Fast, creates `.srt` file alongside video
- `'softcode'` → Fast, embeds as MKV subtitle track (copy, no re-encode)
- `'hardcode'` → Slow, burns into video via FFmpeg re-encode

### FFmpeg Auto-Download (Windows)

On Windows, if `ffplay.exe` not in PATH:

1. Checks local `src/ffmpeg/` directory
2. Downloads `ffmpeg-release-essentials.zip` from gyan.dev
3. Extracts and adds to PATH dynamically
4. Linux requires pre-installed FFmpeg (exits if missing)

### File Naming Convention

Video titles sanitized via `get_safe_title()`: removes `:&<>"/\|?*` (spaces kept)

## Developer Workflows

### Running Tests

```bash
python run_tests.py                              # All tests with colored summary
python -m unittest discover tests                # Standard unittest
python -m unittest tests.test_download_manager -v  # Specific module
```

### Test Coverage (56 tests)

| File                        | Tests | Coverage                                |
| --------------------------- | ----- | --------------------------------------- |
| `test_download_manager.py`  | 16    | Business logic, auto-subtitle, retry    |
| `test_progress_callback.py` | 16    | Progress system, cancel, subtitle modes |
| `test_idlix_helper.py`      | 14    | Core parsing, URL handling              |
| `test_vlc_player.py`        | 7     | Player initialization, controls         |
| `test_crypto.py`            | 3     | AES encryption/decryption               |

### CLI Usage

```bash
python main.py
```

Interactive menu: Movies → TV Series → Play/Download by URL

### GUI Usage

```bash
python main_gui.py
```

Poster grid loads automatically. Click poster → dialog for play/download.

### VLC Requirement

GUI player **requires VLC installed**. Falls back to ffplay if `python-vlc` import fails or VLC not found.

## External Dependencies

### Must-Have

- **cloudscraper** - Bypasses Cloudflare protection (crucial for IDLIX access)
- **python-vlc** - VLC bindings (player GUI, optional - fallback to ffplay)
- **m3u8-To-MP4** - Multithread M3U8 downloader
- **vtt-to-srt** - Subtitle conversion

### System Requirements

- Windows: Auto-downloads FFmpeg if missing
- Linux: Requires `ffmpeg` package pre-installed

## Project-Specific Conventions

### Logger Usage

Uses `loguru` throughout. Levels:

- `logger.info()` - Progress steps
- `logger.success()` - Successful operations
- `logger.warning()` - Non-critical issues (variant playlist, fallback player)
- `logger.error()` - Operation failures

### GUI Logger Integration

`main_gui.py` redirects logger to Tkinter Text widget via custom `GuiLogger` class.

### New Instance Pattern (GUI)

**Important:** GUI creates new `IdlixHelper()` per download to avoid state contamination:

```python
def process_movie(self, url: str, mode: str):
    def task():
        idlix = IdlixHelper()  # NEW instance, not self.idlix
        idlix.cancel_flag = False
        # ... rest of processing
```

### Version History

- **v1/** - Legacy CLI-only implementation (see [v1/README.md](../v1/README.md))
- **Root** - Current GUI + CLI version with VLC player integration

## Common Gotchas

1. **New Instance per Download** - GUI uses new `IdlixHelper()` per download, not shared instance
2. **TV Series Filtering** - Homepage scraper has separate methods: `get_home()` (movies), `get_featured_series()` (series)
3. **Variant Playlist Selection** - Check `m3u8.get("is_variant_playlist")` before prompting user
4. **VLC Window Embedding** - Platform-specific: `set_hwnd()` (Windows) vs `set_xwindow()` (Linux)
5. **Thread Safety** - Player thread set as daemon (`th.daemon = True`) to avoid blocking main process
6. **Cloudscraper Headers** - Always include `Referer` header (`BASE_STATIC_HEADERS`)
7. **Subtitle Mode for Batch** - Preset `subtitle_mode` once, apply to all episodes in batch download

## Key Files for Context

| File                                                                | Lines | Purpose                                 |
| ------------------------------------------------------------------- | ----- | --------------------------------------- |
| [src/download_manager.py](../src/download_manager.py)               | ~170  | Unified business logic (MOST IMPORTANT) |
| [src/idlixHelper.py](../src/idlixHelper.py)                         | ~880  | Core scraping/download engine           |
| [src/vlc_player.py](../src/vlc_player.py)                           | ~540  | YouTube-style VLC player                |
| [main_gui.py](../main_gui.py)                                       | ~1300 | Tkinter GUI                             |
| [main.py](../main.py)                                               | ~430  | CLI interface                           |
| [tests/test_download_manager.py](../tests/test_download_manager.py) | ~350  | Business logic tests                    |
