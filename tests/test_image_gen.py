"""Tests for image generation module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from brainrot.image_gen import (
    _build_image_prompt,
    generate_images,
    generate_subjects,
    load_images_from_dir,
)


def test_load_images_from_dir(tmp_path):
    (tmp_path / "castle.png").write_bytes(b"fake")
    (tmp_path / "beach.jpg").write_bytes(b"fake")
    (tmp_path / "notes.txt").write_bytes(b"ignore")

    paths = load_images_from_dir(tmp_path)
    assert len(paths) == 2
    names = [p.name for p in paths]
    assert "beach.jpg" in names
    assert "castle.png" in names


def test_load_images_from_dir_empty(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_images_from_dir(tmp_path)


def test_load_images_sorted(tmp_path):
    (tmp_path / "c_forest.png").write_bytes(b"fake")
    (tmp_path / "a_castle.png").write_bytes(b"fake")
    (tmp_path / "b_beach.png").write_bytes(b"fake")

    paths = load_images_from_dir(tmp_path)
    assert paths[0].name == "a_castle.png"
    assert paths[1].name == "b_beach.png"
    assert paths[2].name == "c_forest.png"


def test_build_image_prompt():
    result = _build_image_prompt("Crystal Palace", "a shimmering palace of ice")
    assert "Crystal Palace" in result
    assert "shimmering palace of ice" in result
    assert "cinematic lighting" in result
    assert "9:16" in result


@patch.dict("os.environ", {"GEMINI_API_KEY": ""})
def test_generate_images_no_api_key(tmp_path):
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        generate_images("test", [{"subject": "x", "setting_detail": "y"}], tmp_path)


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
def test_generate_images_success(tmp_path):
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (100, 100), (255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")
    fake_data = buf.getvalue()

    mock_part = MagicMock()
    mock_part.inline_data = MagicMock()
    mock_part.inline_data.data = fake_data

    mock_response = MagicMock()
    mock_response.parts = [mock_part]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    subjects = [{"subject": "Red Castle", "setting_detail": "a crimson fortress"}]

    with patch("google.genai.Client", return_value=mock_client):
        paths = generate_images("test prompt", subjects, tmp_path)

    assert len(paths) == 1
    assert paths[0].name == "red_castle.png"
    assert paths[0].exists()


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
def test_generate_images_path_traversal(tmp_path):
    from PIL import Image as PILImage
    from io import BytesIO

    img = PILImage.new("RGB", (100, 100), (255, 0, 0))
    buf = BytesIO()
    img.save(buf, format="PNG")

    mock_part = MagicMock()
    mock_part.inline_data = MagicMock()
    mock_part.inline_data.data = buf.getvalue()

    mock_response = MagicMock()
    mock_response.parts = [mock_part]

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    # path traversal characters are sanitized to underscores
    subjects = [{"subject": "../../../etc/passwd", "setting_detail": "test"}]
    with patch("google.genai.Client", return_value=mock_client):
        paths = generate_images("test", subjects, tmp_path)

    assert len(paths) == 1
    assert str(paths[0].resolve()).startswith(str(tmp_path.resolve()))
    assert "etc" not in str(paths[0].parent)


@patch.dict("os.environ", {"GEMINI_API_KEY": ""})
def test_generate_subjects_no_api_key():
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        generate_subjects("Where would you live?")


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
def test_generate_subjects_success():
    fake_subjects = [
        {"subject": "Crystal Cavern", "setting_detail": "underground palace"},
        {"subject": "Sky Garden", "setting_detail": "floating garden"},
    ]
    mock_response = MagicMock()
    mock_response.text = json.dumps(fake_subjects)

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        result = generate_subjects("Where would you live?", count=2)

    assert len(result) == 2
    assert result[0]["subject"] == "Crystal Cavern"
    assert result[1]["subject"] == "Sky Garden"


@patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"})
def test_generate_subjects_strips_code_fences():
    fake_subjects = [
        {"subject": "A", "setting_detail": "a"},
        {"subject": "B", "setting_detail": "b"},
    ]
    mock_response = MagicMock()
    mock_response.text = f"```json\n{json.dumps(fake_subjects)}\n```"

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response

    with patch("google.genai.Client", return_value=mock_client):
        result = generate_subjects("test", count=2)

    assert len(result) == 2
