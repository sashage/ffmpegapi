#!/usr/bin/env python3
"""
Seamless Audio Loop Merger
Analyzes an audio file to find the optimal loop point between the first 25% and last 25%,
then creates a seamlessly merged version with extended playtime.
"""

import numpy as np
import librosa
import subprocess
import sys
import argparse
from pathlib import Path
from scipy import signal


def load_audio_segment(file_path, start_percent=0, end_percent=100):
    """Load a segment of an audio file."""
    # Load full audio to get duration
    y, sr = librosa.load(file_path, sr=None, mono=True)

    total_samples = len(y)
    start_sample = int(total_samples * start_percent / 100)
    end_sample = int(total_samples * end_percent / 100)

    segment = y[start_sample:end_sample]

    return segment, sr, total_samples


def find_best_loop_point(first_segment, last_segment, sr, search_resolution=0.01):
    """
    Find the best loop point using cross-correlation.

    Args:
        first_segment: Audio data from the first 25%
        last_segment: Audio data from the last 25%
        sr: Sample rate
        search_resolution: Resolution in seconds for search (default 0.01s = 10ms)

    Returns:
        offset_samples: Offset in samples
        offset_microseconds: Offset in microseconds
        correlation_score: Correlation coefficient (0-1)
    """
    print("Analyzing audio segments for loop point...")

    # Use cross-correlation to find where first_segment best matches within last_segment
    # We'll compare the beginning of first_segment with sliding windows in last_segment

    # Use a reasonable window size (e.g., 5 seconds or length of shorter segment)
    window_duration = min(5.0, len(first_segment) / sr, len(last_segment) / sr)
    window_samples = int(window_duration * sr)

    search_segment = first_segment[:window_samples]

    # Normalize for better correlation
    search_segment = (search_segment - np.mean(search_segment)) / (np.std(search_segment) + 1e-10)

    # Correlate with last segment
    correlation = signal.correlate(last_segment, search_segment, mode='valid')

    # Normalize the correlation
    # Calculate the standard deviation of the sliding windows
    last_segment_normalized = (last_segment - np.mean(last_segment)) / (np.std(last_segment) + 1e-10)

    # Find the peak correlation
    best_offset = np.argmax(correlation)
    max_correlation = correlation[best_offset]

    # Normalize correlation score
    correlation_score = max_correlation / (len(search_segment))

    # Convert to microseconds
    offset_microseconds = int((best_offset / sr) * 1_000_000)

    print(f"Best match found at offset: {best_offset} samples")
    print(f"Offset in time: {offset_microseconds / 1000:.2f} ms")
    print(f"Correlation score: {correlation_score:.4f}")

    return best_offset, offset_microseconds, correlation_score


def get_audio_duration(file_path):
    """Get audio duration in seconds using ffprobe."""
    cmd = [
        'ffprobe',
        '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def merge_with_crossfade(input_file, offset_microseconds, output_file, crossfade_duration=2.0):
    """
    Merge the audio file with itself using the calculated offset.

    Args:
        input_file: Path to input audio file
        offset_microseconds: Offset in microseconds where the loop should occur
        output_file: Path to output file
        crossfade_duration: Duration of crossfade in seconds
    """
    print(f"\nMerging audio with {crossfade_duration}s crossfade...")

    # Get total duration
    total_duration = get_audio_duration(input_file)
    offset_seconds = offset_microseconds / 1_000_000

    # Calculate where to start the second copy
    # We want to overlap at the loop point
    # The second file should start at: total_duration - (last_25%_start + offset)

    # For seamless looping:
    # First file plays normally
    # Second file starts at the point where it would create the loop
    # We need to trim the second file and overlay it

    # Calculate the delay for the second input (when to start overlaying)
    # The overlap should occur at total_duration - offset
    overlap_start = total_duration - offset_seconds - crossfade_duration

    if overlap_start < 0:
        print("Warning: Offset is too large, adjusting...")
        overlap_start = total_duration * 0.5

    # FFmpeg command with acrossfade filter
    cmd = [
        'ffmpeg',
        '-i', str(input_file),
        '-i', str(input_file),
        '-filter_complex',
        f'[0][1]acrossfade=d={crossfade_duration}:o=1:c1=qsin:c2=qsin',
        '-y',  # Overwrite output file
        str(output_file)
    ]

    print(f"Running FFmpeg command...")
    print(f"Overlap starts at: {overlap_start:.3f}s")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Error running FFmpeg:")
        print(result.stderr)
        return False

    print(f"\n✓ Successfully created: {output_file}")

    # Get new duration
    new_duration = get_audio_duration(output_file)
    extension = new_duration - total_duration
    print(f"Original duration: {total_duration:.2f}s")
    print(f"New duration: {new_duration:.2f}s")
    print(f"Extended by: {extension:.2f}s ({extension/total_duration*100:.1f}%)")

    return True


def main():
    parser = argparse.ArgumentParser(
        description='Analyze and seamlessly merge looping audio files'
    )
    parser.add_argument('input_file', type=str, help='Input audio file (mp3, wav, etc.)')
    parser.add_argument('-o', '--output', type=str, help='Output file (default: input_looped.mp3)')
    parser.add_argument('-c', '--crossfade', type=float, default=2.0,
                        help='Crossfade duration in seconds (default: 2.0)')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Only analyze and show loop point, do not merge')

    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_name(f"{input_path.stem}_looped{input_path.suffix}")

    print(f"Input file: {input_path}")
    print(f"Output file: {output_path}")
    print("=" * 60)

    # Load first 25% and last 25%
    print("\nLoading first 25% of audio...")
    first_segment, sr, total_samples = load_audio_segment(input_path, 0, 25)

    print("Loading last 25% of audio...")
    last_segment, _, _ = load_audio_segment(input_path, 75, 100)

    # Find the best loop point
    offset_samples, offset_microseconds, correlation_score = find_best_loop_point(
        first_segment, last_segment, sr
    )

    if correlation_score < 0.5:
        print(f"\n⚠ Warning: Low correlation score ({correlation_score:.4f})")
        print("The audio might not loop seamlessly. Consider:")
        print("  - Using a different audio file")
        print("  - Adjusting the crossfade duration")
        print("  - Manual loop point selection")

    if args.analyze_only:
        print("\nAnalysis complete (--analyze-only mode)")
        sys.exit(0)

    # Merge the audio
    success = merge_with_crossfade(
        input_path,
        offset_microseconds,
        output_path,
        args.crossfade
    )

    if success:
        print("\n✓ Done!")
    else:
        print("\n✗ Failed to merge audio")
        sys.exit(1)


if __name__ == '__main__':
    main()
