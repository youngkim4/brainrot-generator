"""TTS engine tests."""

import pytest

from brainrot.config import PipelineConfig, TTSProvider
from brainrot.tts_engine import (
    EdgeTTSEngine,
    ElevenLabsTTSEngine,
    create_tts_engine,
)
from pathlib import Path


def test_create_tts_engine_defaults_to_edge():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
    )
    engine = create_tts_engine(config)
    assert isinstance(engine, EdgeTTSEngine)


def test_create_tts_engine_elevenlabs_requires_api_key():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
        tts_provider=TTSProvider.ELEVENLABS,
        elevenlabs_api_key="",
    )
    with pytest.raises(ValueError, match="API key"):
        create_tts_engine(config)


def test_create_tts_engine_elevenlabs_requires_voice_id():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
        tts_provider=TTSProvider.ELEVENLABS,
        elevenlabs_api_key="sk-test",
        elevenlabs_voice_id="",
    )
    with pytest.raises(ValueError, match="voice ID"):
        create_tts_engine(config)


def test_create_tts_engine_elevenlabs_success():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
        tts_provider=TTSProvider.ELEVENLABS,
        elevenlabs_api_key="sk-test",
        elevenlabs_voice_id="voice123",
    )
    engine = create_tts_engine(config)
    assert isinstance(engine, ElevenLabsTTSEngine)


@pytest.mark.asyncio
async def test_edge_tts_generates_audio(tmp_path):
    engine = EdgeTTSEngine(voice="en-US-ChristopherNeural")
    output = tmp_path / "test.mp3"
    result = await engine.synthesize("Hello world", output)
    assert result.exists()
    assert result.stat().st_size > 0
