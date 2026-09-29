"""Time series for the web view's charts: price history, price stats and annual financials."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from stock_analyzer.models import CompanyData
from stock_analyzer.ratios import annual_run, series


def price_stats(prices: dict[str, float]) -> dict[str, Any]:
    """Latest close, 1-day change, 1-year return and 52-week range (changes as fractions)."""
    points = sorted(prices.items())
    if not points:
        return {}
    last_date, last = points[-1]
    year_ago = (date.fromisoformat(last_date) - timedelta(days=365)).isoformat()
    past_year = [v for d, v in points if d >= year_ago]
    base = next((v for d, v in points if d >= year_ago), None)
    has_full_year = points[0][0] <= year_ago
    prev = points[-2][1] if len(points) > 1 else None
    return {
        "last": last,
        "last_date": last_date,
        "change_1d": last / prev - 1 if prev else None,
        "return_1y": last / base - 1 if base and has_full_year else None,
        "high_52w": max(past_year),
        "low_52w": min(past_year),
    }


def _pct(a: float | None, b: float | None) -> float | None:
    return None if a is None or not b else a / b * 100


def annual_financials(data: CompanyData) -> list[dict[str, Any]]:
    """Revenue, net income and margins for each fiscal year in the most recent consecutive run."""
    inc = data.income
    revenue = annual_run(series(inc, "Total Revenue", "Operating Revenue"))
    rows = []
    for end, rev in revenue:
        net = inc.get("Net Income", {}).get(end)
        rows.append({
            "year": end[:4],
            "end": end,
            "revenue": rev,
            "net_income": net,
            "gross_margin": _pct(inc.get("Gross Profit", {}).get(end), rev),
            "operating_margin": _pct(inc.get("Operating Income", {}).get(end), rev),
            "net_margin": _pct(net, rev),
        })
    return rows


def build_history(data: CompanyData) -> dict[str, Any]:
    return {
        "prices": sorted(data.price_history.items()),
        "stats": price_stats(data.price_history),
        "financials": annual_financials(data),
        "eps": [{"year": end[:4], "end": end, "eps": eps}
                for end, eps in annual_run(list(data.eps_history.items()))],
        "eps_source": data.eps_source,
        "currency": data.profile.currency or "USD",
    }
