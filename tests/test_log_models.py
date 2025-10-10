"""Pytest unit tests for ``cxstat.log_models``."""

# ruff: noqa: S101

from __future__ import annotations

from datetime import UTC, datetime

from cxstat.log_models import (
    FunctionCallEntry,
    FunctionCallOutputEntry,
    SessionMetaEntry,
    parse_log_entry,
)


def test_session_meta_entry_parses_with_timestamp() -> None:
    """Ensure session_meta entries normalize timestamps and payload."""
    raw = {
        "type": "session_meta",
        "timestamp": "2025-09-30T12:34:56Z",
        "payload": {"cwd": "/workspace/project"},
    }

    entry = parse_log_entry(raw)

    assert isinstance(entry, SessionMetaEntry)
    assert entry.payload is not None
    assert entry.payload.cwd == "/workspace/project"
    assert entry.timestamp == datetime(2025, 9, 30, 12, 34, 56, tzinfo=UTC)


def test_function_call_entry_round_trip() -> None:
    """Validate direct function_call entries are returned unchanged."""
    raw = {
        "type": "function_call",
        "timestamp": "2025-10-01T08:15:00",
        "call_id": "abc123",
        "name": "shell",
        "arguments": {"command": ["echo", "hello"]},
    }

    entry = parse_log_entry(raw)

    assert isinstance(entry, FunctionCallEntry)
    assert entry.call_id == "abc123"
    assert entry.arguments == {"command": ["echo", "hello"]}
    assert entry.name == "shell"


def test_response_item_function_call_converts() -> None:
    """Confirm response_item/function_call payloads become FunctionCallEntry."""
    raw = {
        "type": "response_item",
        "timestamp": "2025-10-01T08:30:00Z",
        "payload": {
            "type": "function_call",
            "call_id": "call-001",
            "name": "mcp.tavily-search",
            "arguments": {"query": "codex"},
        },
    }

    entry = parse_log_entry(raw)

    assert isinstance(entry, FunctionCallEntry)
    assert entry.call_id == "call-001"
    assert entry.name == "mcp.tavily-search"
    assert entry.arguments == {"query": "codex"}


def test_response_item_function_call_output_converts() -> None:
    """Confirm response_item/function_call_output payloads are converted."""
    raw = {
        "type": "response_item",
        "timestamp": "2025-10-01T08:31:00Z",
        "payload": {
            "type": "function_call_output",
            "call_id": "call-002",
            "output": {"result": "ok"},
        },
    }

    entry = parse_log_entry(raw)

    assert isinstance(entry, FunctionCallOutputEntry)
    assert entry.call_id == "call-002"
    assert entry.output == {"result": "ok"}


def test_invalid_response_item_without_call_id_returns_none() -> None:
    """Ensure malformed payloads without call_id are ignored."""
    raw = {
        "type": "response_item",
        "timestamp": "2025-10-01T09:00:00Z",
        "payload": {
            "type": "function_call",
            "name": "shell",
            "arguments": {"command": ["ls"]},
        },
    }

    entry = parse_log_entry(raw)

    assert entry is None
