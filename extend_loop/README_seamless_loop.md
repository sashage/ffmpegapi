# Seamless Audio Loop Merger

Automatically detects loop points in instrumental audio and creates seamlessly extended versions.

## How It Works

1. **Analyzes** the first 25% and last 25% of your audio file
2. **Finds** the optimal overlap point using cross-correlation analysis
3. **Calculates** the exact offset in microseconds
4. **Merges** the file with itself using FFmpeg with a smooth crossfade

## Requirements

- Python 3.7+
- FFmpeg (must be installed and in PATH)
- Python packages: numpy, librosa, scipy

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Make script executable (optional)
chmod +x seamless_loop_merger.py
```

## Usage

### Basic usage:
```bash
python seamless_loop_merger.py input.mp3
```

This creates `input_looped.mp3` with the seamlessly extended audio.

### Specify output file:
```bash
python seamless_loop_merger.py input.mp3 -o output.mp3
```

### Adjust crossfade duration:
```bash
python seamless_loop_merger.py input.mp3 --crossfade 3.0
```

### Analyze only (don't merge):
```bash
python seamless_loop_merger.py input.mp3 --analyze-only
```

## Options

- `-o, --output FILE` - Specify output file path
- `-c, --crossfade SECONDS` - Crossfade duration in seconds (default: 2.0)
- `--analyze-only` - Only analyze and show the loop point without merging

## Example Output

```
Input file: music.mp3
Output file: music_looped.mp3
============================================================

Loading first 25% of audio...
Loading last 25% of audio...
Analyzing audio segments for loop point...
Best match found at offset: 234567 samples
Offset in time: 5321.25 ms
Correlation score: 0.8542

Merging audio with 2.0s crossfade...
Running FFmpeg command...
Overlap starts at: 42.679s

✓ Successfully created: music_looped.mp3
Original duration: 50.00s
New duration: 97.68s
Extended by: 47.68s (95.4%)
```

## Tips

- Works best with instrumental music that has repeating patterns
- Higher correlation scores (>0.7) indicate better loop matches
- Adjust `--crossfade` if you hear artifacts at the transition point
- Use `--analyze-only` to check if the file is suitable for looping

## Troubleshooting

**Low correlation score warning:**
- The audio might not have a clear repeating pattern
- Try a different crossfade duration
- The file might not be suitable for automatic looping

**FFmpeg not found:**
- Install FFmpeg: `sudo apt install ffmpeg` (Linux) or `brew install ffmpeg` (macOS)

**Dependencies not installed:**
- Run `pip install -r requirements.txt`
