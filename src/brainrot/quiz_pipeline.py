"""Quiz pipeline orchestrator."""

import asyncio
import tempfile
from pathlib import Path

from moviepy import AudioFileClip

from .config import TTSProvider
from .quiz_compositor import compose_quiz_video
from .quiz_config import QuizPipelineConfig, TriviaQuestion, WYRQuestion
from .tts_engine import EdgeTTSEngine, ElevenLabsTTSEngine, TTSEngine


def _create_quiz_tts_engine(config: QuizPipelineConfig) -> TTSEngine:
    """Build TTS engine from quiz config."""
    if config.tts_provider == TTSProvider.ELEVENLABS:
        if not config.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key required. Set ELEVENLABS_API_KEY env var.")
        if not config.elevenlabs_voice_id:
            raise ValueError("ElevenLabs voice ID required.")
        return ElevenLabsTTSEngine(
            config.elevenlabs_api_key,
            config.elevenlabs_voice_id,
            config.elevenlabs_model_id,
        )
    return EdgeTTSEngine(config.tts_voice)


def _question_to_tts_text(question: TriviaQuestion | WYRQuestion) -> str:
    """Convert question to spoken text."""
    if isinstance(question, TriviaQuestion):
        options_text = ", ".join(
            f"{chr(65 + i)}: {opt}" for i, opt in enumerate(question.options)
        )
        return f"{question.question}. {options_text}"
    return f"Would you rather {question.option_a}, or {question.option_b}?"


async def run_quiz_pipeline(config: QuizPipelineConfig) -> Path:
    """Run quiz pipeline: load quiz -> TTS per question -> compose."""
    engine = _create_quiz_tts_engine(config)
    questions = config.quiz_data.questions

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        audio_paths: list[Path] = []
        audio_durations: list[float] = []

        # generate TTS for each question
        for i, question in enumerate(questions):
            tts_text = _question_to_tts_text(question)
            audio_path = tmp / f"question_{i}.mp3"
            await engine.synthesize(tts_text, audio_path)

            if not audio_path.exists() or audio_path.stat().st_size == 0:
                raise RuntimeError(f"TTS failed for question {i}")

            # get duration
            clip = AudioFileClip(str(audio_path))
            try:
                audio_durations.append(clip.duration)
            finally:
                clip.close()

            audio_paths.append(audio_path)

        # validate TTS durations fit within time limits
        for i, question in enumerate(questions):
            if audio_durations[i] > question.time_limit:
                raise RuntimeError(
                    f"Question {i} TTS duration ({audio_durations[i]:.1f}s) "
                    f"exceeds time_limit ({question.time_limit}s)"
                )

        output = compose_quiz_video(
            background_path=config.background_video,
            audio_paths=audio_paths,
            audio_durations=audio_durations,
            config=config,
        )

    return output


def run_quiz(config: QuizPipelineConfig) -> Path:
    """Sync wrapper."""
    return asyncio.run(run_quiz_pipeline(config))
