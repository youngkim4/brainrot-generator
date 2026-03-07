"""Tests for slideshow pipeline."""

from pathlib import Path

import pytest

from brainrot.slideshow_config import SlideshowConfig
from brainrot.slideshow_pipeline import run_slideshow


def test_run_slideshow_no_images():
    config = SlideshowConfig(
        prompt="Where would you live?",
        output_path=Path("output/test.mp4"),
        bgm_path=Path("music.mp3"),
    )
    with pytest.raises(ValueError, match="Provide --images-dir"):
        run_slideshow(config)


def test_run_slideshow_too_few_images(tmp_path):
    img_dir = tmp_path / "images"
    img_dir.mkdir()
    from PIL import Image
    Image.new("RGB", (100, 100)).save(str(img_dir / "one.png"))

    config = SlideshowConfig(
        prompt="test",
        output_path=tmp_path / "out.mp4",
        bgm_path=Path("music.mp3"),
        image_dir=img_dir,
    )
    with pytest.raises(ValueError, match="at least 2 images"):
        run_slideshow(config)
