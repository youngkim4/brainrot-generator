"""Tests for caption rendering module."""

from PIL import Image

from brainrot.captions import create_caption_frame, _find_current_word_index
from brainrot.config import CaptionStyle, VideoConfig
from brainrot.timestamps import WordTimestamp


def test_create_caption_frame_returns_rgba(sample_words, dev_video_config, default_caption_style):
    frame = create_caption_frame(sample_words, 0.3, dev_video_config, default_caption_style)
    assert isinstance(frame, Image.Image)
    assert frame.mode == "RGBA"
    assert frame.size == (dev_video_config.width, dev_video_config.height)


def test_create_caption_frame_empty_words(dev_video_config, default_caption_style):
    frame = create_caption_frame([], 0.0, dev_video_config, default_caption_style)
    assert frame.mode == "RGBA"
    # All transparent
    pixels = list(frame.getdata())
    assert all(p[3] == 0 for p in pixels)


def test_find_current_word_index(sample_words):
    # "door" is at 0.2-0.5
    assert _find_current_word_index(sample_words, 0.3) == 1
    # "The" is at 0.0-0.2
    assert _find_current_word_index(sample_words, 0.1) == 0
    # "hallway" is at 2.5-3.0
    assert _find_current_word_index(sample_words, 2.7) == 8


def test_caption_frame_not_fully_transparent(sample_words, dev_video_config, default_caption_style):
    """Caption frame at a time with words should have some non-transparent pixels."""
    frame = create_caption_frame(sample_words, 0.3, dev_video_config, default_caption_style)
    pixels = list(frame.getdata())
    has_content = any(p[3] > 0 for p in pixels)
    assert has_content
