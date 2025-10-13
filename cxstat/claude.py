"""Parsing utilities for Claude Code session logs."""

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from tiktoken import Encoding

from cxstat.logger import logger
from cxstat.models import CallRecord, UsageReport
from cxstat.service import (
    aggregate_usage,
    resolve_encoding,
)

from .claude_models import ClaudeEntry, try_parse_claude_entry

LOG = logger.getChild("claude")

DEFAULT_CLAUDE_PROJECTS_ROOT = Path.home() / ".claude" / "projects"

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TOOL_LINE_RE = re.compile(
    r"^└\s*(?P<tool>[^()]+?)\s*\((?P<provider>[^()]+)\):\s*(?P<tokens>[0-9.,]+(?:[km])?)"
)


@dataclass
class _ToolSnapshot:
    """Represents the latest observed usage snapshot for a Claude tool."""

    name: str
    tokens: int
    timestamp: datetime | None
    file_path: Path
    line_no: int
    project_path: str | None


def load_claude_report(
    sessions_root: Path,
    *,
    encoder: Encoding | None = None,
) -> UsageReport:
    """Parse Claude Code logs and return token usage aggregations."""
    resolved_encoder = encoder or resolve_encoding(None, None)
    calls = parse_claude_logs(sessions_root)
    return aggregate_usage(calls.values(), resolved_encoder)


def parse_claude_logs(root: Path) -> dict[str, CallRecord]:
    """Parse Claude Code session logs into call records keyed by synthetic IDs.

    Supports both ``*.jsonl`` and ``*.json`` files under the given root.
    """
    calls: dict[str, CallRecord] = {}
    for path in _iter_claude_session_files(root):
        for record in _parse_session_file(path):
            calls[record.call_id] = record
    return calls


def _iter_claude_session_files(root: Path):
    if not root.exists():  # pragma: no cover - user-facing branch
        message = f"sessions directory not found: {root}"
        raise FileNotFoundError(message)
    # Search *.jsonl and *.json files
    for pattern in ("*.jsonl", "*.json"):
        for path in sorted(root.rglob(pattern)):
            if path.is_file():
                yield path


def _iter_json_objects(path: Path) -> Iterable[tuple[int, dict[str, object]]]:
    """Yield JSON objects from JSONL files or concatenated JSON blobs."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:  # pragma: no cover - defensive I/O branch
        LOG.warning("Failed to read %s: %s", path, exc)
        return []

    decoder = json.JSONDecoder()
    idx = 0
    length = len(text)
    while idx < length:
        # Skip whitespace
        while idx < length and text[idx].isspace():
            idx += 1
        if idx >= length:
            break
        try:
            obj, next_idx = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            # Give up on remaining tail if it cannot be parsed
            LOG.debug(
                "Skipping malformed JSON in %s:%d", path, text.count("\n", 0, idx) + 1
            )
            break
        line_no = text.count("\n", 0, idx) + 1
        if isinstance(obj, dict):
            yield line_no, obj
        idx = next_idx


def _parse_session_file(path: Path) -> Iterable[CallRecord]:
    """Yield CallRecord instances for the latest tool snapshot in a session file."""
    snapshots: dict[str, _ToolSnapshot] = {}
    session_id = path.stem
    last_project_path: str | None = None

    for line_no, raw_obj in _iter_json_objects(path):
        entry: ClaudeEntry | None = try_parse_claude_entry(raw_obj)
        if entry is None:
            continue

        session_id = entry.sessionId or session_id
        if isinstance(entry.cwd, str):
            last_project_path = entry.cwd

        # Prefer nested message content; fall back to top-level content (system)
        content_obj = (
            entry.message.content if entry.message is not None else entry.content
        )
        content_str = content_obj if isinstance(content_obj, str) else None
        if content_str is None or "<local-command-stdout>" not in content_str:
            continue

        stdout_text = _extract_stdout(content_str)
        tool_rows = list(_parse_tool_rows(stdout_text))
        if not tool_rows:
            continue

        timestamp = entry.timestamp

        for name, tokens in tool_rows:
            snapshots[name] = _ToolSnapshot(
                name=name,
                tokens=tokens,
                timestamp=timestamp,
                file_path=path,
                line_no=line_no,
                project_path=last_project_path,
            )

    records: list[CallRecord] = []
    for tool_name, snapshot in snapshots.items():
        call_id = f"{session_id}:{tool_name}"
        records.append(
            CallRecord(
                call_id=call_id,
                name=tool_name,
                file_path=snapshot.file_path,
                line_no=snapshot.line_no,
                project_path=snapshot.project_path,
                timestamp=snapshot.timestamp,
                input_tokens=snapshot.tokens,
                output_tokens=0,
            )
        )
    return records


def _extract_stdout(content: str) -> str:
    """Return the inner stdout text stripped of markup and ANSI escapes."""
    start_tag = "<local-command-stdout>"
    end_tag = "</local-command-stdout>"
    start_idx = content.find(start_tag)
    end_idx = content.rfind(end_tag)
    if start_idx == -1 or end_idx == -1:
        return ANSI_ESCAPE_RE.sub("", content)
    inner = content[start_idx + len(start_tag) : end_idx]
    cleaned = ANSI_ESCAPE_RE.sub("", inner)
    return cleaned.strip()


def _parse_tool_rows(stdout_text: str) -> Iterable[tuple[str, int]]:
    """Yield tool name and token pairs extracted from context output."""
    for raw_line in stdout_text.splitlines():
        line = raw_line.strip()
        if not line.startswith("└"):
            continue
        match = TOOL_LINE_RE.match(line)
        if not match:
            continue
        tool = match.group("tool").strip()
        token_value = match.group("tokens")
        tokens = _parse_token_value(token_value)
        if tokens <= 0:
            continue
        yield tool, tokens


def _parse_token_value(value: str) -> int:
    """Convert a textual token count into an integer number of tokens."""
    cleaned = value.lower().replace(",", "")
    multiplier = 1.0
    if cleaned.endswith("k"):
        multiplier = 1_000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        multiplier = 1_000_000.0
        cleaned = cleaned[:-1]

    try:
        numeric = float(cleaned)
    except ValueError:
        return 0
    return int(numeric * multiplier)


def _parse_timestamp(raw: object) -> datetime | None:
    """Parse Claude timestamp strings into aware datetime objects."""
    if not isinstance(raw, str):
        return None
    try:
        if raw.endswith("Z"):
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return datetime.fromisoformat(raw)
    except ValueError:
        return None
