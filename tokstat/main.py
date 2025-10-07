"""Legacy entry point for compatibility; forwards to the Typer app."""

from __future__ import annotations

from .cli import app


def main() -> None:
    """Invoke the Typer application."""
    app()


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    main()
