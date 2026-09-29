"""End-to-end runs against the saved LIEN / ALAB fixtures (no network)."""

from pathlib import Path

import typer
from typer.testing import CliRunner

from stock_analyzer.cli import analyze

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()
app = typer.Typer()
app.command()(analyze)


def run(*args):
    result = runner.invoke(app, list(args), env={"COLUMNS": "200"})
    assert result.exit_code == 0, result.output
    return result.output


def test_lien_is_value():
    out = run("LIEN", "--offline", str(FIXTURES / "LIEN.json"))
    assert "Verdict: VALUE" in out
    assert "VALUE CHECKLIST" in out and "GROWTH CHECKLIST" in out and "10-YEAR EPS TEST" in out
    assert "not financial or investment advice" in out


def test_alab_is_growth_with_sector_typical_inventory_turnover():
    out = run("ALAB", "--offline", str(FIXTURES / "ALAB.json"))
    assert "Verdict: GROWTH" in out
    assert "Fail (sector-typical)" in out


def test_markdown_export(tmp_path):
    run("ALAB", "--offline", str(FIXTURES / "ALAB.json"), "--export", "md", "--output-dir", str(tmp_path))
    files = list(tmp_path.glob("ALAB_*.md"))
    assert len(files) == 1
    text = files[0].read_text(encoding="utf-8")
    for heading in ("## Value Checklist", "## 10-Year EPS Test", "## Growth Checklist",
                    "## Qualitative Analysis: Value Factors", "## Qualitative Analysis: Growth Factors", "## Sources"):
        assert heading in text
    assert "**Verdict: GROWTH**" in text


def test_eps_overrides_are_applied():
    out = run("LIEN", "--offline", str(FIXTURES / "LIEN.json"), "--eps-10y-ago", "1.23", "--min-pe", "5.65")
    assert "EPS 10 years ago" in out
