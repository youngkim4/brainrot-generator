"""Compositor tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from brainrot.compositor import _get_render_config, _make_word_clips, _pop_scale
from brainrot.config import CaptionStyle, PipelineConfig, VideoConfig
from brainrot.timestamps import WordTimestamp


@pytest.fixture
def production_config():
    return PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
    )


@pytest.fixture
def dev_config():
    return PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
        dev_mode=True,
    )


def test_get_render_config_production(production_config):
    render = _get_render_config(production_config)
    assert render.width == 1080
    assert render.height == 1920


def test_get_render_config_dev_mode(dev_config):
    render = _get_render_config(dev_config)
    assert render.width == 540
    assert render.height == 960


def test_word_clips_one_per_word(sample_words, dev_video_config, default_caption_style):
    clips = _make_word_clips(sample_words, dev_video_config, default_caption_style)
    assert len(clips) == len(sample_words)
    for clip, word in zip(clips, sample_words):
        assert clip.start == pytest.approx(word.start)
        assert clip.duration == pytest.approx(word.end - word.start)
        clip.close()


def test_pop_scale_starts_big_settles_normal():
    assert _pop_scale(0.0) == pytest.approx(1.3)
    assert _pop_scale(0.08) == pytest.approx(1.0)
    assert _pop_scale(1.0) == pytest.approx(1.0)
