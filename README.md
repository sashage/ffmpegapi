# FFmpeg API

A simple REST API for executing FFmpeg commands remotely. No more asking your users to install FFmpeg locally.

## Why This Exists

When building CLI tools that require FFmpeg, the biggest friction point is installation. Users don't want to deal with installing FFmpeg and its dependencies. This API removes that friction entirely—just send your media file and FFmpeg command, get the processed result back.

## How It Works


**Requirements:**
- [FFmpeg must be installed](#installing-ffmpeg) on the server running this API


## Usage Examples

### Example 1: Get the processed file directly

Convert a video to H.264 with audio normalization and scale to 720p:

```python
import requests

# Upload the video file and get the processed result back directly
with open("input_video.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/run",
        files={"file": f},
        data={
            "cmd": "ffmpeg -i <input> -c:v libx264 -preset medium -crf 23 -vf scale=-2:720 -c:a aac -b:a 128k -af loudnorm output.mp4",
            "return_file": "true"
        }
    )

# Save the processed file locally
with open("output.mp4", "wb") as f:
    f.write(response.content)

print("File saved as output.mp4")
```

**Response:** Binary file content that gets saved directly.

### Example 2: Get JSON response with file URL

Extract audio from a video and convert to MP3:

```python
import requests

# Upload the video file and get a URL to download the result
with open("input_video.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/run",
        files={"file": f},
        data={
            "cmd": "ffmpeg -i <input> -vn -c:a libmp3lame -q:a 2 output.mp3"
        }
    )

result = response.json()
print(f"Download your file from: {result['output_url']}")
```

**Response:**
```json
{
  "cmd": "ffmpeg -i /uploads/xyz/input.mp4 -vn -c:a libmp3lame -q:a 2 /outputs/xyz/output.mp3",
  "stdout": "",
  "stderr": "ffmpeg version 4.4.2...",
  "returncode": 0,
  "output_url": "http://localhost:8000/static/xyz/output.mp3"
}
```

### Example 3: Extract a thumbnail with filters

Extract a thumbnail at 5 seconds, scale it, and apply sharpening:

```python
import requests

# Upload the video and extract a thumbnail
with open("video.mp4", "rb") as f:
    response = requests.post(
        "http://localhost:8000/run",
        files={"file": f},
        data={
            "cmd": "ffmpeg -i <input> -ss 00:00:05 -vframes 1 -vf scale=1280:-2,unsharp=5:5:1.0:5:5:0.0 thumbnail.jpg"
        }
    )

result = response.json()
print(f"Thumbnail URL: {result['output_url']}")
print(f"Status: {'Success' if result['returncode'] == 0 else 'Failed'}")
```

**Response:**
```json
{
  "cmd": "ffmpeg -i /uploads/abc/video.mp4 -ss 00:00:05 -vframes 1 -vf scale=1280:-2,unsharp=5:5:1.0:5:5:0.0 /outputs/abc/thumbnail.jpg",
  "stdout": "",
  "stderr": "ffmpeg version 4.4.2...",
  "returncode": 0,
  "output_url": "http://localhost:8000/static/abc/thumbnail.jpg"
}
```

### Example 4: Extend Audio Loop (New!)

Automatically analyze and extend looping audio files:

```python
import requests

# Upload audio file and get extended version
with open("music_loop.mp3", "rb") as f:
    response = requests.post(
        "http://localhost:8000/extendloop",
        files={"input_file": f}
    )

# Save the result (extended or original if not loopable)
with open("output.mp3", "wb") as f:
    f.write(response.content)

# Check headers for metadata
print(f"Extended: {response.headers['X-Extended']}")
print(f"Correlation: {response.headers['X-Correlation-Score']}")
print(f"Original: {response.headers['X-Original-Duration']}s")
print(f"New: {response.headers['X-New-Duration']}s")
```

**How it works:**
1. Analyzes first/last 25% of audio using cross-correlation
2. If correlation ≥ threshold: extends with smooth crossfade
3. If correlation < threshold: returns original unchanged

**Best for:** Instrumental music, game loops, ambient soundscapes

**Parameters:**
- `input_file` (required): Audio file (MP3, WAV, etc.)
- `crossfade` (optional, default: 2.0): Crossfade duration in seconds
- `threshold` (optional, default: 0.5): Min correlation score (0-1)


## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed on your system (see [Installing FFmpeg](#installing-ffmpeg) below)
- [uv](https://github.com/astral-sh/uv) package manager (recommended) or pip

### Installing FFmpeg

FFmpeg must be installed on the server where you run this API.

#### Linux

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Fedora:**
```bash
sudo dnf install ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S ffmpeg
```

#### macOS

Using Homebrew:
```bash
brew install ffmpeg
```

#### Windows

1. **Using Chocolatey** (recommended):
   ```bash
   choco install ffmpeg
   ```

2. **Manual Installation:**
   - Download from [ffmpeg.org](https://ffmpeg.org/download.html#build-windows)
   - Extract the archive
   - Add the `bin` folder to your system PATH

**Verify installation:**
```bash
ffmpeg -version
```

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kevinnadar22/ffmpegapi.git
   cd ffmpegapi
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

   Or with pip:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the API:**
   ```bash
   python run.py
   ```

   The API will start on `http://localhost:8000`

4. **Test the installation:**
   ```bash
   pytest tests/
   ```

### Docker Setup

```bash
docker-compose up
```

The API will be available at `http://localhost:8000`

## Development & Contributing

### Running Tests

Run the test suite to ensure everything works:

```bash
pytest tests/
```

For verbose output:
```bash
pytest tests/ -v
```

### Code Quality

This project uses pre-commit hooks to maintain code quality. If you're contributing:

1. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

2. **The hooks will automatically run** before each commit to check:
   - Code formatting
   - Linting
   - Type checking
   - Other quality checks

3. **Run hooks manually** (optional):
   ```bash
   pre-commit run --all-files
   ```

**All contributions must pass pre-commit checks before being merged.**

## API Reference

For complete interactive API documentation, visit `http://localhost:8000/docs` when the server is running.

---

## Author

**Kevin Nadar**

🌐 Website: [mariakevin.in](https://mariakevin.in)
💻 GitHub: [@kevinnadar22](https://github.com/kevinnadar22)

---

**No more FFmpeg installation headaches for your users. Just upload, process, and download.**
