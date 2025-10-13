"""Utility functions for codex and claude"""

from pathlib import Path


def normalize_path(project: str | Path | None) -> str | None:
    """Return a normalised representation of a project path."""
    if project is None:
        return None
    try:
        candidate = Path(project).expanduser()
    except (TypeError, ValueError, RuntimeError):
        return str(project) if isinstance(project, str) else None
    try:
        resolved = candidate.resolve()
    except OSError:
        resolved = candidate
    return str(resolved)
