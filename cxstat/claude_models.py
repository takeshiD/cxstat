"""Pydantic models for Claude Code session logs.

The Claude desktop app emits mixed JSON lines with varying shapes. We only
normalise the fields required for token usage extraction and ignore the rest.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


class ClaudeMessage(BaseModel):
    """Represents the nested message payload when present."""

    model_config = ConfigDict(extra="ignore")

    role: str | None = None
    content: Any | None = None


class ClaudeEntry(BaseModel):
    """Top-level log entry from Claude Code."""

    model_config = ConfigDict(extra="ignore")

    type: str | None = None
    message: ClaudeMessage | None = None
    # Some entries place content at the top level (e.g. system/local_command)
    content: Any | None = None
    sessionId: str | None = None
    cwd: str | None = None
    timestamp: datetime | None = None

    @field_validator("timestamp", mode="before")
    @classmethod
    def _parse_timestamp(cls, value: object) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                if value.endswith("Z"):
                    value = value[:-1] + "+00:00"
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None


def try_parse_claude_entry(raw: dict[str, Any]) -> ClaudeEntry | None:
    """Best-effort parse of a raw dict into a ClaudeEntry instance."""
    try:
        return ClaudeEntry.model_validate(raw)
    except ValidationError:
        return None
