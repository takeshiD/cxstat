from pathlib import Path

import typer
from rich.console import Console

from cxstat import __version__
from cxstat.theme import AVAILABLE_THEMES


def _version_callback(value: bool | None):
    """Display the CLI version when the eager flag is provided."""
    if value:
        console = Console()
        console.print(f"v{__version__}")
        raise typer.Exit(0)


VERSION_OPTION = typer.Option(
    False,
    "--version",
    "-v",
    is_flag=True,
    is_eager=True,
    callback=_version_callback,
    help="Show cxstat version",
)

DETAIL_OPTION = typer.Option(
    False,
    "--detail",
    "-d",
    help="Display tool call detail",
)

THEME_OPTION = typer.Option(
    "dracura",
    "--theme",
    help=f"Select output colour theme. Available: {', '.join(AVAILABLE_THEMES)}.",
    show_default=True,
    case_sensitive=False,
)

CODEX_ROOT_OPTION = typer.Option(
    Path("~/.codex/sessions"),
    "--sessions-root",
    "-r",
    dir_okay=True,
    file_okay=False,
    readable=True,
    help="Root directory containing Codex logs.",
)

CLAUDE_ROOT_OPTION = typer.Option(
    Path("~/.claude/projects"),
    "--sessions-root",
    "-r",
    dir_okay=True,
    file_okay=False,
    readable=True,
    help="Root directory containing Claude logs.",
)

TOP_OPTION = typer.Option(
    10,
    "--top",
    help="Number of ranked rows to display when limiting tables.",
    min=1,
)

ENCODER_OPTION = typer.Option(
    "o200k_base",
    "--encoder",
    help="Tiktoken encoder.",
)

JSON_OPTION = typer.Option(
    False,
    "--json",
    "-j",
    help="Export report as json",
)
