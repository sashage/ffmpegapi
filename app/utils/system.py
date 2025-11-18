#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: system.py
Author: Maria Kevin
Created: 2025-11-09
Description: System-level operations for directory and file management.
"""

__author__ = "Maria Kevin"
__version__ = "0.1.0"


import subprocess
import uuid
import os
from app.config import settings


def create_temp_folder(parent_dir: str) -> str:
    """Create a temporary folder inside the parent directory and return its absolute path."""
    temp_folder_name = str(uuid.uuid4())
    # parent_dir is already absolute from config
    temp_folder_path = os.path.join(parent_dir, temp_folder_name)
    subprocess.run(["mkdir", "-p", temp_folder_path])
    return temp_folder_path


def ensure_directories_exist() -> None:
    """Ensure that the upload and output directories exist."""
    subprocess.run(["mkdir", "-p", settings.upload_dir])
    subprocess.run(["mkdir", "-p", settings.output_dir])
