"""Row builders shared by the terminal and Markdown renderers."""

from __future__ import annotations

from dataclasses import dataclass

from stock_analyzer import formatting as fmt
from stock_analyzer.models import CheckResult, CompanyProfile, EpsTestResult, Report

DISCLAIMER = "For educational purposes only. This is not financial or investment advice."
SIGNAL_NOTE = "Extra growth signal on top of the core checklist"


def profile_rows(p: CompanyProfile) -> list[tuple[str, str]]:
    return [
        ("Sector", p.sector or "N/A"),
        ("Industry", p.industry or "N/A"),
        ("Country", p.country or "N/A"),
        ("Market cap", fmt.money(p.market_cap)),
        ("Price", f"${p.price:,.2f} {p.currency or ''}".strip() if p.price is not None else "N/A"),
        ("Annual dividend", f"${p.dividend_rate:.2f}" if p.dividend_rate else "None"),
        ("Employees", f"{p.employees:,}" if p.employees else "N/A"),
    ]


@dataclass
class CheckRow:
    check: CheckResult
    label: str
    threshold: str
    actual: str
    status: str
    note: str


def check_rows(checks: list[CheckResult], report: Report) -> list[CheckRow]:
    """Display rows for a checklist; a note repeated from an earlier row becomes "Same as above"."""
    rows, seen = [], set()
    for c in checks:
        note = c.note
        if c.id == "working_capital" and c.status != "na":
            note = working_capital_note(report) or note
        if note and note in seen:
            note = "Same as above."
        elif note:
            seen.add(note)
        rows.append(CheckRow(c, c.label, fmt.threshold(c.op, c.threshold, c.unit), fmt.value(c.actual, c.unit),
                             fmt.STATUS_LABELS[c.status], note))
    return rows


def working_capital_note(report: Report) -> str | None:
    ca, cl = report.metrics.get("current_assets"), report.metrics.get("current_liabilities")
    if ca is None or cl is None:
        return None
    return f"Current assets {fmt.money(ca)} vs current liabilities {fmt.money(cl)}"


def eps_rows(e: EpsTestResult) -> list[tuple[str, str]]:
    def d(v: float | None) -> str:
        return "N/A" if v is None else f"${v:,.2f}"

    def pct(v: float | None) -> str:
        return "N/A" if v is None else f"{v * 100:.2f}%"

    years = f"{e.years:g}" if e.years is not None else "N"
    return [
        (f"EPS {years} years ago", d(e.eps_then)),
        ("Current EPS", d(e.eps_now)),
        ("Lowest P/E in period", "N/A" if e.min_pe is None else f"{e.min_pe:.2f}"),
        ("Current share price", d(e.price)),
        ("Annual dividend per share", d(e.dividend)),
        ("EPS growth rate", pct(e.growth_rate)),
        (f"Projected EPS in {years} years", d(e.projected_eps)),
        ("Projected trading price (lowest P/E x EPS)", d(e.projected_price)),
        (f"Projected value (+ {years} yrs of dividends)", d(e.projected_value)),
        ("Annual compound return", pct(e.annual_return)),
        ("Hurdle rate", pct(e.hurdle)),
    ]


def factor_mark(supports: bool | None) -> str:
    return {True: "Supports", False: "Against", None: "Neutral"}[supports]
