# IDLIX Downloader & Player - AI Coding Agent Instructions

## Project Overview

Dual-interface (CLI + GUI) video downloader and player for the IDLIX streaming platform. Features include M3U8 video streaming/downloading with multithread support, automatic subtitle extraction (VTT→SRT), resolution selection, and integrated VLC-based video playback with custom controls.

## Architecture

### Core Components

- **[src/idlixHelper.py](../src/idlixHelper.py)** - Main business logic class. Handles web scraping (cloudscraper + BeautifulSoup), M3U8 playlist parsing, variant resolution selection, subtitle extraction/conversion, and FFmpeg/ffplay integration. Uses retry logic (3 attempts) for all network operations.
- **[src/CryptoJsAesHelper.py](../src/CryptoJsAesHelper.py)** - CryptoJS-compatible AES encryption/decryption for protected video URLs. Implements custom `dec()` function for IDLIX-specific obfuscation.
- **[src/vlc_player.py](../src/vlc_player.py)** - VLC-based player GUI (Tkinter Toplevel). Embeds VLC using `set_hwnd()` (Windows) or `set_xwindow()` (Linux). Features: custom controls, subtitle sync adjustment, fullscreen toggle, keyboard shortcuts.
- **[main.py](../main.py)** - CLI interface using `inquirer` for interactive prompts. Implements threaded playback to avoid blocking.
- **[main_gui.py](../main_gui.py)** - Tkinter GUI with poster grid, integrated log console, and action buttons.

### Data Flow

1. **Homepage Scraping** → Featured movies list (filters out TV series)
2. **Video URL Parsing** → Extract video ID and metadata
3. **Embed URL Extraction** → Fetch player iframe source
4. **M3U8 URL Discovery** → Parse encrypted/obfuscated playlist URLs
5. **Variant Selection** → User chooses resolution from variant playlist
6. **Subtitle Download** → Extract VTT subtitles, convert to SRT using `vtt-to-srt`
7. **Playback/Download** → Stream via VLC or download via `m3u8-To-MP4` with multithread

## Critical Patterns

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

### Multi-Subtitle Support

Subtitles can have multiple languages. Format: `[Indonesian]url,[English]url`

- `get_available_subtitles()` - Returns list of available subtitles with labels
- `download_selected_subtitle(id)` - Download specific subtitle by ID
- User selects subtitle before play/download

### Retry Logic

All network operations use `retry()` wrapper (3 attempts, 1s delay):

```python
result = retry(idlix_helper.get_video_data, url)
if not result.get("status"):
    logger.error("Error getting video data")
    return
```

### FFmpeg Auto-Download (Windows)

On Windows, if `ffplay.exe` not in PATH:

1. Checks local `src/ffmpeg/` directory
2. Downloads `ffmpeg-release-essentials.zip` from gyan.dev
3. Extracts and adds to PATH dynamically
4. Linux requires pre-installed FFmpeg (exits if missing)

### File Naming Convention

Video titles sanitized via `get_safe_title()`: removes `:&<>"/\|?*`, replaces spaces with `_`

### Subtitle Handling

- Downloads VTT from embed page
- Auto-converts to SRT using `vtt_to_srt.ConvertFile`
- Loads into VLC player automatically
- Keyboard shortcuts: `G`/`H` adjust sync by ±50ms

## Developer Workflows

### Running Tests

```bash
python -m unittest discover tests
```

Tests use mocks extensively - see [tests/test_idlix_helper.py](../tests/test_idlix_helper.py) for patterns.

### CLI Usage

```bash
python main.py
```

Interactive menu: select featured movie or paste URL → play/download → choose resolution

### GUI Usage

```bash
python main_gui.py
```

Poster grid loads automatically. Click poster → dialog for play/download.

### VLC Requirement

GUI player **requires VLC installed**. Falls back to ffplay if `python-vlc` import fails or VLC not found. Check:

```python
if vlc is None:
    messagebox.showwarning("VLC Missing", "...")
```

## External Dependencies

### Must-Have

- **cloudscraper** - Bypasses Cloudflare protection (crucial for IDLIX access)
- **python-vlc** - VLC bindings (player GUI)
- **m3u8-To-MP4** - Multithread M3U8 downloader
- **vtt-to-srt** - Subtitle conversion

### System Requirements

- Windows: Auto-downloads FFmpeg
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

### Version History

- **v1/** - Legacy CLI-only implementation (see [v1/README.md](../v1/README.md))
- **Root** - Current GUI + CLI version with VLC player integration

## Common Gotchas

1. **TV Series Filtering** - Homepage scraper explicitly excludes `/tvseries/` URLs (only movies supported currently)
2. **Variant Playlist Selection** - Check `m3u8.get("is_variant_playlist")` before prompting user
3. **VLC Window Embedding** - Platform-specific: `set_hwnd()` (Windows) vs `set_xwindow()` (Linux)
4. **Thread Safety** - Player thread set as daemon (`th.daemon = True`) to avoid blocking main process
5. **Cloudscraper Headers** - Always include `Referer` header (`BASE_STATIC_HEADERS`)

## Key Files for Context

- Architecture: [src/idlixHelper.py](../src/idlixHelper.py) (511 lines)
- Player implementation: [src/vlc_player.py](../src/vlc_player.py) (268 lines)
- GUI patterns: [main_gui.py](../main_gui.py) (306 lines)
- Test patterns: [tests/test_idlix_helper.py](../tests/test_idlix_helper.py)
