"""Collect tool invocation token usage from Codex CLI session logs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import tiktoken


@dataclass
class CallRecord:
    name: str
    arguments_raw: str | None = None
    arguments_obj: Any | None = None
    output_raw: str | None = None
    output_obj: Any | None = None
    file_path: Path | None = None
    line_no: int | None = None


@dataclass
class Aggregate:
    count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, inp: int, out: int) -> None:
        self.count += 1
        self.input_tokens += inp
        self.output_tokens += out

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


def resolve_encoding(model: Optional[str], encoding_name: Optional[str]):
    if encoding_name:
        return tiktoken.get_encoding(encoding_name)
    if model:
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            pass
    return tiktoken.get_encoding("cl100k_base")


def safe_json_loads(text: Optional[str]) -> Any:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def iter_session_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        raise FileNotFoundError(f"sessions directory not found: {root}")
    for path in sorted(root.rglob("*.jsonl")):
        if path.is_file():
            yield path


def format_shell_command(args_obj: Any) -> str:
    if not isinstance(args_obj, dict):
        return "<unknown shell command>"
    cmd = args_obj.get("command")
    if isinstance(cmd, list):
        return "shell | " + " ".join(str(part) for part in cmd)
    if isinstance(cmd, str):
        return "shell | " + cmd
    return "shell | <unknown>"


def summarize_args(name: str, args_obj: Any, max_len: int = 120) -> str:
    if args_obj is None:
        return name
    try:
        serialized = json.dumps(args_obj, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        serialized = str(args_obj)
    if len(serialized) > max_len:
        serialized = serialized[: max_len - 3] + "..."
    return f"{name} | {serialized}" if serialized else name


def build_detail_key(record: CallRecord) -> str:
    if record.name == "shell":
        return format_shell_command(record.arguments_obj)
    return summarize_args(record.name, record.arguments_obj)


def build_tool_key(record: CallRecord) -> str:
    return record.name or "<unknown>"


def build_provider_key(record: CallRecord) -> str:
    name = record.name or "<unknown>"
    if "__" in name:
        return name.split("__", 1)[0]
    return name


def count_tokens(text: Optional[str], encoder) -> int:
    if not text:
        return 0
    return len(encoder.encode(text))


def parse_logs(root: Path) -> Dict[str, CallRecord]:
    calls: Dict[str, CallRecord] = {}
    for path in iter_session_files(root):
        with path.open("r", encoding="utf-8") as handle:
            for idx, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                entry = json.loads(line)
                entry_type = entry.get("type")
                if entry_type == "function_call":
                    call_id = entry.get("call_id")
                    if not call_id:
                        continue
                    arguments_raw = entry.get("arguments")
                    record = CallRecord(
                        name=entry.get("name", "<unknown>"),
                        arguments_raw=arguments_raw,
                        arguments_obj=safe_json_loads(arguments_raw),
                        file_path=path,
                        line_no=idx,
                    )
                    calls[call_id] = record
                elif entry_type == "function_call_output":
                    call_id = entry.get("call_id")
                    if not call_id:
                        continue
                    record = calls.setdefault(call_id, CallRecord(name="<unknown>"))
                    output_raw = entry.get("output")
                    record.output_raw = output_raw
                    record.output_obj = safe_json_loads(output_raw)
                    if record.file_path is None:
                        record.file_path = path
                        record.line_no = idx
    return calls


def aggregate_calls(
    calls: Dict[str, CallRecord], encoder
) -> Tuple[Dict[str, Aggregate], Dict[str, Aggregate], Dict[str, Aggregate]]:
    detail_stats: Dict[str, Aggregate] = defaultdict(Aggregate)
    tool_stats: Dict[str, Aggregate] = defaultdict(Aggregate)
    provider_stats: Dict[str, Aggregate] = defaultdict(Aggregate)

    for record in calls.values():
        inp = count_tokens(record.arguments_raw, encoder)
        out = count_tokens(record.output_raw, encoder)
        if inp == 0 and out == 0:
            continue
        detail_stats[build_detail_key(record)].add(inp, out)
        tool_stats[build_tool_key(record)].add(inp, out)
        provider_stats[build_provider_key(record)].add(inp, out)
    return detail_stats, tool_stats, provider_stats


def render_table(title: str, stats: Dict[str, Aggregate], top_n: Optional[int] = None) -> None:
    print()
    print(title)
    print("=" * len(title))
    header = f"{'#':>3}  {'total':>10}  {'input':>10}  {'output':>10}  {'count':>5}  detail"
    print(header)
    print("-" * len(header))
    sorted_items = sorted(
        stats.items(),
        key=lambda item: (item[1].total_tokens, item[0]),
        reverse=True,
    )
    for rank, (key, agg) in enumerate(sorted_items, start=1):
        if top_n is not None and rank > top_n:
            break
        print(
            f"{rank:>3}  {agg.total_tokens:>10}  {agg.input_tokens:>10}  {agg.output_tokens:>10}  {agg.count:>5}  {key}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise Codex CLI tool token usage.")
    parser.add_argument(
        "--sessions-root",
        default="sessions",
        help="Root directory containing Codex session logs (default: sessions).",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model name to select tokenizer (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--encoding",
        default=None,
        help="Override tokenizer encoding name (e.g. cl100k_base).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="Number of ranked rows to display per table (default: 20).",
    )
    parser.add_argument(
        "--show-full",
        action="store_true",
        help="Display all rows instead of limiting to --top entries.",
    )
    args = parser.parse_args()

    sessions_root = Path(args.sessions_root)
    encoder = resolve_encoding(args.model, args.encoding)
    calls = parse_logs(sessions_root)
    detail_stats, tool_stats, provider_stats = aggregate_calls(calls, encoder)

    total_calls = sum(agg.count for agg in detail_stats.values())
    print(f"Analysed {len(calls)} tool invocations (with non-zero tokens: {total_calls}).")
    top_n = None if args.show_full else args.top
    render_table("Detail Ranking", detail_stats, top_n)
    render_table("Tool Ranking", tool_stats, top_n)
    render_table("Provider Ranking", provider_stats, top_n)


if __name__ == "__main__":
    main()
