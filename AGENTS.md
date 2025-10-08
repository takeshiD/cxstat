# cxstat Agent Design

## Overview
- Purpose: gather MCP and shell tool usage from Codex CLI session logs under `~/.codex/sessions` and expose user-friendly CLI reports.
- Success criteria: Typer-based command structure, Rich-formatted summaries, and project-wide plus per-project token statistics.
- Constraints: Python 3.12+, existing parsing utilities in `cxstat/main.py`, mandatory Pyright/Ruff validation in follow-up implementation.
- Quality gate: every coding iteration must run `uv run pyright` and `uv run ruff check` before changes are considered complete.

## CLI Architecture
- Replace the standalone `main()` argparse entry point with a Typer application (`cxstat/cli.py`).
- Root callback defines shared options (`--sessions-root`, `--top`, `--detail`, `--theme`).
- Commands:
  - `cxstat` (default action mapped to `summary`) prints global usage breakdown across all projects and tools.
  - `cxstat list-project` lists each project (derived from session path) with aggregated token totals and call counts.
- Packaging: update `pyproject.toml` script entry to `cxstat = "cxstat.cli:app"`; expose `app` from `cxstat/__init__.py`.

## Data Model & Aggregation
- Reuse `CallRecord` and `Aggregate` to capture per-invocation details and token metrics.
- Introduce structures:
  - `ProjectUsage`: project identifier plus per-tool `Aggregate` map.
  - `UsageReport`: overall totals, project summaries, and optional detailed rankings.
- Enhance `parse_logs` to emit project-aware records by inferring the project root from each log file path.
- Expand aggregation logic (`aggregate_usage`) to compute:
  - Global tool/provider/detail stats (existing functionality).
  - Per-project totals for shell vs MCP (extendable to other tools).

## Presentation Layer
- Build dedicated rendering helpers in `cxstat/view.py` (or similar) that accept aggregation results and produce Rich tables.
- Use `Console.print` with `Table` objects, configuring column alignment, styles, and optional zebra striping for readability.
- `summary` command: render counts of total tokens, input/output split, call volume, and top-N rankings (limit via `--top`, colour palette via `--theme`).
- `list-project` command: render project name/path, combined token totals, per-tool splits, and latest invocation timestamp (if available).
- Provide graceful empty-state messaging (`[yellow]No data found[/yellow]`) when logs are absent.

## Configuration & Dependencies
- Add `typer>=0.12` and `rich>=13` to `pyproject.toml` dependencies alongside existing `tiktoken` requirement.
- Keep tokenizer selection logic via `resolve_encoding`; default sessions root to `~/.codex/sessions`.
- Ensure modules remain ASCII by default; document future extension points (filters, additional providers).

## Verification Workflow
- After implementation, run `uv run pyright` and `uv run ruff check` to satisfy the mandatory static analysis policy.
- Create lightweight fixtures (sample JSONL logs) for smoke tests validating CLI outputs via `uv run cxstat --sessions-root fixtures`.
- Consider automated regression tests for aggregation helpers using pytest or snapshot comparisons.

## Rich Rendering Demo
```python
from rich.console import Console
from rich.table import Table
from rich import box

sample_data = [
    {"rank": 1, "tool": "mcp.tavily-search", "total": 18432, "input": 12321, "output": 6111, "count": 28},
    {"rank": 2, "tool": "shell", "total": 14220, "input": 9000, "output": 5220, "count": 35},
    {"rank": 3, "tool": "mcp.context7:get-library-docs", "total": 8230, "input": 5110, "output": 3120, "count": 12},
]

console = Console()
table = Table(
    title="Token Usage by Tool",
    box=box.SIMPLE_HEAVY,
    show_lines=True,
    header_style="bold cyan",
    row_styles=["none", "dim"],
)

table.add_column("#", justify="right", style="bold")
table.add_column("Tool", style="magenta")
table.add_column("Total Tokens", justify="right", style="green")
table.add_column("Input Tokens", justify="right")
table.add_column("Output Tokens", justify="right")
table.add_column("Calls", justify="right", style="yellow")

for row in sample_data:
    table.add_row(
        str(row["rank"]),
        row["tool"],
        f"{row['total']:,}",
        f"{row['input']:,}",
        f"{row['output']:,}",
        str(row["count"]),
    )

console.print(table)
```

```
                              Token Usage by Tool                               
                                                                                
  #   Tool                 Total Tokens   Input Tokens   Output Tokens   Calls  
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 
  1   mcp.tavily-search          18,432         12,321           6,111      28  
                                                                                
  2   shell                      14,220          9,000           5,220      35  
                                                                                
  3   mcp.context7:get-…          8,230          5,110           3,120      12  
                                                                                
```

## Next Steps
- Document tool classification rules (MCP vs shell vs others) for transparency.
- Scaffold new modules (`cli.py`, `service.py`, `view.py`) and migrate current logic incrementally.
- Prepare sample session data to validate Rich formatting in various terminal widths.
