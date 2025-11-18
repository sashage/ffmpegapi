#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: main.py
Author: Maria Kevin
Created: 2025-11-09
Description: FFmpeg command execution via FastAPI endpoint.
"""

__author__ = "Maria Kevin"
__version__ = "0.1.0"

import logging
import os
import shlex
import subprocess
from contextlib import asynccontextmanager
from typing import Union

from fastapi import FastAPI, Form, Request, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import CommandResult
from app.utils import (
    allow_command,
    ensure_directories_exist,
    preprocess_cmd,
    get_output_path_from_cmd,
    create_temp_folder,
    save_uploaded_file,
    input_file_size_within_limit,
)
from app.utils.loop_extension import extend_audio_loop
from app.task import periodic_cleanup
import asyncio
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_directories_exist()
    task = asyncio.create_task(periodic_cleanup())
    yield
    task.cancel()


app = FastAPI(
    lifespan=lifespan, docs_url=None if settings.env == "production" else "/docs"
)

ensure_directories_exist()  # need to ensure directories exist before mounting static files
app.mount("/static", StaticFiles(directory=settings.output_dir), name="static")


@app.get("/")
async def read_root():
    return {"message": "use /run to execute the main functionality"}


@app.post("/run", response_model=CommandResult)
async def ffmpeg_run(
    request: Request,
    cmd: str = Form(...),
    input_file: UploadFile | None = File(None),
    input_file_2: UploadFile | None = File(None),
    input_file_3: UploadFile | None = File(None),
    input_file_4: UploadFile | None = File(None),
    input_file_5: UploadFile | None = File(None),
    return_file: bool = Form(
        False, description="If true, returns the output file itself."
    ),
) -> Union[CommandResult, FileResponse]:
    """Executes the provided FFmpeg command after validation and preprocessing."""
    # Validate command (raises HTTPException on failure)
    allow_command(cmd)

    # Preprocess command with uploaded files (raises HTTPException on failure)
    processed_cmd = preprocess_cmd(
        cmd=cmd,
        input_file=input_file,
        input_file_2=input_file_2,
        input_file_3=input_file_3,
        input_file_4=input_file_4,
        input_file_5=input_file_5,
    )

    # Tokenize and execute
    import sys
    print(f"DEBUG: FFmpeg command: {processed_cmd}", file=sys.stderr)
    result = subprocess.run(
        shlex.split(processed_cmd), capture_output=True, text=True, timeout=30
    )

    # Get the actual output file path from the processed command (already absolute)
    output_file_path = shlex.split(processed_cmd)[-1].strip("'\"")

    # Check if FFmpeg succeeded
    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg failed: {result.stderr}"
        )

    # Check if output file was created
    if not os.path.exists(output_file_path):
        raise HTTPException(
            status_code=500,
            detail=f"Output file not created at {output_file_path}. FFmpeg stderr: {result.stderr}"
        )

    if return_file:
        # Return the file directly
        return FileResponse(
            path=output_file_path,
            media_type="application/octet-stream",
            filename=os.path.basename(output_file_path)
        )

    # Return JSON response with URL for later download
    output_url = request.url_for(
        "static", path=get_output_path_from_cmd(processed_cmd, replace_parent_dir=True)
    )

    return CommandResult(
        cmd=processed_cmd,
        stdout=result.stdout,
        stderr=result.stderr,
        returncode=result.returncode,
        output_url=str(output_url),
    )


@app.post("/extendloop", response_model=None)
async def extend_loop_endpoint(
    input_file: UploadFile = File(...),
    crossfade: float = Form(2.0),
    threshold: float = Form(0.5),
) -> FileResponse:
    """Analyzes audio and creates an extended seamless loop if suitable.

    Returns the extended file if correlation score >= threshold, otherwise returns original.
    """
    logger.info(f"📥 /extendloop request: file={input_file.filename}, size={input_file.size}, threshold={threshold}, crossfade={crossfade}s")

    # Validate file size
    if not input_file_size_within_limit(input_file.size):
        logger.warning(f"File size {input_file.size} exceeds limit")
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {settings.max_upload_size_mb / (1024 * 1024):.0f}MB"
        )

    # Create temp folders
    upload_temp_folder = create_temp_folder(settings.upload_dir)
    output_temp_folder = create_temp_folder(settings.output_dir)
    logger.info(f"Created temp folders: upload={upload_temp_folder}, output={output_temp_folder}")

    # Save uploaded file
    input_filename = input_file.filename or "input.mp3"
    input_path = os.path.join(upload_temp_folder, input_filename)
    file_bytes = await input_file.read()
    save_uploaded_file(file_bytes, input_path)
    logger.info(f"Saved uploaded file to {input_path}")

    # Determine output filename
    file_stem, file_ext = os.path.splitext(input_filename)
    output_filename = f"{file_stem}_extended{file_ext}"
    output_path = os.path.join(output_temp_folder, output_filename)

    # Run loop extension
    result = extend_audio_loop(
        input_path=input_path,
        output_path=output_path,
        threshold=threshold,
        crossfade_duration=crossfade,
    )

    # Check if operation failed
    if not result["success"]:
        logger.error(f"Loop extension failed: {result['error']}")
        raise HTTPException(status_code=500, detail=f"Failed: {result['error']}")

    # Check output exists
    if not os.path.exists(output_path):
        logger.error(f"Output file not created at {output_path}")
        raise HTTPException(status_code=500, detail="Output file not created")

    # Return file directly with metadata headers
    response = FileResponse(
        path=output_path,
        media_type="application/octet-stream",
        filename=output_filename
    )
    response.headers["X-Extended"] = str(result["extended"]).lower()
    response.headers["X-Correlation-Score"] = f"{result['correlation_score']:.4f}"
    response.headers["X-Original-Duration"] = f"{result['original_duration']:.2f}"
    response.headers["X-New-Duration"] = f"{result['new_duration']:.2f}"

    logger.info(f"📤 Returning file: extended={result['extended']}, correlation={result['correlation_score']:.4f}, duration={result['original_duration']:.2f}s → {result['new_duration']:.2f}s")

    return response
