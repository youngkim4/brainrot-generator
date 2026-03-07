"""Tests for quiz pipeline."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from brainrot.config import TTSProvider
from brainrot.quiz_config import (
    QuizData,
    QuizPipelineConfig,
    QuizType,
    TriviaQuestion,
    WYRQuestion,
)
from brainrot.quiz_pipeline import (
    _create_quiz_tts_engine,
    _question_to_tts_text,
    run_quiz,
    run_quiz_pipeline,
)
from brainrot.tts_engine import EdgeTTSEngine, ElevenLabsTTSEngine


@pytest.fixture
def trivia_data():
    q = TriviaQuestion(
        question="Capital of France?",
        options=("Berlin", "Paris", "London"),
        correct=1,
        time_limit=7.0,
    )
    return QuizData(quiz_type=QuizType.TRIVIA, questions=(q,))


@pytest.fixture
def wyr_data():
    q = WYRQuestion(option_a="Fly", option_b="Invisible", time_limit=6.0)
    return QuizData(quiz_type=QuizType.WYR, questions=(q,))


def _make_fake_synthesize(write_data: bytes = b"fake audio data"):
    """Shared fake TTS synthesize function."""
    async def fake_synthesize(text, path):
        if write_data:
            path.write_bytes(write_data)
        return path
    return fake_synthesize


class TestCreateTTSEngine:
    def test_edge_default(self, trivia_data, tmp_path):
        config = QuizPipelineConfig(
            quiz_data=trivia_data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
        )
        engine = _create_quiz_tts_engine(config)
        assert isinstance(engine, EdgeTTSEngine)

    def test_elevenlabs(self, trivia_data, tmp_path):
        config = QuizPipelineConfig(
            quiz_data=trivia_data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
            tts_provider=TTSProvider.ELEVENLABS,
            elevenlabs_api_key="key",
            elevenlabs_voice_id="voice",
        )
        engine = _create_quiz_tts_engine(config)
        assert isinstance(engine, ElevenLabsTTSEngine)

    def test_elevenlabs_missing_key(self, trivia_data, tmp_path):
        config = QuizPipelineConfig(
            quiz_data=trivia_data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
            tts_provider=TTSProvider.ELEVENLABS,
        )
        with pytest.raises(ValueError, match="API key"):
            _create_quiz_tts_engine(config)

    def test_elevenlabs_missing_voice_id(self, trivia_data, tmp_path):
        config = QuizPipelineConfig(
            quiz_data=trivia_data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
            tts_provider=TTSProvider.ELEVENLABS,
            elevenlabs_api_key="key",
            elevenlabs_voice_id="",
        )
        with pytest.raises(ValueError, match="voice ID"):
            _create_quiz_tts_engine(config)


class TestQuestionToTTSText:
    def test_trivia(self):
        q = TriviaQuestion(question="Q?", options=("A", "B", "C"), correct=1)
        text = _question_to_tts_text(q)
        assert "Q?" in text
        assert "A: A" in text
        assert "B: B" in text
        assert "C: C" in text

    def test_wyr(self):
        q = WYRQuestion(option_a="Fly", option_b="Invisible")
        text = _question_to_tts_text(q)
        assert "Would you rather" in text
        assert "Fly" in text
        assert "Invisible" in text


class TestRunQuizPipeline:
    @pytest.mark.asyncio
    @patch("brainrot.quiz_pipeline.compose_quiz_video")
    @patch("brainrot.quiz_pipeline.AudioFileClip")
    async def test_full_flow_mocked(self, mock_audio_clip, mock_compose, trivia_data, tmp_path):
        mock_engine = AsyncMock()
        mock_engine.synthesize = _make_fake_synthesize()

        mock_clip = MagicMock()
        mock_clip.duration = 3.0
        mock_audio_clip.return_value = mock_clip

        output_path = tmp_path / "out.mp4"
        mock_compose.return_value = output_path

        config = QuizPipelineConfig(
            quiz_data=trivia_data,
            background_video=tmp_path / "bg.mp4",
            output_path=output_path,
        )

        with patch("brainrot.quiz_pipeline._create_quiz_tts_engine", return_value=mock_engine):
            result = await run_quiz_pipeline(config)

        assert result == output_path
        mock_compose.assert_called_once()
        # verify AudioFileClip was closed for each question
        assert mock_clip.close.call_count == len(trivia_data.questions)

    @pytest.mark.asyncio
    @patch("brainrot.quiz_pipeline.compose_quiz_video")
    @patch("brainrot.quiz_pipeline.AudioFileClip")
    async def test_tts_exceeds_time_limit(self, mock_audio_clip, mock_compose, tmp_path):
        q = TriviaQuestion(question="Q?", options=("A", "B"), correct=0, time_limit=2.0)
        data = QuizData(quiz_type=QuizType.TRIVIA, questions=(q,))

        mock_engine = AsyncMock()
        mock_engine.synthesize = _make_fake_synthesize()

        mock_clip = MagicMock()
        mock_clip.duration = 5.0
        mock_audio_clip.return_value = mock_clip

        config = QuizPipelineConfig(
            quiz_data=data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
        )

        with patch("brainrot.quiz_pipeline._create_quiz_tts_engine", return_value=mock_engine):
            with pytest.raises(RuntimeError, match="exceeds time_limit"):
                await run_quiz_pipeline(config)

    @pytest.mark.asyncio
    async def test_tts_fails_no_file(self, tmp_path):
        q = TriviaQuestion(question="Q?", options=("A", "B"), correct=0)
        data = QuizData(quiz_type=QuizType.TRIVIA, questions=(q,))

        mock_engine = AsyncMock()

        async def no_file_synthesize(text, path):
            return path

        mock_engine.synthesize = no_file_synthesize

        config = QuizPipelineConfig(
            quiz_data=data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
        )

        with patch("brainrot.quiz_pipeline._create_quiz_tts_engine", return_value=mock_engine):
            with pytest.raises(RuntimeError, match="TTS failed"):
                await run_quiz_pipeline(config)

    @pytest.mark.asyncio
    async def test_tts_fails_zero_byte_file(self, tmp_path):
        q = TriviaQuestion(question="Q?", options=("A", "B"), correct=0)
        data = QuizData(quiz_type=QuizType.TRIVIA, questions=(q,))

        mock_engine = AsyncMock()

        async def zero_byte_synthesize(text, path):
            path.touch()  # creates empty file
            return path

        mock_engine.synthesize = zero_byte_synthesize

        config = QuizPipelineConfig(
            quiz_data=data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
        )

        with patch("brainrot.quiz_pipeline._create_quiz_tts_engine", return_value=mock_engine):
            with pytest.raises(RuntimeError, match="TTS failed"):
                await run_quiz_pipeline(config)


class TestRunQuizSync:
    @patch("brainrot.quiz_pipeline.run_quiz_pipeline")
    def test_run_quiz_calls_async(self, mock_pipeline, trivia_data, tmp_path):
        output_path = tmp_path / "out.mp4"
        mock_pipeline.return_value = output_path

        config = QuizPipelineConfig(
            quiz_data=trivia_data,
            background_video=tmp_path / "bg.mp4",
            output_path=output_path,
        )

        result = run_quiz(config)
        assert result == output_path
