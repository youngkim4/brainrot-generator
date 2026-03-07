"""Tests for quiz JSON loader."""

import json

import pytest

from brainrot.quiz_config import QuizType, TriviaQuestion, WYRQuestion
from brainrot.quiz_loader import load_quiz


@pytest.fixture
def trivia_json(tmp_path):
    data = {
        "type": "trivia",
        "questions": [
            {
                "question": "Capital of France?",
                "options": ["Berlin", "Paris", "London", "Madrid"],
                "correct": 1,
                "time_limit": 7,
            }
        ],
    }
    path = tmp_path / "trivia.json"
    path.write_text(json.dumps(data))
    return path


@pytest.fixture
def wyr_json(tmp_path):
    data = {
        "type": "wyr",
        "questions": [
            {
                "option_a": "Have unlimited money",
                "option_b": "Have unlimited time",
                "time_limit": 6,
            }
        ],
    }
    path = tmp_path / "wyr.json"
    path.write_text(json.dumps(data))
    return path


class TestLoadTrivia:
    def test_valid(self, trivia_json):
        result = load_quiz(trivia_json)
        assert result.quiz_type == QuizType.TRIVIA
        assert len(result.questions) == 1
        q = result.questions[0]
        assert isinstance(q, TriviaQuestion)
        assert q.question == "Capital of France?"
        assert q.correct == 1
        assert q.options == ("Berlin", "Paris", "London", "Madrid")

    def test_default_time_limit(self, tmp_path):
        data = {
            "type": "trivia",
            "questions": [
                {"question": "Q?", "options": ["A", "B"], "correct": 0}
            ],
        }
        path = tmp_path / "q.json"
        path.write_text(json.dumps(data))
        result = load_quiz(path)
        assert result.questions[0].time_limit == 7.0


class TestLoadWYR:
    def test_valid(self, wyr_json):
        result = load_quiz(wyr_json)
        assert result.quiz_type == QuizType.WYR
        assert len(result.questions) == 1
        q = result.questions[0]
        assert isinstance(q, WYRQuestion)
        assert q.option_a == "Have unlimited money"


class TestLoadErrors:
    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_quiz(tmp_path / "missing.json")

    def test_invalid_type(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"type": "invalid", "questions": []}))
        with pytest.raises(ValueError, match="Invalid quiz type"):
            load_quiz(path)

    def test_empty_questions(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text(json.dumps({"type": "trivia", "questions": []}))
        with pytest.raises(ValueError, match="non-empty"):
            load_quiz(path)

    def test_not_object(self, tmp_path):
        path = tmp_path / "arr.json"
        path.write_text(json.dumps([1, 2, 3]))
        with pytest.raises(ValueError, match="must be an object"):
            load_quiz(path)

    def test_missing_question_field(self, tmp_path):
        data = {
            "type": "trivia",
            "questions": [{"options": ["A", "B"], "correct": 0}],
        }
        path = tmp_path / "q.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="missing or invalid 'question'"):
            load_quiz(path)

    def test_correct_out_of_bounds(self, tmp_path):
        data = {
            "type": "trivia",
            "questions": [
                {"question": "Q?", "options": ["A", "B"], "correct": 5}
            ],
        }
        path = tmp_path / "q.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="out of range"):
            load_quiz(path)

    def test_too_few_options(self, tmp_path):
        data = {
            "type": "trivia",
            "questions": [
                {"question": "Q?", "options": ["A"], "correct": 0}
            ],
        }
        path = tmp_path / "q.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="at least 2"):
            load_quiz(path)

    def test_wyr_missing_option_b(self, tmp_path):
        data = {
            "type": "wyr",
            "questions": [{"option_a": "A"}],
        }
        path = tmp_path / "q.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="missing or invalid 'option_b'"):
            load_quiz(path)

    def test_wyr_missing_option_a(self, tmp_path):
        data = {
            "type": "wyr",
            "questions": [{"option_b": "B"}],
        }
        path = tmp_path / "q.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="missing or invalid 'option_a'"):
            load_quiz(path)

    def test_negative_time_limit(self, tmp_path):
        data = {
            "type": "trivia",
            "questions": [
                {"question": "Q?", "options": ["A", "B"], "correct": 0, "time_limit": -1}
            ],
        }
        path = tmp_path / "q.json"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match="positive"):
            load_quiz(path)
