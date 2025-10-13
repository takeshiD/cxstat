from pathlib import Path
from typing import Annotated

import tiktoken
import typer
from rich.console import Console

from cxstat.cli.options import (
    CLAUDE_ROOT_OPTION,
    CODEX_ROOT_OPTION,
    DETAIL_OPTION,
    THEME_OPTION,
    TOP_OPTION,
    VERSION_OPTION,
)
from cxstat.logger import logger
from cxstat.service import load_report
from cxstat.theme import THEMES
from cxstat.view import render_project_list, render_summary

logger = logger.getChild("cli")

console = Console()

app = typer.Typer(
    help="Analyze Codex CLI tool token usage.",
    add_completion=False,
    invoke_without_command=True,
    context_settings={"ignore_unknown_options": True},
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    project_path: Annotated[Path | None, typer.Argument()] = None,
    *,
    version: bool = VERSION_OPTION,
    detail: bool = DETAIL_OPTION,
    top: int = TOP_OPTION,
    theme: str = THEME_OPTION,
    root_path: Path = CODEX_ROOT_OPTION,
    encoder: str = "o200k_base",
) -> None:
    if ctx.invoked_subcommand is None:
        codex(
            ctx,
            project_path,
            detail=detail,
            top=top,
            theme=theme,
            root_path=root_path,
            encoder=encoder,
        )


@app.command("codex", help="Analyze Codex tool and mcp token usage")
def codex(
    ctx: typer.Context,
    project_path: Annotated[Path | None, typer.Argument()] = None,
    *,
    detail: bool = DETAIL_OPTION,
    top: int = TOP_OPTION,
    theme: str = THEME_OPTION,
    root_path: Path = CODEX_ROOT_OPTION,
    encoder: str = "o200k_base",
) -> None:
    logger.debug(f"codex: path={project_path}")
    logger.debug(f"  --detail={detail}")
    logger.debug(f"  --top={top}")
    logger.debug(f"  --root_path={root_path}")
    tiktoken_encoder = tiktoken.get_encoding(encoder)
    report = load_report(root_path.expanduser(), encoder=tiktoken_encoder)
    render_summary(
        report, top_n=top, detail=detail, console=console, theme=THEMES[theme]
    )


@app.command("claude", help="Analyze Claude Code tool and mcp token usage")
def claude(
    ctx: typer.Context,
    project_path: Annotated[Path | None, typer.Argument()] = None,
    *,
    detail: bool = DETAIL_OPTION,
    top: int = TOP_OPTION,
    theme: str = THEME_OPTION,
    root_path: Path = CLAUDE_ROOT_OPTION,
) -> None:
    logger.debug(f"claude: path={project_path}")
    logger.debug(f"  --detail={detail}")
    logger.debug(f"  --top={top}")
    logger.debug(f"  --root_path={root_path}")
    raise NotImplementedError("claude subcommand is not implemented yet")


@app.command("ls", help="List of project select codex or claude")
def list_project(
    ctx: typer.Context,
    codex_root: Path = CODEX_ROOT_OPTION,
    codex_encoder: str = "o200k_base",
    # claude_root: Path = CLAUDE_ROOT_OPTION,
    theme: str = THEME_OPTION,
):
    # codex
    encoder = tiktoken.get_encoding(codex_encoder)
    report = load_report(codex_root.expanduser(), encoder=encoder)
    render_project_list(report, console=console, theme=THEMES[theme])


def run():
    app()
