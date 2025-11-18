#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: task.py
Author: Maria Kevin
Created: 2025-11-09
Description: Background task for cleaning up temporary files.
"""

__author__ = "Maria Kevin"
__version__ = "0.1.0"


import datetime
import os
import shutil
import logging
import asyncio
from app.config import settings

logger = logging.getLogger(__name__)


def cleanup_old_folders(path) -> None:
    """Deletes sub folders and their contents if older than 10 minutes.
    Does not delete the parent folder itself.
    """
    if not os.path.exists(path):
        return

    now = datetime.datetime.now()
    timeout = 10  # minutes

    for subdir in os.listdir(path):
        folder_path = os.path.join(path, subdir)
        if not os.path.isdir(folder_path):
            continue

        stat = os.stat(folder_path)
        modified = datetime.datetime.fromtimestamp(stat.st_mtime)

        # Delete if older than timeout minutes
        if (now - modified).total_seconds() / 60 > timeout:
            try:
                # Count files before deletion for logging
                file_count = sum(len(files) for _, _, files in os.walk(folder_path))

                # Delete folder and all its contents recursively
                shutil.rmtree(folder_path)

                logger.info(
                    f"Deleted {subdir} ({file_count} file(s)) - {int((now - modified).total_seconds() / 60)} minutes old"
                )
            except OSError as e:
                logger.error(f"Error deleting {subdir}: {e}")


async def periodic_cleanup(interval: int = 600) -> None:
    """Periodically runs the cleanup task every 'interval' seconds."""

    while True:
        cleanup_old_folders(settings.upload_dir)
        cleanup_old_folders(settings.output_dir)
        await asyncio.sleep(interval)
