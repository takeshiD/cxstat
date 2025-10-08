"""Typer-based CLI entry point for cxstat."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import click
import typer
from rich.console import Console
from typer.main import get_command

from .service import canonicalize_project_path, get_package_version, load_report
from .view import (
    get_theme_names,
    render_project_list,
    render_project_usage,
    render_summary,
    resolve_theme,
)

if TYPE_CHECKING:
    from .models import UsageReport
    from .view import Theme

DEFAULT_SESSIONS_ROOT = Path.home() / ".codex" / "sessions"
_STATE_ERROR_MESSAGE = "Internal error: application state not initialised."

app = typer.Typer(
    help="Summarise Codex CLI tool token usage.",
    add_completion=False,
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True},
)


PROJECT_ARGUMENT = typer.Argument(
    None,
    metavar="PROJECT",
    help="Project directory to summarise. Defaults to all projects when omitted.",
)


def _version_callback(value: bool | None) -> bool:  # noqa: FBT001
    """Display the CLI version when the eager flag is provided."""
    if value:
        console = Console()
        console.print(get_package_version())
        raise typer.Exit()  # noqa: RSE102
    return bool(value)


DETAIL_OPTION = typer.Option(
    False,  # noqa: FBT003
    "--detail",
    "-d",
    is_flag=True,
    help="Display provider and top-call tables in addition to tool totals.",
)
AVAILABLE_THEMES = get_theme_names()
DEFAULT_THEME_NAME = "dracura" if "dracura" in AVAILABLE_THEMES else AVAILABLE_THEMES[0]
VERSION_OPTION = typer.Option(
    False,  # noqa: FBT003
    "--version",
    "-v",
    is_flag=True,
    is_eager=True,
    callback=_version_callback,
    help="Show cxstat version and exit.",
)
THEME_OPTION = typer.Option(
    DEFAULT_THEME_NAME,
    "--theme",
    "-t",
    help=f"Select output colour theme. Available: {', '.join(AVAILABLE_THEMES)}.",
    show_default=True,
    case_sensitive=False,
)

VERSION_FLAGS = {"--version", "-v"}
REORDERABLE_FLAGS = {"--detail", "-d", "--sessions-root", "-r", "--top", "--theme", "-t"} | VERSION_FLAGS
VALUE_FLAGS = {"--sessions-root", "-r", "--top", "--theme", "-t"}
DETAIL_FLAGS = {"--detail", "-d"}

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
TOP_OPTION = typer.Option(
    10,
    "--top",
    help="Number of ranked rows to display when limiting tables.",
    min=1,
    show_default=True,
)


@dataclass
class AppState:
    """Container for CLI-scoped state shared across commands."""

    sessions_root: Path
    top: int
    console: Console
    detail: bool
    theme_name: str
    theme: Theme
    project_path: str | None = None
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
            state.report = load_report(state.sessions_root)
        except FileNotFoundError as exc:  # pragma: no cover - user-facing branch
            state.console.print(f"[red]{exc}[/red]")
            raise typer.Exit(code=2) from exc
    return state.report


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    project: str | None = PROJECT_ARGUMENT,
    *,
    version: bool = VERSION_OPTION,
    detail: bool = DETAIL_OPTION,
    sessions_root: Path = SESSIONS_ROOT_OPTION,
    top: int = TOP_OPTION,
    theme: str = THEME_OPTION,
) -> None:
    """Initialise shared state and run the default command when appropriate."""
    resolved_root = sessions_root.expanduser()
    console = Console()
    try:
        theme_config = resolve_theme(theme)
    except ValueError as exc:  # pragma: no cover - defensive branch
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=2) from exc
    theme_name = theme.lower()
    if version:
        # The eager callback exits before this executes, but keep coverage safe.
        return

    ctx.obj = AppState(
        sessions_root=resolved_root,
        top=top,
        console=console,
        detail=detail,
        theme_name=theme_name,
        theme=theme_config,
        project_path=None,
    )
    state = get_state(ctx)

    if ctx.invoked_subcommand is None:
        tokens = []
        if project is not None:
            tokens.append(project)
        tokens.extend(ctx.args)
        if _handle_default_tokens(ctx, state, tokens):
            return
        summary(state)


def summary(state: AppState) -> None:
    """Render aggregated token usage, optionally filtered to a single project."""
    report = resolve_report(state)
    top_n = state.top
    target_project = state.project_path
    if target_project is None:
        render_summary(
            report,
            top_n=top_n,
            detail=state.detail,
            console=state.console,
            theme=state.theme,
        )
        return

    usage = report.projects.get(target_project)
    if usage is None or usage.totals.total_tokens == 0:
        state.console.print("project not found")
        raise typer.Exit(code=1)

    render_project_usage(
        usage,
        top_n=top_n,
        detail=state.detail,
        console=state.console,
        theme=state.theme,
    )


@app.command("list-project", help="List projects with their aggregated token usage.")
def list_project() -> None:
    """Display totals grouped by project path across all parsed sessions."""
    ctx = click.get_current_context()
    state = get_state(ctx)
    report = resolve_report(state)
    render_project_list(report, console=state.console, theme=state.theme)


def _collect_positional_tokens(state: AppState, tokens: list[str]) -> list[str]:
    """Return positional arguments after applying flag side effects."""
    positional: list[str] = []
    idx = 0
    while idx < len(tokens):
        token = tokens[idx]
        option_name, _, attached_value = token.partition("=")

        if option_name in DETAIL_FLAGS:
            state.detail = True
            idx += 1
            continue

        if option_name in VERSION_FLAGS:
            idx += 1
            continue

        if option_name in VALUE_FLAGS:
            idx += 1 if attached_value else 2
            continue

        if token.startswith("-"):
            idx += 1
            continue

        positional.append(token)
        idx += 1

    return positional


def _handle_default_tokens(
    ctx: click.Context,
    state: AppState,
    tokens: list[str],
) -> bool:
    """Process positional arguments for the default invocation.

    Returns True if a subcommand was explicitly invoked and executed.
    """
    if not tokens:
        return False

    positional = _collect_positional_tokens(state, tokens)
    if not positional:
        return False

    if len(positional) > 1:
        state.console.print("[red]Only one project path can be provided.[/red]")
        raise typer.Exit(code=2)

    project_candidate = positional[0]

    if isinstance(ctx.command, click.Group):
        command = ctx.command.get_command(ctx, project_candidate)
        if command is not None:
            ctx.invoke(command)
            return True

    canonical = canonicalize_project_path(project_candidate)
    if canonical is not None:
        state.project_path = canonical
    return False


def _normalize_args(raw_args: list[str]) -> list[str]:
    """Reorder CLI arguments so flags can appear after the project path."""
    if not raw_args:
        return raw_args

    first = raw_args[0]
    if first in {"list-project"}:
        return raw_args

    leading: list[str] = []
    trailing: list[str] = []
    idx = 0
    while idx < len(raw_args):
        token = raw_args[idx]
        option_name, _, attached_value = token.partition("=")

        if option_name in VALUE_FLAGS:
            if attached_value:
                leading.append(token)
                idx += 1
                continue
            if idx + 1 >= len(raw_args):
                trailing.append(token)
                idx += 1
                continue
            leading.extend([option_name, raw_args[idx + 1]])
            idx += 2
            continue
        if option_name in REORDERABLE_FLAGS:
            leading.append(token)
            idx += 1
            continue
        trailing.append(token)
        idx += 1

    return leading + trailing


def run() -> None:
    """CLI entry point used by the console script wrapper."""
    command = get_command(app)
    normalized_args = _normalize_args(sys.argv[1:])
    command.main(args=normalized_args, prog_name="cxstat")
