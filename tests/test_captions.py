"""Caption tests."""

from PIL import Image

from brainrot.captions import create_single_word_frame, _find_current_word_index
from brainrot.config import CaptionStyle, VideoConfig
from brainrot.timestamps import WordTimestamp


def test_single_word_frame_returns_rgba(dev_video_config, default_caption_style):
    frame = create_single_word_frame("hello", dev_video_config, default_caption_style)
    assert isinstance(frame, Image.Image)
    assert frame.mode == "RGBA"
    assert frame.size == (dev_video_config.width, dev_video_config.height)


def test_single_word_frame_empty_word(dev_video_config, default_caption_style):
    frame = create_single_word_frame("", dev_video_config, default_caption_style)
    assert frame.mode == "RGBA"
    # all transparent
    pixels = list(frame.getdata())
    assert all(p[3] == 0 for p in pixels)


def test_find_current_word_index(sample_words):
    # door 0.2-0.5
    assert _find_current_word_index(sample_words, 0.3) == 1
    # The 0.0-0.2
    assert _find_current_word_index(sample_words, 0.1) == 0
    # hallway 2.5-3.0
    assert _find_current_word_index(sample_words, 2.7) == 8


def test_single_word_frame_has_content(dev_video_config, default_caption_style):
    frame = create_single_word_frame("hello", dev_video_config, default_caption_style)
    pixels = list(frame.getdata())
    assert any(p[3] > 0 for p in pixels)
