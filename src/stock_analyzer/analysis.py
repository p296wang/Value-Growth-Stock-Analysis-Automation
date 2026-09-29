"""Runs the full pipeline: fetched data -> metrics -> checklists -> verdict -> report."""

from __future__ import annotations

from datetime import date
from typing import Any

from stock_analyzer import criteria, qualitative
from stock_analyzer.classifier import classify
from stock_analyzer.eps_test import eps_test_for
from stock_analyzer.history import build_history
from stock_analyzer.models import CompanyData, Report
from stock_analyzer.ratios import compute_metrics


def build_report(
    data: CompanyData,
    config: dict[str, Any] | None = None,
    eps_then_override: float | None = None,
    min_pe_override: float | None = None,
    today: date | None = None,
) -> Report:
    config = config or criteria.load_config()
    metrics, notes = compute_metrics(data)
    profile = data.profile

    value_checks = criteria.evaluate(config["value_checks"], "value", metrics, notes, profile)
    growth_checks = (
        criteria.evaluate(config["growth_checks"], "growth", metrics, notes, profile)
        + criteria.evaluate(config.get("growth_signals", []), "growth_signal", metrics, notes, profile)
    )
    eps_cfg = config.get("eps_test", {})
    eps = eps_test_for(
        data,
        hurdle=eps_cfg.get("hurdle", 12) / 100,
        max_years=eps_cfg.get("max_years", 10),
        eps_then_override=eps_then_override,
        min_pe_override=min_pe_override,
        today=today,
    )
    cls_cfg = config.get("classifier", {})
    gate = cls_cfg.get("value_price_gate")
    verdict = classify(
        value_checks, eps, growth_checks,
        verdict_threshold=cls_cfg.get("verdict_threshold", 0.6),
        sector_typical_weight=cls_cfg.get("sector_typical_weight", 0.5),
        revenue_cagr=metrics.get("revenue_cagr"),
        min_coverage=cls_cfg.get("min_coverage", 0.0),
        value_price_gate=(gate["checks"], gate["min_pass"]) if gate else None,
    )

    caveats = []
    seen = set()
    for c in value_checks + growth_checks:
        if c.status == "sector_typical_fail" and c.note not in seen:
            caveats.append(f"{c.label} fails the threshold ({c.actual:.2f}), but {c.note[0].lower()}{c.note[1:]}")
            seen.add(c.note)
    if eps.note:
        caveats.append(f"EPS test: {eps.note}")
    if not data.eps_source.startswith("SEC"):
        caveats.append("Long-run EPS history comes from Yahoo Finance (about 4 years). Set SEC_USER_AGENT to use "
                       "10+ years of SEC filings, or enter the EPS test inputs yourself.")

    return Report(
        profile=profile,
        metrics=metrics,
        value_checks=value_checks,
        eps_test=eps,
        growth_checks=growth_checks,
        verdict=verdict,
        qualitative=qualitative.analyze(data, metrics),
        caveats=caveats,
        sources=data.sources,
        fetched_at=data.fetched_at,
        history=build_history(data),
    )
