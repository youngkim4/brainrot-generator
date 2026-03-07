"""Quiz JSON loader."""

import json
from pathlib import Path

from .quiz_config import QuizData, QuizType, TriviaQuestion, WYRQuestion


def load_quiz(path: Path) -> QuizData:
    """Parse and validate quiz JSON file."""
    if not path.exists():
        raise FileNotFoundError(f"Quiz file not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(raw, dict):
        raise ValueError("Quiz JSON must be an object")

    quiz_type_str = raw.get("type")
    if quiz_type_str not in ("trivia", "wyr"):
        raise ValueError(f"Invalid quiz type: {quiz_type_str!r}, must be 'trivia' or 'wyr'")

    raw_questions = raw.get("questions")
    if not isinstance(raw_questions, list) or not raw_questions:
        raise ValueError("Quiz must have a non-empty 'questions' array")

    quiz_type = QuizType(quiz_type_str)

    if quiz_type == QuizType.TRIVIA:
        questions = tuple(_parse_trivia(q, i) for i, q in enumerate(raw_questions))
    else:
        questions = tuple(_parse_wyr(q, i) for i, q in enumerate(raw_questions))

    return QuizData(quiz_type=quiz_type, questions=questions)


def _parse_trivia(raw: dict, index: int) -> TriviaQuestion:
    """Parse single trivia question."""
    if not isinstance(raw, dict):
        raise ValueError(f"Question {index}: must be an object")

    question = raw.get("question")
    if not question or not isinstance(question, str):
        raise ValueError(f"Question {index}: missing or invalid 'question' field")

    options = raw.get("options")
    if not isinstance(options, list) or len(options) < 2:
        raise ValueError(f"Question {index}: 'options' must be a list with at least 2 items")

    for i, opt in enumerate(options):
        if not isinstance(opt, str) or not opt.strip():
            raise ValueError(f"Question {index}, option {i}: must be a non-empty string")

    correct = raw.get("correct")
    if not isinstance(correct, int):
        raise ValueError(f"Question {index}: 'correct' must be an integer")

    time_limit = raw.get("time_limit", 7.0)
    if not isinstance(time_limit, (int, float)) or time_limit <= 0:
        raise ValueError(f"Question {index}: 'time_limit' must be a positive number")

    return TriviaQuestion(
        question=question,
        options=tuple(options),
        correct=correct,
        time_limit=float(time_limit),
    )


def _parse_wyr(raw: dict, index: int) -> WYRQuestion:
    """Parse single WYR question."""
    if not isinstance(raw, dict):
        raise ValueError(f"Question {index}: must be an object")

    option_a = raw.get("option_a")
    option_b = raw.get("option_b")

    if not option_a or not isinstance(option_a, str):
        raise ValueError(f"Question {index}: missing or invalid 'option_a'")
    if not option_b or not isinstance(option_b, str):
        raise ValueError(f"Question {index}: missing or invalid 'option_b'")

    time_limit = raw.get("time_limit", 6.0)
    if not isinstance(time_limit, (int, float)) or time_limit <= 0:
        raise ValueError(f"Question {index}: 'time_limit' must be a positive number")

    return WYRQuestion(
        option_a=option_a,
        option_b=option_b,
        time_limit=float(time_limit),
    )
