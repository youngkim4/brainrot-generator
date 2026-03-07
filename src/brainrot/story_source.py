"""Story sourcing."""

from pathlib import Path


def load_story(source: str, allowed_dirs: list[Path] | None = None) -> str:
    """Load from string or file path. Checks allowed_dirs."""
    if len(source) > 255:
        return source.strip()
    path = Path(source)
    if path.exists() and path.is_file():
        resolved = path.resolve()
        if allowed_dirs is not None:
            if not any(resolved.is_relative_to(d.resolve()) for d in allowed_dirs):
                raise ValueError(
                    f"File {resolved} is outside allowed directories"
                )
        return resolved.read_text(encoding="utf-8").strip()
    return source.strip()
