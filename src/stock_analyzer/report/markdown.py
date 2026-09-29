"""Markdown export of a Report."""

from __future__ import annotations

from stock_analyzer import formatting as fmt
from stock_analyzer.models import CheckResult, Report
from stock_analyzer.report.common import DISCLAIMER, check_rows, eps_rows, factor_mark, profile_rows


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(_cell(c) for c in row) + " |" for row in rows]
    return lines


def _check_rows(checks: list[CheckResult], report: Report) -> list[list[str]]:
    return [
        [f"{r.label} *" if r.check.group == "growth_signal" else r.label, r.threshold, r.actual,
         f"**{r.status}**" if r.status == "Pass" else r.status, r.note]
        for r in check_rows(checks, report)
    ]


def _score(s: float | None) -> str:
    return "N/A" if s is None else f"{s:.0%}"


def render(report: Report) -> str:
    p, v = report.profile, report.verdict
    out = [
        f"# {p.ticker}: {p.name or ''}",
        "",
        f"**Verdict: {v.label.upper()}** · Confidence {v.confidence:.0%} · "
        f"Value score {_score(v.value_score)} · Growth score {_score(v.growth_score)}",
        "",
        v.explanation,
        "",
        "## Company",
        "",
        *_table(["", ""], [[k, val] for k, val in profile_rows(p)]),
        "",
        p.summary or "",
        "",
        "## Value Checklist",
        "",
        *_table(["Ratio", "Threshold", "Actual", "Result", "Note"], _check_rows(report.value_checks, report)),
        "",
        "## 10-Year EPS Test",
        "",
        *_table(["Step", "Value"], [[k, val] for k, val in eps_rows(report.eps_test)]
                + [["Result", f"**{fmt.STATUS_LABELS[report.eps_test.status]}**"]]),
        "",
    ]
    if report.eps_test.inputs_source:
        out += [f"Inputs: {report.eps_test.inputs_source}", ""]
    if report.eps_test.note:
        out += [f"_{report.eps_test.note}_", ""]
    out += [
        "## Growth Checklist",
        "",
        *_table(["Ratio", "Threshold", "Actual", "Result", "Note"], _check_rows(report.growth_checks, report)),
        "",
        "\\* Supplementary growth signal, not part of the assignment table.",
        "",
    ]
    for profile_name, title in (("value", "Qualitative Analysis: Value Factors"),
                                ("growth", "Qualitative Analysis: Growth Factors")):
        rows = [[f.name, factor_mark(f.supports), f.evidence] for f in report.qualitative if f.profile == profile_name]
        out += [f"## {title}", "", *_table(["Factor", "Signal", "Evidence"], rows), ""]
    if report.caveats:
        out += ["## Caveats", "", *[f"- {c}" for c in report.caveats], ""]
    out += [
        "## Sources",
        "",
        *[f"- {s}" for s in report.sources],
        f"- Data fetched: {report.fetched_at}",
        "",
        f"> ⚠️ {DISCLAIMER}",
        "",
    ]
    return "\n".join(out)
