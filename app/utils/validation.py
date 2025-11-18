#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: validation.py
Author: Maria Kevin
Created: 2025-11-09
Description: Validation functions for FFmpeg commands and file operations.
"""

__author__ = "Maria Kevin"
__version__ = "0.1.0"


import subprocess

from fastapi import Form
from app.config import settings
from app.exceptions import (
    FFmpegNotInstalledException,
    InvalidFFmpegCommandException,
    ProhibitedOperationException,
)
from typing_extensions import Annotated


def check_if_ffmpeg_installed() -> bool:
    """Check if FFmpeg is installed on the system."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False


def validate_ffmpeg_command(cmd: str) -> bool:
    """Validate if the command is a proper FFmpeg command."""
    return cmd.strip().startswith("ffmpeg")


def contains_prohibited_operations(cmd: str) -> bool:
    """Check if the command contains prohibited operations."""
    commands_to_exclude = [
        "rm",
        "del",
        "mv",
        "cp",
        "sudo",
        "apt-get",
        "yum",
        "dnf",
        "curl",
        "wget",
    ]
    return any(excluded in cmd for excluded in commands_to_exclude)


def check_if_input_tag_exists(cmd: str) -> bool:
    """Check if the command contains at least one input tag."""
    # Check for <input> or <input_2> through <input_5>
    if f"-i {settings.input_tag_placeholder}" in cmd:
        return True
    for i in range(2, settings.max_input_files + 1):
        if f"-i <input_{i}>" in cmd:
            return True
    return False


def input_file_size_within_limit(file_size: int | None) -> bool:
    """Check if the uploaded file size is within the allowed limit."""
    file_size = file_size or 0
    return 0 < file_size <= settings.max_upload_size_mb


def allow_command(cmd: Annotated[str, Form(...)]) -> bool:
    """Checks if the command is allowed to be executed."""

    if not check_if_ffmpeg_installed():
        raise FFmpegNotInstalledException()

    if not validate_ffmpeg_command(cmd):
        raise InvalidFFmpegCommandException()

    if contains_prohibited_operations(cmd):
        raise ProhibitedOperationException()

    if not check_if_input_tag_exists(cmd):
        raise InvalidFFmpegCommandException(
            detail=f"Command must contain an input tag '-i {settings.input_tag_placeholder}'."
        )

    return True
