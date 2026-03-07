"""Tests for slideshow compositor."""

from pathlib import Path

import numpy as np
from PIL import Image

from brainrot.slideshow_compositor import (
    _fit_image,
    _label_from_path,
    _make_ken_burns_clip,
    _render_intro_card,
    _render_slide_with_label,
)


def test_label_from_path():
    assert _label_from_path(Path("underwater_palace.png")) == "Underwater Palace"
    assert _label_from_path(Path("cloud-castle.jpg")) == "Cloud Castle"
    assert _label_from_path(Path("forest.png")) == "Forest"


def test_fit_image_wider():
    # wider than target — should crop width
    img = Image.new("RGB", (400, 200), (255, 0, 0))
    result = _fit_image(img, 100, 200)
    assert result.size == (100, 200)


def test_fit_image_taller():
    # taller than target — should crop height
    img = Image.new("RGB", (200, 400), (0, 255, 0))
    result = _fit_image(img, 200, 200)
    assert result.size == (200, 200)


def test_fit_image_exact():
    img = Image.new("RGB", (100, 200), (0, 0, 255))
    result = _fit_image(img, 100, 200)
    assert result.size == (100, 200)


def test_render_intro_card():
    frame = _render_intro_card("Where would you live?", 540, 960)
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (960, 540, 3)


def test_render_slide_with_label(tmp_path):
    # create a test image
    img = Image.new("RGB", (540, 960), (100, 150, 200))
    img_path = tmp_path / "test_slide.png"
    img.save(str(img_path))

    frame = _render_slide_with_label(img_path, "Test Label", 540, 960)
    assert isinstance(frame, np.ndarray)
    assert frame.shape == (960, 540, 3)


def test_make_ken_burns_clip():
    frame = np.full((200, 100, 3), 128, dtype=np.uint8)
    clip = _make_ken_burns_clip(frame, duration=0.1, zoom_factor=1.15, fps=10)
    assert clip.duration == 0.1
    result_frame = clip.get_frame(0.0)
    assert result_frame.shape == (200, 100, 3)
    clip.close()
