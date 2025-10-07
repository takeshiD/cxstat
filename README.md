# cxstat

Token usage analytics for Codex CLI sessions

## What cxstat?
- Visualize token usage for MCP and shell and more other tool call.
- Highlight the most expensive tools, prompts, and projects so you can tune workflows fast.

## Key Features
- **Rich-powered reports** - colourful tables for top tools, providers, and individual function calls.
- **Project breakdown** - aggregate counts per workspace, including the latest invocation timestamp.
- **Zero-noise defaults** - ignores empty invocations while keeping total call counts for context.

## Installation
cxstat targets Python 3.12+. Install from source with your preferred workflow:

```bash
# using uvx
uvx cxstat

# using uv
uv tool install cxstat

# or pip
pip install cxstat
```


## Quick Start
Analyse your Codex CLI history in seconds:

```bash
# default root is ~/.codex/sessions
cxstat

# customise the tokenizer and row limits
cxstat --top 10

# inspect usage grouped by project paths
cxstat list-project
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

## Options
All commands share these flags:
- `--sessions-root PATH` - directory containing Codex CLI JSONL logs (defaults to `~/.codex/sessions`).
- `--model NAME` - model hint used to resolve the tokenizer (e.g. `gpt-4o-mini`).
- `--encoding NAME` - explicit tiktoken encoding such as `cl100k_base`.
- `--top N` - limit table rows; combine with `--show-full` to disable truncation.


## Roadmap Status
- [ ] Additional groupings (agents, approval policy, latency buckets).
- [ ] Optional CSV/JSON export for dashboards.
- [ ] Snapshot comparisons between two time ranges.
