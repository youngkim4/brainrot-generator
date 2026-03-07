"""Pipeline tests."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brainrot.config import PipelineConfig, TTSProvider
from brainrot.timestamps import WordTimestamp


@pytest.fixture
def basic_config(tmp_path):
    return PipelineConfig(
        story_text="Hello world test story.",
        background_video=tmp_path / "bg.mp4",
        output_path=tmp_path / "output.mp4",
    )


@pytest.mark.asyncio
async def test_run_pipeline_rejects_empty_story(tmp_path):
    from brainrot.pipeline import run_pipeline

    config = PipelineConfig(
        story_text="",
        background_video=tmp_path / "bg.mp4",
        output_path=tmp_path / "output.mp4",
    )
    with pytest.raises(ValueError, match="empty"):
        await run_pipeline(config)


@pytest.mark.asyncio
async def test_run_pipeline_rejects_failed_tts(basic_config):
    from brainrot.pipeline import run_pipeline

    mock_engine = AsyncMock()
    mock_engine.synthesize = AsyncMock(return_value=Path("/fake/audio.mp3"))

    with patch("brainrot.pipeline.create_tts_engine", return_value=mock_engine):
        with pytest.raises(RuntimeError, match="TTS failed"):
            await run_pipeline(basic_config)


def test_config_repr_masks_api_key():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
        elevenlabs_api_key="sk-secret-key-12345",
    )
    r = repr(config)
    assert "sk-secret-key-12345" not in r
    assert "***" in r


def test_config_repr_empty_key_not_masked():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
    )
    r = repr(config)
    assert "***" not in r
