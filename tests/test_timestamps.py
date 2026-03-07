"""Timestamp tests."""

import pytest

from brainrot.timestamps import WordTimestamp, validate_timestamps


def test_validate_timestamps_within_drift(sample_words):
    # drift 0.2, ok
    assert validate_timestamps(sample_words, audio_duration=3.2) is True


def test_validate_timestamps_exceeds_drift(sample_words):
    # drift 3.0, exceeds default
    assert validate_timestamps(sample_words, audio_duration=6.0) is False


def test_validate_timestamps_empty():
    assert validate_timestamps([], audio_duration=5.0) is False


def test_validate_timestamps_exact_match(sample_words):
    assert validate_timestamps(sample_words, audio_duration=3.0) is True


def test_word_timestamp_is_frozen():
    w = WordTimestamp(word="hello", start=0.0, end=0.5, confidence=0.9)
    with pytest.raises(AttributeError):
        w.word = "changed"


def test_validate_timestamps_custom_max_drift(sample_words):
    # drift 0.8
    assert validate_timestamps(sample_words, audio_duration=3.8, max_drift=1.0) is True
    assert validate_timestamps(sample_words, audio_duration=3.8, max_drift=0.5) is False
