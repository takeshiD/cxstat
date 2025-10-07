"""Rendering helpers using Rich for cxstat CLI output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich import box
from rich.console import Console
from rich.table import Table

if TYPE_CHECKING:
    from datetime import datetime

    from .models import Aggregate, UsageReport


def render_summary(
    report: UsageReport,
    *,
    top_n: int | None,
    console: Console | None = None,
) -> None:
    """Render global aggregate tables for the provided usage report."""
    console = console or Console()

    if report.total_invocations == 0:
        console.print("[yellow]No tool invocations found in the given sessions directory.[/yellow]")
        return

    console.print(
        f"[bold]Analysed[/bold] {report.total_invocations} tool invocations "
        f"([green]{report.non_zero_invocations} with tokens[/green]).",
    )
    console.print(
        f"[bold]Total tokens:[/bold] {report.overall.total_tokens:,} "
        f"(input {report.overall.input_tokens:,} / output {report.overall.output_tokens:,}).",
    )

    render_aggregate_table(
        title="Token Usage by Tool",
        stats=report.tool_stats,
        console=console,
        top_n=top_n,
        highlight_tool=True,
    )

    render_aggregate_table(
        title="Token Usage by Provider",
        stats=report.provider_stats,
        console=console,
        top_n=top_n,
    )

    render_aggregate_table(
        title="Top Tool Calls",
        stats=report.detail_stats,
        console=console,
        top_n=top_n,
    )


def render_project_list(
    report: UsageReport,
    *,
    console: Console | None = None,
) -> None:
    """Render a table of aggregated totals grouped by project path."""
    console = console or Console()
    rows = list(report.iter_projects())

    if not rows:
        console.print("[yellow]No projects with token usage found.[/yellow]")
        return

    table = Table(
        title="Token Usage by Project",
        box=box.SIMPLE_HEAVY,
        show_lines=True,
        header_style="bold cyan",
        row_styles=["none", "dim"],
    )
    table.add_column("#", justify="right", style="bold")
    table.add_column("Project", overflow="fold", max_width=80)
    table.add_column("Total Tokens", justify="right", style="green")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Calls", justify="right", style="yellow")
    table.add_column("Last Invocation", justify="left")

    for index, usage in enumerate(rows, start=1):
        table.add_row(
            str(index),
            usage.project_path,
            f"{usage.totals.total_tokens:,}",
            f"{usage.totals.input_tokens:,}",
            f"{usage.totals.output_tokens:,}",
            str(usage.totals.count),
            format_timestamp(usage.last_invocation),
        )

    console.print(table)


def render_aggregate_table(
    *,
    title: str,
    stats: dict[str, Aggregate],
    console: Console,
    top_n: int | None,
    highlight_tool: bool = False,
) -> None:
    """Render a generic aggregate table sorted by total tokens."""
    items = sorted(
        ((key, value) for key, value in stats.items() if value.total_tokens > 0),
        key=lambda item: (item[1].total_tokens, item[0]),
        reverse=True,
    )

    if top_n is not None:
        items = items[:top_n]

    if not items:
        console.print(f"[yellow]{title}: no data[/yellow]")
        return

    table = Table(
        title=title,
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style="bold cyan",
        row_styles=["none", "dim"],
        pad_edge=False,
        padding=(0, 1),
    )
    table.add_column("#", justify="right", style="bold")
    table.add_column("Label", style="magenta" if highlight_tool else "white")
    table.add_column("Total Tokens", justify="right", style="green")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Calls", justify="right", style="yellow")

    for index, (label, aggregate) in enumerate(items, start=1):
        table.add_row(
            str(index),
            label,
            f"{aggregate.total_tokens:,}",
            f"{aggregate.input_tokens:,}",
            f"{aggregate.output_tokens:,}",
            str(aggregate.count),
        )

    console.print(table)


def format_timestamp(value: datetime | None) -> str:
    """Format a timestamp for table display, using local time when possible."""
    if value is None:
        return "—"
    dt = value.replace(microsecond=0)
    if dt.tzinfo is None:
        return dt.isoformat()
    return dt.astimezone().isoformat()
