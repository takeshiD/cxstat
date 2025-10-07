# tokstat

Token usage analytics for Codex CLI sessions, powered by Typer and Rich.

## Why tokstat?
- Transform raw MCP and shell call logs into an at-a-glance productivity dashboard.
- Highlight the most expensive tools, prompts, and projects so you can tune workflows fast.
- Ship with sensible defaults (tokenizer auto-detection, friendly tables) yet remain fully configurable.

## Key Features
- **Session aware parsing** - walks `~/.codex/sessions` (or any directory you point at) and understands project boundaries.
- **Rich-powered reports** - colourful tables for top tools, providers, and individual function calls.
- **Project breakdown** - aggregate counts per workspace, including the latest invocation timestamp.
- **Tokenizer flexibility** - auto-pick encodings from model names or override with `--encoding`.
- **Zero-noise defaults** - ignores empty invocations while keeping total call counts for context.

## Installation
tokstat targets Python 3.12+. Install from source with your preferred workflow:

```bash
# using uv
uvx tokstat

# or with pip
pip install tokstat
```

The CLI is exposed as the `tokstat` entry point via Typer.

## Quick Start
Analyse your Codex CLI history in seconds:

```bash
# default root is ~/.codex/sessions
tokstat

# customise the tokenizer and row limits
tokstat --model gpt-4o-mini --top 10

# inspect usage grouped by project paths
tokstat list-project --sessions-root /path/to/sessions
```

Sample summary output:

```
Analysed 128 tool invocations (96 with tokens).
Total tokens: 68,421 (input 41,230 / output 27,191).

Token Usage by Tool
#  Label                                 Total Tokens  Input   Output  Calls
1  mcp.tavily-search                             18432  12321     6111     28
2  shell                                         14220   9000     5220     35
3  mcp.context7:get-library-docs                  8230   5110     3120     12
```

The project listing offers similar insight per workspace:

```
Token Usage by Project
#  Project                               Total Tokens  Input   Output  Calls  Last Invocation
1  /home/user/work/acme-app                     19876   12980     6896     42  2025-07-18T14:02:33
2  /home/user/work/internal-tools               15220    9210     6010     31  2025-07-17T09:11:02
```

## How It Works
- `tokstat.service` handles log discovery, JSONL parsing, and token aggregation (global, provider, detail, project scopes).
- `tokstat.models` defines lightweight dataclasses (`CallRecord`, `Aggregate`, `ProjectUsage`, `UsageReport`).
- `tokstat.view` renders Rich tables with zebra-striping, highlights, and friendly fallbacks when data is missing.
- `tokstat.cli` wires everything together with Typer, managing shared CLI state and commands.

## Configuration Options
All commands share these flags:
- `--sessions-root PATH` - directory containing Codex CLI JSONL logs (defaults to `~/.codex/sessions`).
- `--model NAME` - model hint used to resolve the tokenizer (e.g. `gpt-4o-mini`).
- `--encoding NAME` - explicit tiktoken encoding such as `cl100k_base`.
- `--top N` - limit table rows; combine with `--show-full` to disable truncation.

## Development Workflow
```bash
uv run pyright
uv run ruff check
uv run tokstat --sessions-root fixtures
```

- Type-check with Pyright and lint with Ruff before committing.
- Rich fixtures under `fixtures/` (add your own JSONL samples) keep regression checks fast.
- Contributions are welcome; please open an issue or PR with a short summary of the scenario you want to analyse.

## Roadmap Ideas
- Additional groupings (agents, approval policy, latency buckets).
- Optional CSV/JSON export for dashboards.
- Snapshot comparisons between two time ranges.

---
Made with care to help Codex power users understand where their tokens go.
