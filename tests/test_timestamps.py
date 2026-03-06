"""Tests for timestamp module."""

from brainrot.timestamps import WordTimestamp, validate_timestamps


def test_validate_timestamps_within_drift(sample_words):
    # Last word ends at 3.0, audio is 3.2 — drift is 0.2 (ok)
    assert validate_timestamps(sample_words, audio_duration=3.2) is True


def test_validate_timestamps_exceeds_drift(sample_words):
    # Last word ends at 3.0, audio is 4.0 — drift is 1.0 (too much)
    assert validate_timestamps(sample_words, audio_duration=4.0) is False


def test_validate_timestamps_empty():
    assert validate_timestamps([], audio_duration=5.0) is False


def test_validate_timestamps_exact_match(sample_words):
    assert validate_timestamps(sample_words, audio_duration=3.0) is True


def test_word_timestamp_is_frozen():
    w = WordTimestamp(word="hello", start=0.0, end=0.5, confidence=0.9)
    try:
        w.word = "changed"
        assert False, "Should have raised FrozenInstanceError"
    except AttributeError:
        pass
