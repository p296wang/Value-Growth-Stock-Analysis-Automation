"""Number formatting shared by the qualitative text and report renderers."""

from __future__ import annotations

from typing import Any


def money(v: float | None, decimals: int = 1) -> str:
    if v is None:
        return "N/A"
    if v == 0:
        return "$0"
    sign = "-" if v < 0 else ""
    v = abs(v)
    for size, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if v >= size:
            return f"{sign}${v / size:.{decimals}f}{suffix}"
    return f"{sign}${v:,.2f}"


def value(v: float | None, unit: str = "") -> str:
    if v is None:
        return "N/A"
    if unit == "%":
        return f"{v:.2f}%"
    if unit == "$":
        return money(v)
    return f"{v:.2f}"


def threshold(op: str, t: Any, unit: str = "") -> str:
    def one(x: float) -> str:
        if unit == "%":
            return f"{x:g}%"
        if unit == "$":
            return money(x)
        return f"{x:g}"

    if op == "between":
        return f"{one(t[0])} to {one(t[1])}"
    return f"{'Below' if op == 'lt' else 'Above'} {one(t)}"


STATUS_LABELS = {
    "pass": "Pass",
    "fail": "Fail",
    "sector_typical_fail": "Fail (sector-typical)",
    "na": "N/A",
}
