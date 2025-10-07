"""Typer-based CLI entry point for cxstat."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click
import typer
from rich.console import Console

from .service import load_report
from .view import render_project_list, render_summary

if TYPE_CHECKING:
    from .models import UsageReport

DEFAULT_SESSIONS_ROOT = Path.home() / ".codex" / "sessions"
_STATE_ERROR_MESSAGE = "Internal error: application state not initialised."

app = typer.Typer(
    help="Summarise Codex CLI tool token usage.",
    add_completion=False,
    invoke_without_command=True,
)


SESSIONS_ROOT_OPTION = typer.Option(
    DEFAULT_SESSIONS_ROOT,
    "--sessions-root",
    "-r",
    dir_okay=True,
    file_okay=False,
    readable=True,
    help="Root directory containing Codex session logs.",
    show_default=True,
)
MODEL_OPTION = typer.Option(
    "gpt-4o-mini",
    "--model",
    "-m",
    help="Model name used to select the tokenizer.",
    show_default=True,
)
ENCODING_OPTION = typer.Option(
    None,
    "--encoding",
    "-e",
    help="Override tokenizer encoding name (e.g. cl100k_base).",
)
TOP_OPTION = typer.Option(
    20,
    "--top",
    help="Number of ranked rows to display when limiting tables.",
    min=1,
    show_default=True,
)
SHOW_FULL_OPTION = typer.Option(
    False,  # noqa: FBT003
    "--show-full",
    is_flag=True,
    help="Display all rows instead of truncating to --top entries.",
)


@dataclass
class AppState:
    """Container for CLI-scoped state shared across commands."""

    sessions_root: Path
    model: str | None
    encoding: str | None
    top: int
    show_full: bool
    console: Console
    report: UsageReport | None = None


def get_state(ctx: click.Context) -> AppState:
    """Retrieve the application state from the Typer context."""
    state = ctx.obj
    if not isinstance(state, AppState):
        raise typer.Abort(_STATE_ERROR_MESSAGE)
    return state


def resolve_report(state: AppState) -> UsageReport:
    """Load and cache the aggregated usage report for the current invocation."""
    if state.report is None:
        try:
            state.report = load_report(state.sessions_root, state.model, state.encoding)
        except FileNotFoundError as exc:  # pragma: no cover - user-facing branch
            state.console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2) from exc
    return state.report


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    sessions_root: Path = SESSIONS_ROOT_OPTION,
    model: str = MODEL_OPTION,
    encoding: str | None = ENCODING_OPTION,
    top: int = TOP_OPTION,
    show_full: bool = SHOW_FULL_OPTION,  # noqa: FBT001
) -> None:
    """Initialise shared state and run the default command when appropriate."""
    resolved_root = sessions_root.expanduser()
    console = Console()
    ctx.obj = AppState(
        sessions_root=resolved_root,
        model=model,
        encoding=encoding,
        top=top,
        show_full=show_full,
        console=console,
    )

    if ctx.invoked_subcommand is None:
        ctx.invoke(summary)


@app.command(help="Show global token usage summary.")
def summary() -> None:
    """Render the aggregated token usage tables for all projects combined."""
    ctx = click.get_current_context()
    state = get_state(ctx)
    report = resolve_report(state)
    top_n = None if state.show_full else state.top
    render_summary(report, top_n=top_n, console=state.console)


@app.command("list-project", help="List projects with their aggregated token usage.")
def list_project() -> None:
    """Display totals grouped by project path across all parsed sessions."""
    ctx = click.get_current_context()
    state = get_state(ctx)
    report = resolve_report(state)
    render_project_list(report, console=state.console)
