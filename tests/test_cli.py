from typer.testing import CliRunner

from cxstat.cli.main import app

runner = CliRunner()


def test_codex():
    # no options
    result = runner.invoke(app, ["codex"])
    assert result.exit_code == 0
    # detail
    result = runner.invoke(app, ["codex", "--detail"])
    assert result.exit_code == 0
    # detail and top
    result = runner.invoke(app, ["codex", "--detail", "--top", "20"])
    assert result.exit_code == 0
    # theme
    result = runner.invoke(app, ["codex", "--theme", "ayu"])
    assert result.exit_code == 0
    # encoder
    result = runner.invoke(app, ["codex", "--encoder", "o200k_base"])
    assert result.exit_code == 0
