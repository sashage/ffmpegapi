#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: command_processing.py
Author: Maria Kevin
Created: 2025-11-09
Description: Command preprocessing and manipulation functions for FFmpeg commands.
"""

__author__ = "Maria Kevin"
__version__ = "0.1.0"


import os
import shlex
from fastapi import UploadFile
from app.config import settings
from app.exceptions import InvalidFFmpegCommandException
from app.utils.file_operations import save_uploaded_file
from app.utils.system import create_temp_folder
from app.utils.validation import input_file_size_within_limit


def preprocess_cmd(
    cmd: str,
    input_file: UploadFile | None = None,
    input_file_2: UploadFile | None = None,
    input_file_3: UploadFile | None = None,
    input_file_4: UploadFile | None = None,
    input_file_5: UploadFile | None = None,
) -> str:
    """Saves uploaded input files and replaces input tags in the command.

    Supports up to 5 input files:
    - input_file -> <input>
    - input_file_2 -> <input_2>
    - input_file_3 -> <input_3>
    - input_file_4 -> <input_4>
    - input_file_5 -> <input_5>

    Example:
    cmd = "ffmpeg -i <input> -i <input_2> -filter_complex hstack output.mp4"
    Files: input_file=video1.mp4, input_file_2=video2.mp4
    Result: Saves both files and replaces placeholders with their paths.
    """

    # Collect uploaded files with their corresponding placeholder keys
    files_map = {
        "input": input_file,
        "input_2": input_file_2,
        "input_3": input_file_3,
        "input_4": input_file_4,
        "input_5": input_file_5,
    }

    # Filter out None values to get actually uploaded files
    uploaded_files = {key: file for key, file in files_map.items() if file is not None}

    # Validate at least one file is provided
    if not uploaded_files:
        raise InvalidFFmpegCommandException(
            detail="At least one input file must be provided."
        )

    # Create a single temp folder for all input files in this request
    temp_folder = create_temp_folder(settings.upload_dir)

    # Process each uploaded file
    new_cmd = cmd
    for placeholder_key, file in uploaded_files.items():
        # Validate file size
        if not input_file_size_within_limit(file.size):
            raise InvalidFFmpegCommandException(
                status_code=413,
                detail=f"File '{file.filename}' size exceeds the maximum allowed limit of {settings.max_upload_size_mb} bytes.",
            )

        # Construct placeholder and check if it exists in command
        placeholder = f"<{placeholder_key}>"
        if placeholder not in cmd:
            raise InvalidFFmpegCommandException(
                detail=f"Uploaded file for '{placeholder}' but placeholder not found in command."
            )

        # Save file to temp folder
        full_path = f"{temp_folder}/{file.filename}"
        save_uploaded_file(file.file.read(), full_path)

        # Replace placeholder with actual file path
        new_cmd = new_cmd.replace(placeholder, f"'{full_path}'", 1)

    # Replace output tag
    new_cmd = replace_output_tag(new_cmd)
    return new_cmd


def replace_input_tag(cmd: str, full_path: str) -> str:
    """Replaces the input tag in the command with the actual local input file path."""
    # get the part after -i
    # replace only the input file name part
    new_cmd = cmd.replace(settings.input_tag_placeholder, f"'{full_path}'", 1)
    return new_cmd


def get_output_path_from_cmd(cmd: str, replace_parent_dir: bool = False) -> str:
    """Extract the output file path safely from an ffmpeg command string.

    Handles quoted and unquoted filenames.
    Example:
        ffmpeg -i input.mp3 -c:v libx264 'output video.mp4' → output video.mp4
        ffmpeg -i input.mp3 -c:v libx264 video.mp4         → video.mp4
    """
    tokens = shlex.split(cmd)
    if not tokens:
        return ""

    # Last token is assumed to be output path
    output_path = tokens[-1].strip()

    # Normalize quotes (in case shlex didn't fully handle it)
    output_path = output_path.strip("'").strip('"')

    if replace_parent_dir:
        # Extract path relative to the output directory
        output_path = os.path.normpath(output_path)

        # Find the output_dir in the path and get everything after it
        output_dir = os.path.normpath(settings.output_dir)
        if output_dir in output_path:
            # Split on the output_dir and take the part after it
            parts = output_path.split(output_dir, 1)
            if len(parts) == 2:
                # Remove leading separator
                output_path = parts[1].lstrip(os.sep)
        else:
            # Fallback: remove first directory level if present
            parts = output_path.split(os.sep, 1)
            if len(parts) == 2:
                output_path = parts[1]

    return output_path


def replace_output_tag(cmd: str) -> str:
    "Replace the output tag in the command with the actual local output file path."

    # get the part after the last space
    output_file_name_part = get_output_path_from_cmd(cmd)
    # have only the part after last /
    output_file_name_part = output_file_name_part.split("/")[-1]

    local_path = f"{create_temp_folder(settings.output_dir)}/{output_file_name_part}"

    if cmd.endswith("'"):
        new_cmd = cmd.replace(output_file_name_part, f"{local_path}", 1)
    else:
        new_cmd = cmd.replace(output_file_name_part, f"'{local_path}'", 1)
    return new_cmd
