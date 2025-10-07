"""Core services for parsing Codex CLI session logs and aggregating token usage."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

import tiktoken
from tiktoken import Encoding

from .models import Aggregate, CallRecord, ProjectUsage, UsageReport

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path


def resolve_encoding(model: str | None, encoding_name: str | None) -> Encoding:
    """Select a tokenizer encoding based on model or explicit preference."""
    if encoding_name:
        return tiktoken.get_encoding(encoding_name)
    if model:
        try:
            return tiktoken.encoding_for_model(model)
        except KeyError:
            pass
    return tiktoken.get_encoding("cl100k_base")


def safe_json_loads(text: str | None) -> object | None:
    """Parse JSON while tolerating invalid or empty payloads."""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def iter_session_files(root: Path) -> Iterator[Path]:
    """Yield all JSONL session files under the given directory sorted by name."""
    if not root.exists():
        message = f"sessions directory not found: {root}"
        raise FileNotFoundError(message)
    for path in sorted(root.rglob("*.jsonl")):
        if path.is_file():
            yield path


def parse_logs(root: Path) -> dict[str, CallRecord]:
    """Parse session logs and return call records keyed by call_id."""
    calls: dict[str, CallRecord] = {}
    for path in iter_session_files(root):
        _parse_session_file(path, calls)
    return calls


def _parse_session_file(path: Path, calls: dict[str, CallRecord]) -> None:
    project_path: str | None = None
    for line_no, entry in _iter_json_entries(path):
        project_path = _process_entry(
            entry,
            calls=calls,
            path=path,
            line_no=line_no,
            project_path=project_path,
        )


def _iter_json_entries(path: Path) -> Iterator[tuple[int, dict[str, object]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                yield line_no, entry


def _process_entry(
    entry: dict[str, object],
    *,
    calls: dict[str, CallRecord],
    path: Path,
    line_no: int,
    project_path: str | None,
) -> str | None:
    entry_type = entry.get("type")
    raw_timestamp = entry.get("timestamp")
    timestamp = parse_timestamp(raw_timestamp if isinstance(raw_timestamp, str) else None)

    if entry_type == "session_meta":
        payload = entry.get("payload") or {}
        cwd = payload.get("cwd") if isinstance(payload, dict) else None
        return cwd if isinstance(cwd, str) else project_path

    payload, payload_type = _extract_payload(entry_type, entry)
    if payload_type == "function_call":
        _record_function_call(
            payload,
            calls=calls,
            path=path,
            line_no=line_no,
            project_path=project_path,
            timestamp=timestamp,
        )
    elif payload_type == "function_call_output":
        _record_function_call_output(
            payload,
            calls=calls,
            path=path,
            line_no=line_no,
            project_path=project_path,
            timestamp=timestamp,
        )
    return project_path


def _extract_payload(
    entry_type: object,
    entry: dict[str, object],
) -> tuple[dict[str, object], object]:
    if entry_type == "response_item":
        payload = entry.get("payload")
        if isinstance(payload, dict):
            return payload, payload.get("type")
        return {}, None
    if isinstance(entry_type, str):
        return entry, entry_type
    return entry, None


def _record_function_call(
    payload: dict[str, object],
    *,
    calls: dict[str, CallRecord],
    path: Path,
    line_no: int,
    project_path: str | None,
    timestamp: datetime | None,
) -> None:
    call_id = payload.get("call_id")
    if not isinstance(call_id, str):
        return
    arguments_raw = _coerce_payload_text(payload.get("arguments"))
    name = payload.get("name", "<unknown>")
    record = CallRecord(
        call_id=call_id,
        name=name if isinstance(name, str) else "<unknown>",
        arguments_raw=arguments_raw,
        arguments_obj=safe_json_loads(arguments_raw),
        file_path=path,
        line_no=line_no,
        project_path=project_path,
        timestamp=timestamp,
    )
    calls[call_id] = record


def _record_function_call_output(
    payload: dict[str, object],
    *,
    calls: dict[str, CallRecord],
    path: Path,
    line_no: int,
    project_path: str | None,
    timestamp: datetime | None,
) -> None:
    call_id = payload.get("call_id")
    if not isinstance(call_id, str):
        return
    record = calls.setdefault(call_id, CallRecord(call_id=call_id, name="<unknown>"))
    record.output_raw = _coerce_payload_text(payload.get("output"))
    record.output_obj = safe_json_loads(record.output_raw)
    if record.file_path is None:
        record.file_path = path
        record.line_no = line_no
    if record.project_path is None:
        record.project_path = project_path
    if record.timestamp is None:
        record.timestamp = timestamp


def _coerce_payload_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def parse_timestamp(value: str | None) -> datetime | None:
    """Parse ISO timestamp values tolerant of trailing Z suffixes."""
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def count_tokens(text: str | None, encoder: Encoding) -> int:
    """Count tokens for the provided text using the supplied encoder."""
    if not text:
        return 0
    return len(encoder.encode(text))


def build_detail_key(record: CallRecord) -> str:
    """Generate a descriptive key for the detail-ranking table."""
    if record.name == "shell":
        return format_shell_command(record.arguments_obj)
    return summarize_args(record.name, record.arguments_obj)


def build_tool_key(record: CallRecord) -> str:
    """Return the fully-qualified tool name for aggregation."""
    return record.name or "<unknown>"


def build_provider_key(record: CallRecord) -> str:
    """Return the provider portion of the tool name for aggregation."""
    name = record.name or "<unknown>"
    if "__" in name:
        return name.split("__", 1)[0]
    return name


def format_shell_command(args_obj: object, max_len: int = 80) -> str:
    """Produce a readable label for shell command invocations."""
    prefix = "shell"
    default_label = f"{prefix} | <unknown>"

    if not isinstance(args_obj, dict):
        label = default_label
    else:
        cmd = args_obj.get("command")
        if isinstance(cmd, list):
            command_text = " ".join(str(part) for part in cmd)
            label = f"{prefix} | {command_text}" if command_text else prefix
        elif isinstance(cmd, str):
            label = f"{prefix} | {cmd}" if cmd else prefix
        else:
            label = default_label

    if len(label) > max_len:
        trim_at = max(max_len - 3, len(prefix) + 3)
        label = label[:trim_at] + "..."

    return label


def summarize_args(name: str, args_obj: object, max_len: int = 120) -> str:
    """Summarise tool arguments for detail-level reporting."""
    if args_obj is None:
        return name
    try:
        serialized = json.dumps(args_obj, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        serialized = str(args_obj)
    if len(serialized) > max_len:
        serialized = serialized[: max_len - 3] + "..."
    return f"{name} | {serialized}" if serialized else name


def aggregate_usage(records: Iterable[CallRecord], encoder: Encoding) -> UsageReport:
    """Aggregate token usage across multiple grouping dimensions."""
    detail_stats: dict[str, Aggregate] = defaultdict(Aggregate)
    tool_stats: dict[str, Aggregate] = defaultdict(Aggregate)
    provider_stats: dict[str, Aggregate] = defaultdict(Aggregate)
    projects: dict[str, ProjectUsage] = {}

    total_invocations = 0
    non_zero_invocations = 0
    overall = Aggregate()

    for record in records:
        total_invocations += 1
        inp = count_tokens(record.arguments_raw, encoder)
        out = count_tokens(record.output_raw, encoder)
        if inp == 0 and out == 0:
            continue

        non_zero_invocations += 1
        detail_stats[build_detail_key(record)].add(inp, out)
        tool_key = build_tool_key(record)
        tool_stats[tool_key].add(inp, out)
        provider_stats[build_provider_key(record)].add(inp, out)
        overall.add(inp, out)

        project_key = record.project_path or "<unknown>"
        project_usage = projects.get(project_key)
        if project_usage is None:
            project_usage = ProjectUsage(project_path=project_key)
            projects[project_key] = project_usage
        project_usage.add_invocation(tool_key, inp, out, record.timestamp)

    return UsageReport(
        detail_stats=dict(detail_stats),
        tool_stats=dict(tool_stats),
        provider_stats=dict(provider_stats),
        projects=projects,
        total_invocations=total_invocations,
        non_zero_invocations=non_zero_invocations,
        overall=overall,
    )


def load_report(
    sessions_root: Path,
    model: str | None = None,
    encoding_name: str | None = None,
) -> UsageReport:
    """Convenience helper to parse logs and aggregate token usage."""
    encoder = resolve_encoding(model, encoding_name)
    calls = parse_logs(sessions_root)
    return aggregate_usage(calls.values(), encoder)
