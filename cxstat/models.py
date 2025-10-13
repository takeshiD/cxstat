"""Data models for cxstat token usage aggregation."""

from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, NonNegativeInt


class CallRecord(BaseModel):
    """Represents a single tool invocation extracted from Codex session logs."""

    call_id: str
    name: str
    arguments_raw: str | None = None
    arguments_obj: Any | None = None
    output_raw: str | None = None
    output_obj: Any | None = None
    file_path: Path | None = None
    line_no: int | None = None
    project_path: str | None = None
    timestamp: datetime | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None


class Aggregate(BaseModel):
    """Token usage summary for a given grouping."""

    count: NonNegativeInt = Field(default=0)
    input_tokens: NonNegativeInt = Field(default=0)
    output_tokens: NonNegativeInt = Field(default=0)

    def add(self, inp: int, out: int) -> None:
        """Accumulate token counts for a single invocation."""
        self.count += 1
        self.input_tokens += inp
        self.output_tokens += out

    @property
    def total_tokens(self) -> int:
        """Return the combined input and output token totals."""
        return self.input_tokens + self.output_tokens


class ProjectUsage(BaseModel):
    """Aggregate usage statistics for a single project path."""

    project_path: str = Field(...)
    totals: Aggregate = Field(default_factory=Aggregate)
    tool_totals: dict[str, Aggregate] = Field(default_factory=dict)
    provider_totals: dict[str, Aggregate] = Field(default_factory=dict)
    detail_totals: dict[str, Aggregate] = Field(default_factory=dict)
    last_invocation: datetime | None = Field(default=None)

    def add_invocation(
        self,
        tool_key: str,
        provider_key: str,
        detail_key: str,
        inp: int,
        out: int,
        timestamp: datetime | None,
    ) -> None:
        """Update totals with a new invocation of the given tool."""
        self.totals.add(inp, out)
        aggregate = self.tool_totals.get(tool_key)
        if aggregate is None:
            aggregate = Aggregate()
            self.tool_totals[tool_key] = aggregate
        aggregate.add(inp, out)

        provider_aggregate = self.provider_totals.get(provider_key)
        if provider_aggregate is None:
            provider_aggregate = Aggregate()
            self.provider_totals[provider_key] = provider_aggregate
        provider_aggregate.add(inp, out)

        detail_aggregate = self.detail_totals.get(detail_key)
        if detail_aggregate is None:
            detail_aggregate = Aggregate()
            self.detail_totals[detail_key] = detail_aggregate
        detail_aggregate.add(inp, out)
        if timestamp is not None and (
            self.last_invocation is None or timestamp > self.last_invocation
        ):
            self.last_invocation = timestamp

    def iter_tools(self) -> list[tuple[str, Aggregate]]:
        """Return tool aggregates sorted by total tokens descending."""
        return sorted(
            self.tool_totals.items(),
            key=lambda item: (item[1].total_tokens, item[0]),
            reverse=True,
        )


class UsageReport(BaseModel):
    """Complete aggregation result for a sessions directory."""

    detail_stats: dict[str, Aggregate] = Field(default_factory=dict)
    tool_stats: dict[str, Aggregate] = Field(default_factory=dict)
    provider_stats: dict[str, Aggregate] = Field(default_factory=dict)
    projects: dict[str, ProjectUsage] = Field(default_factory=dict)
    total_invocations: NonNegativeInt = Field(default=0)
    non_zero_invocations: NonNegativeInt = Field(default=0)
    overall: Aggregate = Field(...)

    def sorted_stats(self, stats: dict[str, Aggregate]) -> list[tuple[str, Aggregate]]:
        """Return entries sorted by total token usage descending."""
        return sorted(
            stats.items(),
            key=lambda item: (item[1].total_tokens, item[0]),
            reverse=True,
        )

    def iter_projects(self) -> list[ProjectUsage]:
        """Return projects sorted by total token usage descending."""
        return sorted(
            self.projects.values(),
            key=lambda usage: (usage.totals.total_tokens, usage.project_path),
            reverse=True,
        )
