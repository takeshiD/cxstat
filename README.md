![](/docs/images/cxstat_logo.png)
# cxstat

Analytics Shell call and MCP call of token usage or Codex

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


### QuickStart
```bash
# use uvx
uvx cxstat

# show only specified project(example current directorry)
uvx cxstat ./

# show detail
uvx cxstat --detail

# show detail and top 20 tool calls
uvx cxstat --detail --top 20

# export json for tool usage
uvx cxstat --json

# filtering by jq
uvx cxstat --json | jq
```

## Usage

### Summarise all project tool token usage
collected under the default sessions root (`~/.codex/sessions`)

```bash
$ cxstat
                                    Token Usage by Tool

  #   Label                                     Total Tokens     Input      Output   Calls
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1   shell                                        1,939,531   494,773   1,444,758    3061
  2   serena__find_symbol                            165,339    10,439     154,900     411
  3   sequential-thinking__sequentialthinking         50,163    37,898      12,265     217
  4   serena__search_for_pattern                      38,790     5,331      33,459     210
  5   serena__activate_project                        28,935    20,413       8,522      42
  6   update_plan                                     24,910    24,544         366     183
  7   serena__get_symbols_overview                    23,186     1,613      21,573     116
  8   context7__resolve-library-id                    18,552        64      18,488       8
  9   serena__list_dir                                 9,804     1,456       8,348      91
 10   serena__replace_symbol_body                      9,696     9,554         142      24
```

Use flags such as `--detail` or `--top 10` when you want deeper tool or prompt rankings.

### Focus on a single project
You can view a summary focused on a specific project.

```bash
$ cxstat ~/path/to/project
Project: /home/your_name/path/to/project
Total tokens: 1,338,272 (input 354,260 / output 984,012) | calls 2821
Last invocation: 2025-10-05T21:52:15+09:00
                                   Token Usage by Tool

  #   Label                                     Total Tokens     Input    Output   Calls
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1   shell                                        1,116,967   299,797   817,170    1972
  2   serena__find_symbol                            104,009     6,948    97,061     278
  3   sequential-thinking__sequentialthinking         25,595    19,807     5,788     103
  4   serena__search_for_pattern                      22,200     3,428    18,772     145
  5   context7__resolve-library-id                    14,094        51    14,043       6
  6   serena__get_symbols_overview                    12,761       688    12,073      58
  7   update_plan                                     11,037    10,889       148      74
  8   serena__replace_symbol_body                      8,991     8,859       132      22
  9   context7__get-library-docs                       6,378        77     6,301       3
 10   serena__activate_project                         3,946       199     3,747      18
```

To see detailed information about shell commands, use the `--detail` option.

(e.g `cxstat /to/path --detail`)

## List your project with their aggregated totals:

```bash
$ cxstat list-project

                                            Token Usage by Project

  #   Project                                   Total Tokens    Input    Output   Calls   Last Invocation
 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  1   /home/your_name/ex_prog/ex_rust/typua       1,338,272   354,260   984,012    2821   2025-10-05T21:52:15+09:00
  2   /home/your_name/.codex                        176,235    30,857   145,378     234   2025-10-07T23:06:52+09:00
  3   /home/your_name/ex_prog/ex_py/cxstat          149,792    40,232   109,560     363   2025-10-08T15:28:09+09:00
  4   /home/your_name/ex_prog/ex_rust/typua_        127,974    32,115    95,859     196   2025-10-06T15:41:16+09:00
      check
  5   /home/your_name/ex_prog/ex_rust/apps/r        123,151    32,581    90,570     133   2025-09-28T17:41:37+09:00
      ust-analyzer
  6   /home/your_name/ex_prog/ex_py/tokstat         114,735    37,980    76,755     236   2025-10-08T00:55:14+09:00
  7   /home/your_name/ex_prog/ex_rust/toksta         81,571    16,738    64,833     135   2025-10-07T01:03:38+09:00
      t
  8   /home/your_name/.claude                        30,396     8,597    21,799      83   2025-10-06T16:01:13+09:00
  9   /home/your_name/ex_prog/ex_rust/mini-r         28,023    10,069    17,954      25   2025-10-06T14:53:26+09:00
      ua
 10   /home/your_name/ex_prog/ex_rust/ex_oct          8,630     3,686     4,944      36   2025-09-20T00:05:28+09:00
      ocrab
 11   /home/your_name/ex_prog/ex_chore                7,652     1,795     5,857       7   2025-09-18T14:49:40+09:00
 12   /home/your_name/zenn                            5,855       677     5,178       9   2025-10-08T18:31:17+09:00
```

The listing displays each project path, total/input/output token counts, call volume, and the most recent invocation timestamp.


## Options
The following options are available except for list-project:

- `--detail` / `-d`  include provider-level and top-call breakdown tables.
- `--top N`  limit table rows for each summary table.
- `--theme NAME` / `-t NAME` select the colour theme for table output
    - `dracura`(default)
    - `monokai`
    - `ayu`
    - `contrast`
    - `mono`
- `--version` / `-v` - show the installed cxstat version and exit.
- `--sessions-root PATH`  directory containing Codex CLI JSONL logs (defaults to `~/.codex/sessions`).


## Roadmap Status
- [ ] Sorting(by InputToken, OutputToken, Calls, LastInvocation)
- [ ] Customization of display table
- [ ] Detailed analysis shell commands(sed, python, node etc...)
- [ ] Export Data(Json, CSV)
- [ ] Support npm
- [ ] Support ClaudeCode
- [ ] CI/CD(docs, tests, publish for pypi)
