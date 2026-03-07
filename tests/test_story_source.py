"""Story source tests."""

import pytest

from brainrot.story_source import load_story


def test_load_story_from_string():
    result = load_story("A dark hallway stretched before me.")
    assert result == "A dark hallway stretched before me."


def test_load_story_strips_whitespace():
    result = load_story("  hello world  \n")
    assert result == "hello world"


def test_load_story_from_file(tmp_path):
    story_file = tmp_path / "story.txt"
    story_file.write_text("The door creaked open.")
    result = load_story(str(story_file))
    assert result == "The door creaked open."


def test_load_story_nonexistent_path_treated_as_text():
    result = load_story("/nonexistent/path/story.txt")
    assert result == "/nonexistent/path/story.txt"


def test_load_story_rejects_path_outside_allowed_dirs(tmp_path):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("secret data")

    with pytest.raises(ValueError, match="outside allowed directories"):
        load_story(str(secret), allowed_dirs=[allowed])


def test_load_story_allows_path_inside_allowed_dirs(tmp_path):
    allowed = tmp_path / "stories"
    allowed.mkdir()
    story_file = allowed / "tale.txt"
    story_file.write_text("Once upon a time.")

    result = load_story(str(story_file), allowed_dirs=[allowed])
    assert result == "Once upon a time."
