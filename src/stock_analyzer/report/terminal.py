"""Rich terminal rendering of a Report."""

from __future__ import annotations

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from stock_analyzer import formatting as fmt
from stock_analyzer.models import CheckResult, Report
from stock_analyzer.report.common import DISCLAIMER, SIGNAL_NOTE, check_rows, eps_rows, factor_mark, profile_rows

VERDICT_STYLES = {"Value": "bold green", "Growth": "bold cyan", "Both": "bold magenta", "Neither": "bold yellow"}
STATUS_STYLES = {"Pass": "green", "Fail": "red", "Fail (sector-typical)": "yellow", "N/A": "dim"}
FACTOR_STYLES = {"Supports": "green", "Against": "red", "Neutral": "dim"}


def _score(v: float | None) -> str:
    return "N/A" if v is None else f"{v:.0%}"


def _checks_table(title: str, checks: list[CheckResult], report: Report) -> Table:
    table = Table(title=title, title_justify="left", box=box.SIMPLE_HEAVY, expand=True)
    table.add_column("Ratio", style="bold", ratio=3)
    table.add_column("Threshold", ratio=2)
    table.add_column("Actual", justify="right", ratio=2)
    table.add_column("Result", ratio=2)
    table.add_column("Note", style="dim", ratio=5)
    for row in check_rows(checks, report):
        label = f"{row.label} *" if row.check.group == "growth_signal" else row.label
        table.add_row(label, row.threshold, row.actual, Text(row.status, style=STATUS_STYLES[row.status]), row.note)
    return table


def render(report: Report, console: Console | None = None) -> None:
    console = console or Console()
    p, v = report.profile, report.verdict

    header = Text.assemble(
        (f"{p.ticker}", "bold"), "  ", (p.name or "", "bold"), "\n",
        "Verdict: ", (v.label.upper(), VERDICT_STYLES[v.label]),
        f"   Confidence: {v.confidence:.0%}",
        f"   Value score: {_score(v.value_score)}   Growth score: {_score(v.growth_score)}",
    )
    console.print(Panel(header, box=box.DOUBLE, expand=True))

    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold")
    info.add_column()
    for k, val in profile_rows(p):
        info.add_row(k, val)
    summary = (p.summary or "")
    if len(summary) > 600:
        summary = summary[:600].rsplit(" ", 1)[0] + "..."
    console.print(Panel(Group(info, Text(""), Text(summary)), title="Company", title_align="left"))
    console.print(Panel(Text(v.explanation), title="Why this verdict", title_align="left"))

    console.print(_checks_table("VALUE CHECKLIST", report.value_checks, report))

    e = report.eps_test
    eps = Table(title="10-YEAR EPS TEST", title_justify="left", box=box.SIMPLE_HEAVY)
    eps.add_column("Step", style="bold")
    eps.add_column("Value", justify="right")
    for k, val in eps_rows(e):
        eps.add_row(k, val)
    status = fmt.STATUS_LABELS[e.status]
    eps.add_row("Result", Text(status, style=STATUS_STYLES[status]))
    console.print(eps)
    if e.inputs_source:
        console.print(Text(f"  Inputs: {e.inputs_source}", style="dim"))
    if e.note:
        console.print(Text(f"  {e.note}", style="dim"))

    console.print(_checks_table("GROWTH CHECKLIST", report.growth_checks, report))
    console.print(Text(f"  * {SIGNAL_NOTE}", style="dim"))

    for profile_name, title in (("value", "QUALITATIVE: VALUE FACTORS"), ("growth", "QUALITATIVE: GROWTH FACTORS")):
        table = Table(title=title, title_justify="left", box=box.SIMPLE_HEAVY, expand=True, show_lines=False)
        table.add_column("Factor", style="bold", ratio=2)
        table.add_column("Signal", ratio=1)
        table.add_column("Evidence", ratio=7)
        for f in report.qualitative:
            if f.profile == profile_name:
                mark = factor_mark(f.supports)
                table.add_row(f.name, Text(mark, style=FACTOR_STYLES[mark]), f.evidence)
        console.print(table)

    if report.caveats:
        console.print(Panel("\n".join(f"- {c}" for c in report.caveats), title="Caveats", title_align="left",
                            border_style="yellow"))
    console.print(Text("Sources: " + "; ".join(report.sources), style="dim"))
    console.print(Text(f"Data fetched: {report.fetched_at}", style="dim"))
    console.print(Text(DISCLAIMER, style="bold yellow"))
