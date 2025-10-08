![](/docs/images/cxstat_logo.png)
# cxstat

Token usage analytics for Codex CLI sessions

![](/docs/images/cxstat_no_args.png)

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

1. Summarise every project collected under the default sessions root (`~/.codex/sessions`):

   ```bash
   cxstat
   ```

   Use flags such as `--detail` or `--top 10` when you want deeper tool or prompt rankings.

2. Focus on a single project by passing its path (absolute or relative) as the positional argument:

   ```bash
   cxstat /path/to/project
   ```

   The summary switches to that project only and reuses your chosen options (e.g. `--detail`).

3. Review the project catalogue with their aggregated totals:

   ```bash
   cxstat list-project --top 10
   ```

   The listing displays each project path, total/input/output token counts, call volume, and the most recent invocation timestamp. Combine it with `--sessions-root` when your logs live outside the default directory.

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
- `--detail` / `-d` - include provider-level and top-call breakdown tables.
- `--top N` - limit table rows for each summary table.
- `--theme NAME` / `-t NAME` - select the colour theme for table output (available: `default`, `contrast`, `mono`, `monokai`, `dracura`, `ayu`; default is `dracura`).
- `--version` / `-v` - show the installed cxstat version and exit.


## Roadmap Status
- [ ] Additional groupings (agents, approval policy, latency buckets).
- [ ] Optional CSV/JSON export for dashboards.
- [ ] Snapshot comparisons between two time ranges.
