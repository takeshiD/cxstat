# ruff: noqa: E501
from pathlib import Path

from cxstat.service import _parse_session_file


def test_call_report():
    pass


def test_private_parse_session_file_parse_cat_command(tmpdir: Path):
    d = tmpdir / "sessions"
    d.mkdir()
    p = d / "sample.jsonl"
    p.write_text(
        r"""
{"timestamp":"2025-10-02T13:17:35.524Z","type":"session_meta","payload":{"id":"00000","timestamp":"2025-10-02T13:17:35.514Z","cwd":"/home/someone/program","originator":"codex_cli_rs","cli_version":"0.42.0","instructions":"None","git":{"commit_hash":"72c423731dff8bd817d3e57800c62d9e7ba05938","branch":"develop","repository_url":"https://github.com/someone/sample_program.git"}}}
{"timestamp":"2025-10-02T13:19:15.001Z","type":"response_item","payload":{"type":"function_call","name":"shell","arguments":"{\"command\":[\"bash\",\"-lc\",\"cat TODO.md\"],\"workdir\":\".\",\"timeout_ms\":120000}","call_id":"call_67ZP338hFIcoJVfTnwT2f6Zc"}}
{"timestamp":"2025-10-02T13:19:12.731Z","type":"response_item","payload":{"type":"function_call_output","call_id":"call_67ZP338hFIcoJVfTnwT2f6Zc","output":"sample_output"}}
    """,
        encoding="utf-8",
    )
    call_record = _parse_session_file(Path(p))
    assert "call_67ZP338hFIcoJVfTnwT2f6Zc" in call_record
    assert call_record["call_67ZP338hFIcoJVfTnwT2f6Zc"].name == "shell"
    assert call_record["call_67ZP338hFIcoJVfTnwT2f6Zc"].arguments_obj == {
        "command": ["bash", "-lc", "cat TODO.md"],
        "workdir": ".",
        "timeout_ms": 120000,
    }
    assert call_record["call_67ZP338hFIcoJVfTnwT2f6Zc"].output_raw == "sample_output"
    assert call_record["call_67ZP338hFIcoJVfTnwT2f6Zc"].output_obj is None

def test_private_parse_session_file_python_call(tmpdir: Path):
    d = tmpdir / "sessions"
    d.mkdir()
    p = d / "sample.jsonl"
    p.write_text(
        r"""
{"timestamp":"2025-10-02T13:17:35.524Z","type":"session_meta","payload":{"id":"00000","timestamp":"2025-10-02T13:17:35.514Z","cwd":"/home/someone/program","originator":"codex_cli_rs","cli_version":"0.42.0","instructions":"None","git":{"commit_hash":"72c423731dff8bd817d3e57800c62d9e7ba05938","branch":"develop","repository_url":"https://github.com/someone/sample_program.git"}}}
{"timestamp":"2025-10-10T14:24:54.561Z","type":"response_item","payload":{"type":"function_call","name":"shell","arguments":"{\"command\":[\"bash\",\"-lc\",\"uv run python - <<'PY'\\nfrom pathlib import Path\\nfrom cxstat.claude import parse_claude_logs\\nroot = Path('~/.claude/projects').expanduser()\\nrecords = parse_claude_logs(root)\\nprint('records', len(records))\\nprint(list(records.values())[:2])\\nPY\"],\"workdir\":\".\",\"timeout_ms\": 120000}","call_id":"call_onvpu6B6Mx0eTBivEf2RLuYF"}}
{"timestamp":"2025-10-10T14:24:54.561Z","type":"response_item","payload":{"type":"function_call_output","call_id":"call_onvpu6B6Mx0eTBivEf2RLuYF","output":"{\"output\":\"records 40\\n[CallRecord(call_id='60e4b8dc-8af8-4d95-8163-e9707b14fe2f:mcp__serena__list_dir', name='mcp__serena__list_dir', arguments_raw=None, arguments_obj=None, output_raw=None, output_obj=None, file_path=PosixPath('/home/tkcd/.claude/projects/-home-tkcd--codex/60e4b8dc-8af8-4d95-8163-e9707b14fe2f.jsonl'), line_no=4, project_path='/home/tkcd/.codex', timestamp=datetime.datetime(2025, 10, 7, 14, 18, 8, 600000, tzinfo=datetime.timezone.utc), input_tokens=800, output_tokens=0), CallRecord(call_id='60e4b8dc-8af8-4d95-8163-e9707b14fe2f:mcp__serena__find_file', name='mcp__serena__find_file', arguments_raw=None, arguments_obj=None, output_raw=None, output_obj=None, file_path=PosixPath('/home/tkcd/.claude/projects/-home-tkcd--codex/60e4b8dc-8af8-4d95-8163-e9707b14fe2f.jsonl'), line_no=4, project_path='/home/tkcd/.codex', timestamp=datetime.datetime(2025, 10, 7, 14, 18, 8, 600000, tzinfo=datetime.timezone.utc), input_tokens=679, output_tokens=0)]\\n\",\"metadata\":{\"exit_code\":0,\"duration_seconds\":0.2}}"}}
    """,
        encoding="utf-8",
    )
    call_record = _parse_session_file(Path(p))
    assert "call_onvpu6B6Mx0eTBivEf2RLuYF" in call_record
    assert call_record["call_onvpu6B6Mx0eTBivEf2RLuYF"].name == "shell"
    assert call_record["call_onvpu6B6Mx0eTBivEf2RLuYF"].arguments_obj == {
        "command": ["bash", "-lc", "uv run python - <<'PY'\\nfrom pathlib import Path\\nfrom cxstat.claude import parse_claude_logs\\nroot = Path('~/.claude/projects').expanduser()\\nrecords = parse_claude_logs(root)\\nprint('records', len(records))\\nprint(list(records.values())[:2])\\nPY"],
        "workdir": ".",
        "timeout_ms": 120000,
    }
    assert call_record["call_onvpu6B6Mx0eTBivEf2RLuYF"].output_raw == "sample_output"
    assert call_record["call_onvpu6B6Mx0eTBivEf2RLuYF"].output_obj is None
