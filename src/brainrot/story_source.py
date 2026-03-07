"""Story sourcing."""

from pathlib import Path

_MAX_STORY_LENGTH = 50_000  # chars
_DEFAULT_ALLOWED_DIRS = [Path("."), Path("assets"), Path("stories")]


def load_story(
    source: str,
    allowed_dirs: list[Path] | None = None,
) -> str:
    """Load from string or file path. Always enforces directory restrictions."""
    if len(source) > 255:
        text = source.strip()
        if len(text) > _MAX_STORY_LENGTH:
            raise ValueError(f"Story exceeds {_MAX_STORY_LENGTH} char limit")
        return text

    path = Path(source)
    if path.exists() and path.is_file():
        resolved = path.resolve()
        dirs = allowed_dirs if allowed_dirs is not None else _DEFAULT_ALLOWED_DIRS
        if not any(resolved.is_relative_to(d.resolve()) for d in dirs):
            raise ValueError(
                f"File {resolved} is outside allowed directories: {dirs}"
            )
        text = resolved.read_text(encoding="utf-8").strip()
        if len(text) > _MAX_STORY_LENGTH:
            raise ValueError(f"Story exceeds {_MAX_STORY_LENGTH} char limit")
        return text

    text = source.strip()
    if len(text) > _MAX_STORY_LENGTH:
        raise ValueError(f"Story exceeds {_MAX_STORY_LENGTH} char limit")
    return text
