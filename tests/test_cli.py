from typer.testing import CliRunner

from cxstat.cli.main import app

runner = CliRunner()

def test_no_subcommand():
    # no options
    result = runner.invoke(app)
    assert result.exit_code == 0 
    # detail
    result = runner.invoke(app, ["--detail"])
    assert result.exit_code == 0 
    # detail and top
    result = runner.invoke(app, ["--detail", "--top", "20"])
    assert result.exit_code == 0 
    # theme
    result = runner.invoke(app, ["--theme", "ayu"])
    assert result.exit_code == 0 
    # theme
    result = runner.invoke(app, ["--encoder", "o200k_base"])
    assert result.exit_code == 0 
