"""Loads the thresholds config and evaluates each checklist."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from stock_analyzer import sector
from stock_analyzer.models import CheckResult, CompanyProfile

# Metrics that are undefined (not just bad) when zero or negative
POSITIVE_ONLY = {"pe", "pb", "peg"}


def load_config(path: Path | None = None) -> dict[str, Any]:
    if path is not None:
        text = Path(path).read_text(encoding="utf-8")
    else:
        text = resources.files("stock_analyzer").joinpath("criteria.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(text)


def passes(op: str, actual: float, threshold: Any) -> bool:
    if op == "lt":
        return actual < threshold
    if op == "gt":
        return actual > threshold
    if op == "between":
        low, high = threshold
        return low <= actual <= high
    raise ValueError(f"unknown op: {op}")


def evaluate_check(
    check: dict[str, Any],
    group: str,
    metrics: dict[str, float | None],
    notes: dict[str, str],
    profile: CompanyProfile,
) -> CheckResult:
    metric = check["metric"]
    actual = metrics.get(metric)
    result = CheckResult(
        id=check["id"], label=check["label"], group=group, op=check["op"], threshold=check["threshold"],
        unit=check.get("unit", ""), actual=actual, status="na", rationale=check.get("rationale", ""),
        note=notes.get(metric, ""),
    )

    not_applicable = sector.find_rule(profile, metric, "not_applicable")
    if not_applicable:
        result.note = not_applicable.note
        return result
    if actual is None:
        result.note = result.note or "Data not available."
        return result
    if metric in POSITIVE_ONLY and actual <= 0:
        result.note = "Undefined because earnings or book value are negative."
        return result

    if passes(check["op"], actual, check["threshold"]):
        result.status = "pass"
        if metric == "current_ratio" and actual > 3:
            result.note = "Very high; can mean idle cash or bloated receivables/inventory, not only strength."
        return result

    typical = sector.is_sector_typical(profile, metric, actual)
    if typical:
        result.status = "sector_typical_fail"
        result.note = typical.note
    else:
        result.status = "fail"
        if check["op"] == "between" and actual > check["threshold"][1]:
            result.note = "Above the range: very profitable, which fits a mature business more than one reinvesting for growth."
    return result


def evaluate(
    checks: list[dict[str, Any]],
    group: str,
    metrics: dict[str, float | None],
    notes: dict[str, str],
    profile: CompanyProfile,
) -> list[CheckResult]:
    return [evaluate_check(c, group, metrics, notes, profile) for c in checks]
