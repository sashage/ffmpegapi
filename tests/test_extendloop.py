#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File: test_extendloop.py
Author: Maria Kevin
Created: 2025-11-18
Description: Tests for the /extendloop endpoint.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_extendloop_missing_file():
    """Test that missing input file returns 422 validation error."""
    response = client.post("/extendloop")
    assert response.status_code == 422


def test_extendloop_large_file():
    """Test that file exceeding size limit is rejected."""
    large_file_content = b"a" * (100 * 1024 * 1024 + 1)  # 100MB + 1 byte
    files = {"input_file": ("large.mp3", large_file_content, "audio/mpeg")}
    response = client.post("/extendloop", files=files)
    assert response.status_code == 400
    assert "exceeds" in response.json()["detail"]


@patch("app.main.extend_audio_loop")
@patch("app.utils.file_operations.save_uploaded_file")
@patch("app.main.FileResponse")
def test_extendloop_success_extended(mock_file_response, mock_save, mock_extend):
    """Test successful loop extension with high correlation."""
    from unittest.mock import MagicMock

    mock_extend.return_value = {
        "success": True,
        "extended": True,
        "correlation_score": 0.85,
        "message": "Extended",
        "original_duration": 50.0,
        "new_duration": 97.5,
        "error": "",
    }

    # Create mock FileResponse
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_file_response.return_value = mock_response

    small_file = b"a" * (1 * 1024 * 1024)  # 1MB
    files = {"input_file": ("test.mp3", small_file, "audio/mpeg")}

    with patch("os.path.exists", return_value=True):
        response = client.post("/extendloop", files=files)

    # Verify FileResponse was created
    assert mock_file_response.called
    # Verify headers were set
    assert "X-Extended" in mock_response.headers
    assert mock_response.headers["X-Extended"] == "true"
    assert mock_response.headers["X-Correlation-Score"] == "0.8500"


@patch("app.main.extend_audio_loop")
@patch("app.utils.file_operations.save_uploaded_file")
@patch("app.main.FileResponse")
def test_extendloop_not_extended(mock_file_response, mock_save, mock_extend):
    """Test that low correlation returns original file unchanged."""
    from unittest.mock import MagicMock

    mock_extend.return_value = {
        "success": True,
        "extended": False,
        "correlation_score": 0.35,
        "message": "Below threshold",
        "original_duration": 50.0,
        "new_duration": 50.0,
        "error": "",
    }

    mock_response = MagicMock()
    mock_response.headers = {}
    mock_file_response.return_value = mock_response

    small_file = b"a" * (1 * 1024 * 1024)
    files = {"input_file": ("test.mp3", small_file, "audio/mpeg")}

    with patch("os.path.exists", return_value=True):
        response = client.post("/extendloop", files=files)

    assert mock_file_response.called
    assert mock_response.headers["X-Extended"] == "false"


@patch("app.main.extend_audio_loop")
@patch("app.utils.file_operations.save_uploaded_file")
def test_extendloop_processing_error(mock_save, mock_extend):
    """Test handling of processing errors."""
    mock_extend.return_value = {
        "success": False,
        "extended": False,
        "correlation_score": 0.0,
        "message": "Error",
        "original_duration": 0.0,
        "new_duration": 0.0,
        "error": "librosa failed",
    }

    small_file = b"a" * (1 * 1024 * 1024)
    files = {"input_file": ("test.mp3", small_file, "audio/mpeg")}
    response = client.post("/extendloop", files=files)

    assert response.status_code == 500
    assert "Failed" in response.json()["detail"]
