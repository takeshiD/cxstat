from pathlib import Path
from typing import Annotated

import tiktoken
import typer
from rich.console import Console

from cxstat.cli.options import (
    CLAUDE_ROOT_OPTION,
    CODEX_ROOT_OPTION,
    DETAIL_OPTION,
    ENCODER_OPTION,
    JSON_OPTION,
    THEME_OPTION,
    TOP_OPTION,
    VERSION_OPTION,
)
from cxstat.logger import logger
from cxstat.models import UsageReport
from cxstat.service import load_report
from cxstat.theme import THEMES
from cxstat.utils import normalize_path
from cxstat.view import render_project_list, render_project_usage, render_summary

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
    *,
    version: bool = VERSION_OPTION,
    detail: bool = DETAIL_OPTION,
    top: int = TOP_OPTION,
    theme: str = THEME_OPTION,
    root_path: Path = CODEX_ROOT_OPTION,
    encoder: str = ENCODER_OPTION,
    json: bool = JSON_OPTION,
) -> None:
    if ctx.invoked_subcommand is None:
        ctx.params.pop("version")
        params = ctx.params.copy()
        codex(**params)


@app.command("codex", help="Analyze Codex tool and mcp token usage")
def codex(
    project_path: Annotated[Path | None, typer.Argument()] = None,
    *,
    detail: bool = DETAIL_OPTION,
    top: int = TOP_OPTION,
    theme: str = THEME_OPTION,
    root_path: Path = CODEX_ROOT_OPTION,
    encoder: str = ENCODER_OPTION,
    json: bool = JSON_OPTION,
) -> None:
    logger.debug(f"codex: path={project_path}")
    logger.debug(f"  --detail={detail}")
    logger.debug(f"  --top={top}")
    logger.debug(f"  --theme={theme}")
    logger.debug(f"  --root_path={root_path}")
    logger.debug(f"  --encoder={encoder}")
    logger.debug(f"  --json={json}")
    tiktoken_encoder = tiktoken.get_encoding(encoder)
    report: UsageReport = load_report(root_path.expanduser(), encoder=tiktoken_encoder)
    if json:
        if project_path is None:
            print(report.model_dump_json(indent=2))
        else:
            normalize_project_path = normalize_path(project_path)
            project_usage = report.projects.get(str(normalize_project_path))
            if project_usage is None or project_usage.totals.total_tokens == 0:
                console.print(
                    f"'{str(normalize_project_path)}' is not found in codex logs."
                )
                raise typer.Exit(1)
            print(project_usage.model_dump_json(indent=2))
    else:
        if project_path is None:
            render_summary(
                report, top_n=top, detail=detail, console=console, theme=THEMES[theme]
            )
        else:
            normalize_project_path = normalize_path(project_path)
            project_usage = report.projects.get(str(normalize_project_path))
            if project_usage is None or project_usage.totals.total_tokens == 0:
                console.print(
                    f"'{str(normalize_project_path)}' is not found in codex logs."
                )
                raise typer.Exit(1)
            render_project_usage(
                project_usage,
                top_n=top,
                detail=detail,
                console=console,
                theme=THEMES[theme],
            )


@app.command("claude", help="Analyze Claude Code tool and mcp token usage", hidden=True)
def claude(
    project_path: Annotated[Path | None, typer.Argument()] = None,
    *,
    detail: bool = DETAIL_OPTION,
    top: int = TOP_OPTION,
    theme: str = THEME_OPTION,
    root_path: Path = CLAUDE_ROOT_OPTION,
    json: bool = JSON_OPTION,
) -> None:
    logger.debug(f"claude: path={project_path}")
    logger.debug(f"  --detail={detail}")
    logger.debug(f"  --top={top}")
    logger.debug(f"  --theme={theme}")
    logger.debug(f"  --root_path={root_path}")
    logger.debug(f"  --json={json}")
    raise NotImplementedError("claude subcommand is not implemented yet")


@app.command("ls", help="List of project select codex or claude")
def list_project(
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
