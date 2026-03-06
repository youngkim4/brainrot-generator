"""Shared test fixtures."""

import pytest

from brainrot.config import CaptionStyle, PipelineConfig, TTSProvider, VideoConfig
from brainrot.timestamps import WordTimestamp


@pytest.fixture
def sample_words() -> list[WordTimestamp]:
    return [
        WordTimestamp(word="The", start=0.0, end=0.2, confidence=0.95),
        WordTimestamp(word="door", start=0.2, end=0.5, confidence=0.92),
        WordTimestamp(word="creaked", start=0.5, end=0.9, confidence=0.88),
        WordTimestamp(word="open", start=0.9, end=1.2, confidence=0.91),
        WordTimestamp(word="slowly", start=1.2, end=1.7, confidence=0.90),
        WordTimestamp(word="in", start=1.7, end=1.9, confidence=0.93),
        WordTimestamp(word="the", start=1.9, end=2.1, confidence=0.94),
        WordTimestamp(word="dark", start=2.1, end=2.5, confidence=0.89),
        WordTimestamp(word="hallway", start=2.5, end=3.0, confidence=0.87),
    ]


@pytest.fixture
def dev_video_config() -> VideoConfig:
    return VideoConfig(width=540, height=960, fps=30, max_duration=10)


@pytest.fixture
def default_caption_style() -> CaptionStyle:
    return CaptionStyle()
