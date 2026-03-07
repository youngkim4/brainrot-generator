"""Tests for quiz compositor."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image

from brainrot.config import VideoConfig
from brainrot.quiz_config import (
    QuizData,
    QuizPipelineConfig,
    QuizType,
    TriviaQuestion,
    WYRQuestion,
)
from brainrot.quiz_compositor import (
    _compute_total_duration,
    _get_render_config,
    compose_quiz_video,
)


@pytest.fixture
def trivia_questions():
    return (
        TriviaQuestion(question="Q1?", options=("A", "B", "C"), correct=1, time_limit=7.0),
        TriviaQuestion(question="Q2?", options=("X", "Y"), correct=0, time_limit=5.0),
    )


@pytest.fixture
def wyr_questions():
    return (
        WYRQuestion(option_a="Fly", option_b="Invisible", time_limit=6.0),
    )


@pytest.fixture
def quiz_config(tmp_path, trivia_questions):
    data = QuizData(quiz_type=QuizType.TRIVIA, questions=trivia_questions)
    return QuizPipelineConfig(
        quiz_data=data,
        background_video=tmp_path / "bg.mp4",
        output_path=tmp_path / "out.mp4",
    )


class TestComputeTotalDuration:
    def test_two_trivia_questions(self, trivia_questions, quiz_config):
        total = _compute_total_duration(trivia_questions, quiz_config)
        # (7 + 1.5 + 0.3) + (5 + 1.5 + 0.3) = 8.8 + 6.8 = 15.6
        expected = (7.0 + 1.5 + 0.3) + (5.0 + 1.5 + 0.3)
        assert abs(total - expected) < 0.01

    def test_single_wyr(self, wyr_questions, tmp_path):
        data = QuizData(quiz_type=QuizType.WYR, questions=wyr_questions)
        config = QuizPipelineConfig(
            quiz_data=data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
        )
        total = _compute_total_duration(wyr_questions, config)
        expected = 6.0 + 1.5 + 0.3
        assert abs(total - expected) < 0.01


class TestGetRenderConfig:
    def test_normal_mode(self, quiz_config):
        rc = _get_render_config(quiz_config)
        assert rc.width == 1080
        assert rc.height == 1920

    def test_dev_mode(self, tmp_path, trivia_questions):
        data = QuizData(quiz_type=QuizType.TRIVIA, questions=trivia_questions)
        config = QuizPipelineConfig(
            quiz_data=data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
            dev_mode=True,
        )
        rc = _get_render_config(config)
        assert rc.width == 540
        assert rc.height == 960


class TestComposeQuizVideo:
    @patch("brainrot.quiz_compositor.VideoFileClip")
    @patch("brainrot.quiz_compositor.AudioFileClip")
    @patch("brainrot.quiz_compositor.CompositeVideoClip")
    @patch("brainrot.quiz_compositor.CompositeAudioClip")
    @patch("brainrot.quiz_compositor._crop_to_portrait")
    def test_calls_write_videofile(
        self,
        mock_crop,
        mock_composite_audio,
        mock_composite_video,
        mock_audio_clip,
        mock_video_clip,
        quiz_config,
        tmp_path,
    ):
        # setup mocks
        mock_bg = MagicMock()
        mock_bg.duration = 60.0
        mock_bg.size = (1920, 1080)
        mock_video_clip.return_value = mock_bg
        mock_bg.with_duration.return_value = mock_bg

        mock_crop.return_value = mock_bg

        mock_audio = MagicMock()
        mock_audio_clip.return_value = mock_audio
        mock_audio.with_start.return_value = mock_audio

        mock_final = MagicMock()
        mock_composite_video.return_value = mock_final
        mock_final.with_audio.return_value = mock_final
        mock_final.with_duration.return_value = mock_final

        audio_paths = [tmp_path / "q0.mp3", tmp_path / "q1.mp3"]
        for p in audio_paths:
            p.touch()

        compose_quiz_video(
            background_path=tmp_path / "bg.mp4",
            audio_paths=audio_paths,
            audio_durations=[3.0, 2.5],
            config=quiz_config,
        )

        mock_final.write_videofile.assert_called_once()

    @patch("brainrot.quiz_compositor.VideoFileClip")
    @patch("brainrot.quiz_compositor.AudioFileClip")
    @patch("brainrot.quiz_compositor.CompositeVideoClip")
    @patch("brainrot.quiz_compositor.CompositeAudioClip")
    @patch("brainrot.quiz_compositor._crop_to_portrait")
    def test_with_character_overlay(
        self,
        mock_crop,
        mock_composite_audio,
        mock_composite_video,
        mock_audio_clip,
        mock_video_clip,
        tmp_path,
    ):
        # create character image
        char_path = tmp_path / "char.png"
        char = Image.new("RGBA", (100, 150), (255, 0, 0, 255))
        char.save(char_path)

        q = TriviaQuestion(question="Q?", options=("A", "B"), correct=0, time_limit=5.0)
        data = QuizData(quiz_type=QuizType.TRIVIA, questions=(q,))
        config = QuizPipelineConfig(
            quiz_data=data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
            character_image=char_path,
        )

        mock_bg = MagicMock()
        mock_bg.duration = 60.0
        mock_bg.size = (1920, 1080)
        mock_video_clip.return_value = mock_bg
        mock_bg.with_duration.return_value = mock_bg
        mock_crop.return_value = mock_bg

        mock_audio = MagicMock()
        mock_audio_clip.return_value = mock_audio
        mock_audio.with_start.return_value = mock_audio

        mock_final = MagicMock()
        mock_composite_video.return_value = mock_final
        mock_final.with_audio.return_value = mock_final
        mock_final.with_duration.return_value = mock_final

        audio_path = tmp_path / "q0.mp3"
        audio_path.touch()

        compose_quiz_video(
            background_path=tmp_path / "bg.mp4",
            audio_paths=[audio_path],
            audio_durations=[2.0],
            config=config,
        )

        # verify CompositeVideoClip was called with character clip included
        call_args = mock_composite_video.call_args
        clips = call_args[0][0]
        # bg + character + question + countdown frames + reveal = more than 2
        assert len(clips) > 2
