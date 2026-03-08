"""TTS engine tests."""

import pytest

from brainrot.config import PipelineConfig, TTSProvider
from brainrot.tts_engine import (
    CartesiaTTSEngine,
    EdgeTTSEngine,
    ElevenLabsTTSEngine,
    PollyTTSEngine,
    create_tts_engine,
)
from pathlib import Path


def test_create_tts_engine_defaults_to_polly():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
    )
    engine = create_tts_engine(config)
    assert isinstance(engine, PollyTTSEngine)


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


def test_create_tts_engine_cartesia_requires_api_key():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
        tts_provider=TTSProvider.CARTESIA,
        cartesia_api_key="",
    )
    with pytest.raises(ValueError, match="Cartesia API key"):
        create_tts_engine(config)


def test_create_tts_engine_cartesia_success():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
        tts_provider=TTSProvider.CARTESIA,
        cartesia_api_key="sk-test-cartesia",
    )
    engine = create_tts_engine(config)
    assert isinstance(engine, CartesiaTTSEngine)
    assert engine.voice_id == "a0e99841-438c-4a64-b679-ae501e7d6091"
    assert engine.model_id == "sonic-3"


def test_create_tts_engine_cartesia_custom_voice():
    config = PipelineConfig(
        story_text="test",
        background_video=Path("bg.mp4"),
        output_path=Path("out.mp4"),
        tts_provider=TTSProvider.CARTESIA,
        cartesia_api_key="sk-test-cartesia",
        cartesia_voice_id="custom-voice-id",
        cartesia_model_id="sonic-3",
    )
    engine = create_tts_engine(config)
    assert isinstance(engine, CartesiaTTSEngine)
    assert engine.voice_id == "custom-voice-id"


@pytest.mark.asyncio
async def test_edge_tts_generates_audio(tmp_path):
    engine = EdgeTTSEngine(voice="en-US-ChristopherNeural")
    output = tmp_path / "test.mp3"
    result = await engine.synthesize("Hello world", output)
    assert result.exists()
    assert result.stat().st_size > 0
