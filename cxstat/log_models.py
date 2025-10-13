"""Pydantic models for Codex CLI log entries."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from cxstat.logger import logger

logger = logger.getChild("models")


class TimestampedEntry(BaseModel):
    """Mixin that normalises timestamp fields to ``datetime`` instances."""

    model_config = ConfigDict(extra="ignore")

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


class SessionMetaPayload(BaseModel):
    """Payload describing session metadata such as the working directory."""

    model_config = ConfigDict(extra="ignore")

    cwd: str | None = None


class SessionMetaEntry(TimestampedEntry):
    """Log entry emitted when a session starts and reports metadata."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["session_meta"]
    payload: SessionMetaPayload | None = None


class FunctionCallEntry(TimestampedEntry):
    """Log entry representing a tool invocation."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["function_call"]
    call_id: str
    name: str | None = None
    arguments: Any | None = None


class FunctionCallOutputEntry(TimestampedEntry):
    """Log entry capturing the output of a tool invocation."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["function_call_output"]
    call_id: str
    output: Any | None = None


class ResponsePayload(BaseModel):
    """Payload embedded within a response_item entry."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["function_call", "function_call_output"] | None = None
    call_id: str | None = None
    name: str | None = None
    arguments: Any | None = None
    output: Any | None = None


class ResponseItemEntry(TimestampedEntry):
    """Envelope entry that wraps tool call payloads."""

    model_config = ConfigDict(extra="ignore")

    type: Literal["response_item"]
    payload: ResponsePayload | None = None


LogEntry = SessionMetaEntry | FunctionCallEntry | FunctionCallOutputEntry


def parse_log_entry(raw: dict[str, Any]) -> LogEntry | None:
    """Parse a raw log dictionary into a strongly-typed log entry."""
    entry_type = raw.get("type")
    try:
        match entry_type:
            case "session_meta":
                return SessionMetaEntry.model_validate(raw)
            case "function_call":
                return FunctionCallEntry.model_validate(raw)
            case "function_call_output":
                return FunctionCallOutputEntry.model_validate(raw)
            case "response_item":
                return _parse_response_item(raw)
            case _:
                return None
    except ValidationError:
        logger.debug(f"validate error: {raw}")
        return None


def _parse_response_item(raw: dict[str, Any]) -> LogEntry | None:
    try:
        envelope = ResponseItemEntry.model_validate(raw)
    except ValidationError:
        return None

    payload = envelope.payload
    if payload is None or payload.type is None or not isinstance(payload.call_id, str):
        return None

    if payload.type == "function_call":
        return FunctionCallEntry(
            type="function_call",
            timestamp=envelope.timestamp,
            call_id=payload.call_id,
            name=payload.name,
            arguments=payload.arguments,
        )
    if payload.type == "function_call_output":
        return FunctionCallOutputEntry(
            type="function_call_output",
            timestamp=envelope.timestamp,
            call_id=payload.call_id,
            output=payload.output,
        )
    return None
