"""Tests for slideshow config."""

from pathlib import Path

from brainrot.slideshow_config import SlideshowConfig


def test_default_config():
    config = SlideshowConfig(
        prompt="Where would you live?",
        output_path=Path("output/test.mp4"),
        bgm_path=Path("music.mp3"),
    )
    assert config.prompt == "Where would you live?"
    assert config.seconds_per_slide == 6.0
    assert config.intro_duration == 3.0
    assert config.fade_duration == 0.5
    assert config.ken_burns_zoom == 1.15
    assert config.width == 1080
    assert config.height == 1920
    assert config.fps == 30
    assert config.num_images == 10
    assert config.dev_mode is False


def test_render_dimensions_full():
    config = SlideshowConfig(
        prompt="test",
        output_path=Path("out.mp4"),
        bgm_path=Path("m.mp3"),
    )
    assert config.render_width == 1080
    assert config.render_height == 1920


def test_render_dimensions_dev():
    config = SlideshowConfig(
        prompt="test",
        output_path=Path("out.mp4"),
        bgm_path=Path("m.mp3"),
        dev_mode=True,
    )
    assert config.render_width == 540
    assert config.render_height == 960


def test_frozen():
    config = SlideshowConfig(
        prompt="test",
        output_path=Path("out.mp4"),
        bgm_path=Path("m.mp3"),
    )
    try:
        config.prompt = "changed"
        assert False, "Should have raised"
    except AttributeError:
        pass
