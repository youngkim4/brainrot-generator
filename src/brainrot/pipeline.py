"""Pipeline orchestrator."""

import asyncio
import tempfile
from pathlib import Path

from .compositor import compose_video
from .config import PipelineConfig
from .story_source import load_story
from .timestamps import generate_timestamps, validate_timestamps
from .tts_engine import create_tts_engine


async def run_pipeline(config: PipelineConfig) -> Path:
    """Run full pipeline: story -> TTS -> timestamps -> video."""
    # story
    story = load_story(config.story_text)
    if not story:
        raise ValueError("Story text is empty")

    # tts
    engine = create_tts_engine(config)
    with tempfile.TemporaryDirectory() as tmp_dir:
        audio_path = Path(tmp_dir) / "narration.mp3"
        await engine.synthesize(story, audio_path)

        if not audio_path.exists() or audio_path.stat().st_size == 0:
            raise RuntimeError("TTS failed to generate audio")

        # timestamps
        words = generate_timestamps(audio_path)

        if not words:
            raise RuntimeError("No words detected in audio")

        from moviepy import AudioFileClip

        audio_clip = AudioFileClip(str(audio_path))
        audio_duration = audio_clip.duration
        audio_clip.close()

        if not validate_timestamps(words, audio_duration):
            raise RuntimeError(
                f"Timestamp drift exceeds threshold: last word ends at {words[-1].end:.2f}s, "
                f"audio is {audio_duration:.2f}s"
            )

        # composite
        output = compose_video(
            background_path=config.background_video,
            audio_path=audio_path,
            words=words,
            config=config,
        )

    return output


def run(config: PipelineConfig) -> Path:
    """Sync wrapper."""
    return asyncio.run(run_pipeline(config))
