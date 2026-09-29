"""Sector context: thresholds should be read relative to the industry (README section 2.5).

A rule either marks a metric as not meaningful for the sector ("not_applicable"), or
downgrades a failed check to "sector_typical_fail" when the value is normal for peers ("typical").
"""

from __future__ import annotations

from dataclasses import dataclass

from stock_analyzer.models import CompanyProfile


@dataclass(frozen=True)
class SectorRule:
    metrics: tuple[str, ...]
    kind: str  # "typical" or "not_applicable"
    note: str
    sectors: tuple[str, ...] = ()
    industries: tuple[str, ...] = ()  # case-insensitive substrings of the industry name
    typical_range: tuple[float, float] | None = None

    def matches(self, profile: CompanyProfile, metric: str) -> bool:
        if metric not in self.metrics:
            return False
        sector = (profile.sector or "").lower()
        industry = (profile.industry or "").lower()
        return any(s.lower() == sector for s in self.sectors) or any(i in industry for i in self.industries)


RULES: tuple[SectorRule, ...] = (
    SectorRule(
        metrics=("inventory_turnover",),
        industries=("semiconductor",),
        kind="typical",
        typical_range=(0, 7.3),
        note="Low inventory turnover is normal for chipmakers (NVDA ~3.2, AMD ~2.3 in 2025, per AlphaQuery).",
    ),
    SectorRule(
        metrics=("current_ratio", "quick_ratio", "working_capital", "inventory_turnover", "ar_turnover"),
        sectors=("Financial Services",),
        kind="not_applicable",
        note="Not meaningful for financial firms: their balance sheets aren't split into current and "
             "long-term items, and their receivables are the loans they make.",
    ),
    SectorRule(
        metrics=("gross_margin",),
        sectors=("Financial Services",),
        kind="not_applicable",
        note="Not meaningful for financial firms, which have no cost of goods sold.",
    ),
    SectorRule(
        metrics=("roa",),
        sectors=("Financial Services",),
        kind="typical",
        typical_range=(0, 4),
        note="Financial firms hold large loan and securities books, so ROA is naturally low "
             "(bank ROA is usually near 1%; CIBC ~0.76%).",
    ),
    SectorRule(
        metrics=("de",),
        sectors=("Financial Services",),
        kind="typical",
        typical_range=(0, 10),
        note="Lenders fund their loans with borrowed money, so higher D/E is normal for financial firms.",
    ),
    SectorRule(
        metrics=("de",),
        sectors=("Utilities", "Real Estate"),
        kind="typical",
        typical_range=(0, 2.5),
        note="Utilities and real estate companies finance long-lived assets with debt; D/E up to ~2.5 is common.",
    ),
    SectorRule(
        metrics=("gross_margin",),
        sectors=("Consumer Defensive",),
        industries=("retail", "grocery", "discount"),
        kind="typical",
        typical_range=(15, 40),
        note="Retailers and consumer staples run on thin gross margins by design.",
    ),
)


def find_rule(profile: CompanyProfile, metric: str, kind: str) -> SectorRule | None:
    return next((r for r in RULES if r.kind == kind and r.matches(profile, metric)), None)


def is_sector_typical(profile: CompanyProfile, metric: str, actual: float) -> SectorRule | None:
    rule = find_rule(profile, metric, "typical")
    if rule and rule.typical_range and rule.typical_range[0] <= actual <= rule.typical_range[1]:
        return rule
    return None
