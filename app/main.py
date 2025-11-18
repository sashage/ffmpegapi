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
)
from app.task import periodic_cleanup
import asyncio
from app.config import settings


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
