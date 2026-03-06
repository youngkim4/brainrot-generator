"""Pipeline orchestrator — runs all stages in sequence."""

import asyncio
import tempfile
from pathlib import Path

from .compositor import compose_video
from .config import PipelineConfig
from .story_source import load_story
from .timestamps import generate_timestamps, validate_timestamps
from .tts_engine import create_tts_engine


async def run_pipeline(config: PipelineConfig) -> Path:
    """Execute the full video generation pipeline.

    Stages:
        1. Load story text
        2. Generate TTS audio
        3. Extract word-level timestamps
        4. Composite video with captions
    """
    # 1. Story
    story = load_story(config.story_text)
    if not story:
        raise ValueError("Story text is empty")

    # 2. TTS
    engine = create_tts_engine(config)
    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = Path(tmp_dir) / "narration.mp3"
        await engine.synthesize(story, audio_path)

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("TTS failed to generate audio")

        # 3. Timestamps
        words = generate_timestamps(audio_path)

        if not words:
            raise RuntimeError("No words detected in audio")

        from moviepy import AudioFileClip

        audio_clip = AudioFileClip(str(audio_path))
        audio_duration = audio_clip.duration
        audio_clip.close()

        if not validate_timestamps(words, audio_duration):
            raise RuntimeError(
                f"Timestamp drift exceeds 0.5s: last word ends at {words[-1].end:.2f}s, "
                f"audio is {audio_duration:.2f}s"
            )

        # 4. Composite
        output = compose_video(
            background_path=config.background_video,
            audio_path=audio_path,
            words=words,
            config=config,
        )

    return output


def run(config: PipelineConfig) -> Path:
    """Synchronous wrapper for the pipeline."""
    return asyncio.run(run_pipeline(config))
