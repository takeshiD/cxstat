"""Rendering helpers using Rich for cxstat CLI output."""

from datetime import datetime

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from cxstat.models import Aggregate, ProjectUsage, UsageReport
from cxstat.theme import THEMES, CxStatTheme


def get_theme_names() -> tuple[str, ...]:
    """Return available theme identifiers for CLI option hints."""
    return tuple(sorted(THEMES))


def resolve_theme(name: str) -> CxStatTheme:
    """Return the colour palette for the requested theme name."""
    key = name.lower()
    try:
        return THEMES[key]
    except KeyError as exc:  # pragma: no cover - defensive branch
        available = ", ".join(get_theme_names())
        message = f"unknown theme '{name}'. Available themes: {available}"
        raise ValueError(message) from exc


def render_summary(
    report: UsageReport,
    *,
    top_n: int | None,
    detail: bool,
    console: Console | None = None,
    theme: CxStatTheme,
) -> None:
    """Render global aggregate tables for the provided usage report."""
    console = console or Console()

    if report.total_invocations == 0:
        console.print(
            Text(
                "No tool invocations found in the given sessions directory.",
                style=theme.warning_style,
            )
        )
        return

    if detail:
        analysed = Text(
            f"Analysed {report.total_invocations} tool invocations "
            f"({report.non_zero_invocations} with tokens).",
            style=theme.info_style,
        )
        console.print(analysed)
        totals = Text("Total tokens:", style=theme.accent_style)
        totals.append(f" {report.overall.total_tokens:,} ", style=theme.total_style)
        totals.append(
            (
                f"(input {report.overall.input_tokens:,} / "
                f"output {report.overall.output_tokens:,})."
            ),
            style=theme.info_style,
        )
        console.print(totals)

    render_aggregate_table(
        title="Token Usage by Tool",
        stats=report.tool_stats,
        console=console,
        top_n=top_n,
        highlight_tool=True,
        theme=theme,
    )

    if not detail:
        return

    render_aggregate_table(
        title="Token Usage by Provider",
        stats=report.provider_stats,
        console=console,
        top_n=top_n,
        theme=theme,
    )

    render_aggregate_table(
        title="Top Tool Calls",
        stats=report.detail_stats,
        console=console,
        top_n=top_n,
        theme=theme,
    )


def render_project_list(
    report: UsageReport,
    *,
    console: Console | None = None,
    theme: CxStatTheme,
) -> None:
    """Render a table of aggregated totals grouped by project path."""
    console = console or Console()
    rows = list(report.iter_projects())

    if not rows:
        console.print(
            Text("No projects with token usage found.", style=theme.warning_style)
        )
        return

    table = Table(
        title="Token Usage by Project",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style=theme.header_style,
        row_styles=theme.row_styles,
        pad_edge=False,
        padding=(0, 1),
    )
    table.add_column("#", justify="right", style=theme.accent_style)
    table.add_column("Project", overflow="fold", max_width=80, style=theme.label_style)
    table.add_column("Total Tokens", justify="right", style=theme.total_style)
    table.add_column("Input", justify="right", style=theme.input_style)
    table.add_column("Output", justify="right", style=theme.output_style)
    table.add_column("Calls", justify="right", style=theme.count_style)
    table.add_column("Last Invocation", justify="left", style=theme.label_style)

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


def render_project_usage(
    usage: ProjectUsage,
    *,
    console: Console | None = None,
    top_n: int | None = None,
    detail: bool,
    theme: CxStatTheme,
) -> None:
    """Render detailed token usage for a single project."""
    console = console or Console()

    if usage.totals.count == 0:
        console.print(
            Text(
                "No token usage found for the specified project.",
                style=theme.warning_style,
            )
        )
        return

    project_line = Text("Project:", style=theme.accent_style)
    project_line.append(f" {usage.project_path}", style=theme.label_style)
    console.print(project_line)

    totals_line = Text("Total tokens:", style=theme.accent_style)
    totals_line.append(f" {usage.totals.total_tokens:,} ", style=theme.total_style)
    totals_line.append(
        (
            f"(input {usage.totals.input_tokens:,} / "
            f"output {usage.totals.output_tokens:,})"
        ),
        style=theme.info_style,
    )
    totals_line.append(f" | calls {usage.totals.count}", style=theme.count_style)
    console.print(totals_line)
    if usage.last_invocation is not None:
        last_line = Text("Last invocation:", style=theme.accent_style)
        last_line.append(
            f" {format_timestamp(usage.last_invocation)}", style=theme.label_style
        )
        console.print(last_line)

    render_aggregate_table(
        title="Token Usage by Tool",
        stats=usage.tool_totals,
        console=console,
        top_n=top_n,
        highlight_tool=True,
        theme=theme,
    )

    if not detail:
        return

    render_aggregate_table(
        title="Token Usage by Provider",
        stats=usage.provider_totals,
        console=console,
        top_n=top_n,
        theme=theme,
    )

    render_aggregate_table(
        title="Top Tool Calls",
        stats=usage.detail_totals,
        console=console,
        top_n=top_n,
        theme=theme,
    )


def render_aggregate_table(
    *,
    title: str,
    stats: dict[str, Aggregate],
    console: Console,
    top_n: int | None,
    highlight_tool: bool = False,
    theme: CxStatTheme,
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
        console.print(Text(f"{title}: no data", style=theme.warning_style))
        return

    table = Table(
        title=title,
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style=theme.header_style,
        row_styles=theme.row_styles,
        pad_edge=False,
        padding=(0, 1),
    )
    table.add_column("#", justify="right", style=theme.accent_style)
    label_style = theme.highlight_label_style if highlight_tool else theme.label_style
    table.add_column("Label", style=label_style)
    table.add_column("Total Tokens", justify="right", style=theme.total_style)
    table.add_column("Input", justify="right", style=theme.input_style)
    table.add_column("Output", justify="right", style=theme.output_style)
    table.add_column("Calls", justify="right", style=theme.count_style)

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
