"""Story sourcing — manual text input or file reading."""

from pathlib import Path


def load_story(source: str) -> str:
    """Load story text from a string or file path.

    If source is a path to an existing file, reads its contents.
    Otherwise, treats source as the story text directly.
    """
    path = Path(source)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return source.strip()
