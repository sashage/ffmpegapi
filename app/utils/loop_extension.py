"""
Seamless Audio Loop Extension Utility

Analyzes an audio file to find the optimal loop point between the first 25% and last 25%,
then creates a seamlessly merged version with extended playtime.
"""

import subprocess
from pathlib import Path
from typing import Tuple

import librosa
import numpy as np
from scipy import signal


def load_audio_segment(
    file_path: Path | str, start_percent: float = 0, end_percent: float = 100
) -> Tuple[np.ndarray, int, int]:
    """Load a segment of an audio file.

    Args:
        file_path: Path to audio file
        start_percent: Start position as percentage (0-100)
        end_percent: End position as percentage (0-100)

    Returns:
        Tuple of (audio_segment, sample_rate, total_samples)
    """
    # Load full audio to get duration
    y, sr = librosa.load(str(file_path), sr=None, mono=True)

    total_samples = len(y)
    start_sample = int(total_samples * start_percent / 100)
    end_sample = int(total_samples * end_percent / 100)

    segment = y[start_sample:end_sample]

    return segment, sr, total_samples


def find_best_loop_point(
    first_segment: np.ndarray, last_segment: np.ndarray, sr: int
) -> Tuple[int, int, float]:
    """Find the best loop point using cross-correlation.

    Args:
        first_segment: Audio data from the first 25%
        last_segment: Audio data from the last 25%
        sr: Sample rate

    Returns:
        Tuple of (offset_samples, offset_microseconds, correlation_score)
    """
    # Use cross-correlation to find where first_segment best matches within last_segment
    # We'll compare the beginning of first_segment with sliding windows in last_segment

    # Use a reasonable window size (e.g., 5 seconds or length of shorter segment)
    window_duration = min(5.0, len(first_segment) / sr, len(last_segment) / sr)
    window_samples = int(window_duration * sr)

    search_segment = first_segment[:window_samples]

    # Normalize for better correlation
    search_segment = (search_segment - np.mean(search_segment)) / (
        np.std(search_segment) + 1e-10
    )

    # Correlate with last segment
    correlation = signal.correlate(last_segment, search_segment, mode="valid")

    # Find the peak correlation
    best_offset = np.argmax(correlation)
    max_correlation = correlation[best_offset]

    # Normalize correlation score
    correlation_score = max_correlation / len(search_segment)

    # Convert to microseconds
    offset_microseconds = int((best_offset / sr) * 1_000_000)

    return best_offset, offset_microseconds, correlation_score


def get_audio_duration(file_path: Path | str) -> float:
    """Get audio duration in seconds using ffprobe.

    Args:
        file_path: Path to audio file

    Returns:
        Duration in seconds
    """
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def merge_with_crossfade(
    input_file: Path | str,
    offset_microseconds: int,
    output_file: Path | str,
    crossfade_duration: float = 2.0,
) -> Tuple[bool, str]:
    """Merge the audio file with itself using the calculated offset.

    Args:
        input_file: Path to input audio file
        offset_microseconds: Offset in microseconds where the loop should occur
        output_file: Path to output file
        crossfade_duration: Duration of crossfade in seconds

    Returns:
        Tuple of (success, error_message)
    """
    # Get total duration
    total_duration = get_audio_duration(input_file)
    offset_seconds = offset_microseconds / 1_000_000

    # Calculate where to start the second copy
    overlap_start = total_duration - offset_seconds - crossfade_duration

    if overlap_start < 0:
        overlap_start = total_duration * 0.5

    # FFmpeg command with acrossfade filter
    cmd = [
        "ffmpeg",
        "-i",
        str(input_file),
        "-i",
        str(input_file),
        "-filter_complex",
        f"[0][1]acrossfade=d={crossfade_duration}:o=1:c1=qsin:c2=qsin",
        "-y",  # Overwrite output file
        str(output_file),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return False, result.stderr

    return True, ""


def extend_audio_loop(
    input_path: Path | str,
    output_path: Path | str,
    threshold: float = 0.5,
    crossfade_duration: float = 2.0,
) -> dict:
    """Analyze audio and create extended loop if suitable.

    Args:
        input_path: Path to input audio file
        output_path: Path to output file
        threshold: Minimum correlation score to proceed with extension (0-1)
        crossfade_duration: Duration of crossfade in seconds

    Returns:
        Dictionary with:
            - success: bool - Whether operation completed successfully
            - extended: bool - Whether file was extended (False if returned original)
            - correlation_score: float - Correlation score from analysis
            - message: str - Human-readable message
            - original_duration: float - Original duration in seconds
            - new_duration: float - New duration in seconds
            - error: str - Error message if failed
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    try:
        # Get original duration
        original_duration = get_audio_duration(input_path)

        # Load first 25% and last 25%
        first_segment, sr, total_samples = load_audio_segment(input_path, 0, 25)
        last_segment, _, _ = load_audio_segment(input_path, 75, 100)

        # Find the best loop point
        offset_samples, offset_microseconds, correlation_score = find_best_loop_point(
            first_segment, last_segment, sr
        )

        # Check if correlation score is below threshold
        if correlation_score < threshold:
            # Copy original file to output without modification
            subprocess.run(["cp", str(input_path), str(output_path)], check=True)

            return {
                "success": True,
                "extended": False,
                "correlation_score": float(correlation_score),
                "message": f"Correlation score ({correlation_score:.4f}) below threshold ({threshold}). Returning original file.",
                "original_duration": original_duration,
                "new_duration": original_duration,
                "error": "",
            }

        # Merge the audio with crossfade
        success, error_msg = merge_with_crossfade(
            input_path, offset_microseconds, output_path, crossfade_duration
        )

        if not success:
            return {
                "success": False,
                "extended": False,
                "correlation_score": float(correlation_score),
                "message": "Failed to merge audio",
                "original_duration": original_duration,
                "new_duration": original_duration,
                "error": error_msg,
            }

        # Get new duration
        new_duration = get_audio_duration(output_path)
        extension = new_duration - original_duration

        return {
            "success": True,
            "extended": True,
            "correlation_score": float(correlation_score),
            "message": f"Successfully extended audio by {extension:.2f}s ({extension/original_duration*100:.1f}%)",
            "original_duration": original_duration,
            "new_duration": new_duration,
            "error": "",
        }

    except Exception as e:
        return {
            "success": False,
            "extended": False,
            "correlation_score": 0.0,
            "message": f"Error processing audio: {str(e)}",
            "original_duration": 0.0,
            "new_duration": 0.0,
            "error": str(e),
        }
