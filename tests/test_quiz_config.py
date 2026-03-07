"""Tests for quiz config dataclasses."""

import pytest

from brainrot.quiz_config import (
    QuizData,
    QuizPipelineConfig,
    QuizType,
    TriviaQuestion,
    WYRQuestion,
)


class TestQuizType:
    def test_trivia_value(self):
        assert QuizType.TRIVIA.value == "trivia"

    def test_wyr_value(self):
        assert QuizType.WYR.value == "wyr"

    def test_from_string(self):
        assert QuizType("trivia") == QuizType.TRIVIA
        assert QuizType("wyr") == QuizType.WYR


class TestTriviaQuestion:
    def test_valid(self):
        q = TriviaQuestion(
            question="Capital of France?",
            options=("Berlin", "Paris", "London"),
            correct=1,
            time_limit=7.0,
        )
        assert q.question == "Capital of France?"
        assert q.correct == 1
        assert len(q.options) == 3

    def test_frozen(self):
        q = TriviaQuestion(
            question="Q?",
            options=("A", "B"),
            correct=0,
        )
        with pytest.raises(AttributeError):
            q.question = "new"

    def test_invalid_correct_index(self):
        with pytest.raises(ValueError, match="out of range"):
            TriviaQuestion(question="Q?", options=("A", "B"), correct=5)

    def test_negative_correct_index(self):
        with pytest.raises(ValueError, match="out of range"):
            TriviaQuestion(question="Q?", options=("A", "B"), correct=-1)

    def test_empty_options(self):
        with pytest.raises(ValueError, match="empty"):
            TriviaQuestion(question="Q?", options=(), correct=0)

    def test_invalid_time_limit(self):
        with pytest.raises(ValueError, match="positive"):
            TriviaQuestion(question="Q?", options=("A", "B"), correct=0, time_limit=0)

    def test_default_time_limit(self):
        q = TriviaQuestion(question="Q?", options=("A", "B"), correct=0)
        assert q.time_limit == 7.0


class TestWYRQuestion:
    def test_valid(self):
        q = WYRQuestion(option_a="Fly", option_b="Invisible")
        assert q.option_a == "Fly"
        assert q.option_b == "Invisible"

    def test_frozen(self):
        q = WYRQuestion(option_a="A", option_b="B")
        with pytest.raises(AttributeError):
            q.option_a = "new"

    def test_empty_option_a(self):
        with pytest.raises(ValueError, match="required"):
            WYRQuestion(option_a="", option_b="B")

    def test_empty_option_b(self):
        with pytest.raises(ValueError, match="required"):
            WYRQuestion(option_a="A", option_b="")

    def test_default_time_limit(self):
        q = WYRQuestion(option_a="A", option_b="B")
        assert q.time_limit == 6.0

    def test_invalid_time_limit(self):
        with pytest.raises(ValueError, match="positive"):
            WYRQuestion(option_a="A", option_b="B", time_limit=0)

    def test_negative_time_limit(self):
        with pytest.raises(ValueError, match="positive"):
            WYRQuestion(option_a="A", option_b="B", time_limit=-3.0)


class TestQuizData:
    def test_valid_trivia(self):
        q = TriviaQuestion(question="Q?", options=("A", "B"), correct=0)
        data = QuizData(quiz_type=QuizType.TRIVIA, questions=(q,))
        assert data.quiz_type == QuizType.TRIVIA
        assert len(data.questions) == 1

    def test_empty_questions(self):
        with pytest.raises(ValueError, match="at least one"):
            QuizData(quiz_type=QuizType.TRIVIA, questions=())


class TestQuizPipelineConfig:
    def test_repr_masks_api_key(self, tmp_path):
        q = TriviaQuestion(question="Q?", options=("A", "B"), correct=0)
        data = QuizData(quiz_type=QuizType.TRIVIA, questions=(q,))
        config = QuizPipelineConfig(
            quiz_data=data,
            background_video=tmp_path / "bg.mp4",
            output_path=tmp_path / "out.mp4",
            elevenlabs_api_key="secret123",
        )
        r = repr(config)
        assert "secret123" not in r
        assert "***" in r
