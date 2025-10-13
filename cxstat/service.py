"""Core services for parsing Codex CLI session logs and aggregating token usage."""

import json
from collections import defaultdict, deque
from collections.abc import Iterable, Iterator
from pathlib import Path

import tiktoken
from tiktoken import Encoding

from cxstat.log_models import (
    FunctionCallEntry,
    FunctionCallOutputEntry,
    SessionMetaEntry,
    parse_log_entry,
)
from cxstat.logger import logger
from cxstat.models import Aggregate, CallRecord, ProjectUsage, UsageReport
from cxstat.utils import normalize_path

logger = logger.getChild("service")


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


def parse_logs(root: Path) -> dict[str, CallRecord]:
    """Parse session logs and return call records keyed by call_id."""
    if not root.exists():
        message = f"sessions directory not found: {root}"
        raise FileNotFoundError(message)
    calls: dict[str, CallRecord] = {}
    for path in sorted(root.rglob("*.jsonl")):
        if path.is_file():
            calls.update(_parse_session_file(path))
    return calls


def _parse_session_file(path: Path) -> dict[str, CallRecord]:
    project_path: str | None = None
    calls: dict[str, CallRecord] = dict()
    for line_no, raw_entry in _iter_json_entries(path):
        entry = parse_log_entry(raw_entry)
        match entry:
            case SessionMetaEntry(type=_, payload=payload):
                if payload is None:
                    continue
                new_project_path = payload.cwd if payload.cwd is not None else None
                project_path = new_project_path
                continue
            case FunctionCallEntry(
                type=_, call_id=call_id, name=name, arguments=arguments
            ):
                normalised_project = normalize_path(project_path)
                arguments_raw = _coerce_payload_text(arguments)
                record = CallRecord(
                    call_id=call_id,
                    name=name or "<unknown>",
                    arguments_raw=arguments_raw,
                    arguments_obj=safe_json_loads(arguments_raw),
                    file_path=path,
                    line_no=line_no,
                    project_path=normalised_project,
                    timestamp=entry.timestamp,
                )
                calls[call_id] = record
                continue
            case FunctionCallOutputEntry(type=_, call_id=call_id, output=output):
                record = calls.setdefault(
                    call_id, CallRecord(call_id=call_id, name="<unknown>")
                )
                record.output_raw = _coerce_payload_text(output)
                record.output_obj = safe_json_loads(record.output_raw)
                if record.file_path is None:
                    record.file_path = path
                    record.line_no = line_no
                if record.project_path is None:
                    record.project_path = normalize_path(project_path)
                if record.timestamp is None:
                    record.timestamp = entry.timestamp
                continue
    return calls


def _iter_json_entries(path: Path) -> Iterator[tuple[int, dict[str, object]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                logger.debug(f"json line empty: {str(path)} line={line_no}")
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                logger.warning(f"json decode failed: {str(path)} line={line_no}")
                continue
            if isinstance(entry, dict):
                yield line_no, entry


def _coerce_payload_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


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
    default_label = f"[green]{prefix}[/]([bright_black]<unknown>[/])"
    if not isinstance(args_obj, dict):
        label = default_label
    else:
        command = args_obj.get("command")
        if isinstance(command, list):
            command = deque(command)
            command_list: list[str] = []
            if command[0] == "bash":
                command.popleft()
            if command[0] == "-lc":
                command.popleft()
            while len(command) > 0:
                cmd = command.popleft()
                logger.debug(f'command: "{cmd}"')
                commands = deque(cmd.split(" "))
                ignore_option_commands = {
                    "apply_patch",
                    "awk",
                    "head",
                    "tail",
                    "ls",
                    "nl",
                    "cat",
                    "rg",
                    "python",
                    "python3",
                    "pip",
                    "pip3",
                    "node",
                    "grep",
                    "pyright",
                    "cp",
                    "rm",
                    "mkdir",
                    "find",
                    "fd",
                    "diff",
                    "jq",
                    "tomlq",
                    "tmux",
                    ".",
                    "wc",
                    "printf",
                    "mv",
                    "chmod",
                    "echo",
                    "rustfmt",
                }
                contain_option_commands = {"cargo", "ruff", "uv", "git", "sed"}
                while len(commands) > 0:
                    c = commands.popleft()
                    if c.startswith("<<"):  # heardocument
                        command.clear()
                        break
                    if c == "-":
                        command.clear()
                        break
                    if c in ignore_option_commands:
                        if c == ".":
                            command_list.append("source")
                        else:
                            command_list.append(c)
                        command.clear()
                        break
                    if c in contain_option_commands:
                        command_list.append(c)
                        if len(commands) > 0:
                            c = commands.popleft()
                            if c is not None:
                                command_list.append(c)
                            command.clear()
                        break
                    command_list.append(c)
            command_text = " ".join(command_list)
            label = f"[green]{prefix}[/]({command_text})" if command_text else prefix
        elif isinstance(command, str):
            label = f"[green]{prefix}[/]([gray]{command}[/])" if command else prefix
        else:
            label = default_label
    if len(label) > max_len:
        trim_at = max(max_len - 3, len(prefix) + 3)
        label = label[:trim_at] + "..."
    return label


def summarize_args(name: str, args_obj: object, max_len: int = 120) -> str:
    """Summarise tool arguments for detail-level reporting."""
    tool = name.split("__")
    if len(tool) > 1:
        tool_name = tool[0]
        tool_arg = tool[1]
        return f"[yellow]{tool_name}[/]({tool_arg})"
    else:
        return name
    # if args_obj is None:
    #     return name
    # try:
    #     serialized = json.dumps(args_obj, ensure_ascii=False, sort_keys=True)
    # except (TypeError, ValueError):
    #     serialized = str(args_obj)
    # if len(serialized) > max_len:
    #     serialized = serialized[: max_len - 3] + "..."
    # return f"{name} | {serialized}" if serialized else name


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
        inp = (
            record.input_tokens
            if record.input_tokens is not None
            else count_tokens(record.arguments_raw, encoder)
        )
        out = (
            record.output_tokens
            if record.output_tokens is not None
            else count_tokens(record.output_raw, encoder)
        )
        if inp == 0 and out == 0:
            continue

        non_zero_invocations += 1
        detail_key = build_detail_key(record)
        tool_key = build_tool_key(record)
        provider_key = build_provider_key(record)
        detail_stats[detail_key].add(inp, out)
        tool_stats[tool_key].add(inp, out)
        provider_stats[provider_key].add(inp, out)
        overall.add(inp, out)

        project_key = normalize_path(record.project_path) or "<unknown>"
        project_usage = projects.get(project_key)
        if project_usage is None:
            project_usage = ProjectUsage(project_path=project_key)
            projects[project_key] = project_usage
        project_usage.add_invocation(
            tool_key,
            provider_key,
            detail_key,
            inp,
            out,
            record.timestamp,
        )

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
    *,
    encoder: Encoding | None = None,
) -> UsageReport:
    """Convenience helper to parse logs and aggregate token usage."""
    resolved_encoder = encoder or resolve_encoding(None, None)
    calls: dict[str, CallRecord] = parse_logs(sessions_root)
    return aggregate_usage(calls.values(), resolved_encoder)
