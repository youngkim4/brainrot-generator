"""Tests for story source module."""

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
