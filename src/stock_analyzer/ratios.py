"""Turns fetched CompanyData into a flat dict of metrics used by the checklists.

Percent metrics are stored as percent numbers (17.1 means 17.1%); multiples as plain numbers.
"""

from __future__ import annotations

from datetime import date

from stock_analyzer.models import CompanyData, Statement

Metrics = dict[str, float | None]


def series(stmt: Statement, *rows: str) -> list[tuple[str, float]]:
    """(date, value) pairs for the first row name that exists, oldest first."""
    for row in rows:
        if stmt.get(row):
            return sorted(stmt[row].items())
    return []


def latest(stmt: Statement, *rows: str) -> float | None:
    s = series(stmt, *rows)
    return s[-1][1] if s else None


def average_latest_two(stmt: Statement, *rows: str) -> float | None:
    s = series(stmt, *rows)
    if not s:
        return None
    vals = [v for _, v in s[-2:]]
    return sum(vals) / len(vals)


def years_between(start: str, end: str) -> float:
    return (date.fromisoformat(end) - date.fromisoformat(start)).days / 365.25


def annual_run(points: list[tuple[str, float]]) -> list[tuple[str, float]]:
    """The most recent run of points spaced about a year apart.

    Drops older points before an irregular gap (fiscal-year changes, pre-merger stub periods)
    so growth rates aren't computed from a non-comparable base.
    """
    points = sorted(points)
    run = points[-1:]
    for prev in reversed(points[:-1]):
        gap = (date.fromisoformat(run[0][0]) - date.fromisoformat(prev[0])).days
        if not 300 <= gap <= 430:
            break
        run.insert(0, prev)
    return run


def cagr(points: list[tuple[str, float]]) -> float | None:
    """Compound annual growth rate (fraction) across the most recent run of annual points."""
    points = annual_run(points)
    if len(points) < 2:
        return None
    (d0, v0), (d1, v1) = points[0], points[-1]
    years = years_between(d0, d1)
    if v0 <= 0 or v1 <= 0 or years < 0.9:
        return None
    return (v1 / v0) ** (1 / years) - 1


def _div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _pct(v: float | None) -> float | None:
    return None if v is None else v * 100


def compute_metrics(data: CompanyData) -> tuple[Metrics, dict[str, str]]:
    """Returns (metrics, notes). Notes explain how a metric was derived when it isn't obvious."""
    info, inc, bs, cf = data.info, data.income, data.balance, data.cashflow
    notes: dict[str, str] = {}
    m: Metrics = {}

    revenue = latest(inc, "Total Revenue", "Operating Revenue")
    price = data.profile.price

    # Price ratios
    m["pe"] = info.get("trailingPE")
    trailing_eps = info.get("trailingEps")
    if m["pe"] is None and price and trailing_eps and trailing_eps > 0:
        m["pe"] = price / trailing_eps
    if m["pe"] is None and trailing_eps is not None and trailing_eps <= 0:
        notes["pe"] = f"Undefined: trailing EPS is {trailing_eps:.2f} (not profitable)."
    m["forward_pe"] = info.get("forwardPE")
    m["pb"] = info.get("priceToBook")

    # Growth
    eps_points = sorted(data.eps_history.items())
    hist_eps_cagr = cagr(eps_points)
    m["eps_cagr"] = _pct(hist_eps_cagr)
    m["revenue_cagr"] = _pct(cagr(series(inc, "Total Revenue", "Operating Revenue")))
    ge = data.growth_estimates
    m["eps_growth_forward"] = _pct(ge.get("+1y"))

    # PEG = P/E / expected EPS growth (%). Prefer long-term analyst growth, then next year, then history.
    peg_growth, basis = None, ""
    for key, label in (("LTG", "analyst long-term EPS growth"), ("+5y", "analyst 5-year EPS growth"),
                       ("+1y", "analyst next-year EPS growth")):
        if ge.get(key) is not None:
            peg_growth, basis = ge[key], label
            break
    if peg_growth is None and hist_eps_cagr is not None:
        peg_growth, basis = hist_eps_cagr, "historical EPS CAGR"
    m["peg"] = info.get("trailingPegRatio")
    if m["peg"] is not None:
        notes["peg"] = "Reported by Yahoo Finance"
    elif m["pe"] and m["pe"] > 0 and peg_growth and peg_growth > 0:
        m["peg"] = m["pe"] / (peg_growth * 100)
        notes["peg"] = f"P/E / {peg_growth * 100:.1f}% {basis}"
    elif peg_growth is not None and peg_growth <= 0:
        notes["peg"] = f"Undefined: {basis} is negative ({peg_growth * 100:.1f}%)"

    # Profitability (yfinance reports fractions)
    m["roe"] = _pct(info.get("returnOnEquity"))
    if m["roe"] is None:
        m["roe"] = _pct(_div(latest(inc, "Net Income"), average_latest_two(bs, "Stockholders Equity")))
    m["roa"] = _pct(info.get("returnOnAssets"))
    if m["roa"] is None:
        m["roa"] = _pct(_div(latest(inc, "Net Income"), average_latest_two(bs, "Total Assets")))
    m["gross_margin"] = _pct(info.get("grossMargins"))
    if m["gross_margin"] is None:
        m["gross_margin"] = _pct(_div(latest(inc, "Gross Profit"), revenue))
    m["operating_margin"] = _pct(info.get("operatingMargins"))
    if m["operating_margin"] is None:
        m["operating_margin"] = _pct(_div(latest(inc, "Operating Income"), revenue))
    m["net_margin"] = _pct(info.get("profitMargins"))
    if m["net_margin"] is None:
        m["net_margin"] = _pct(_div(latest(inc, "Net Income"), revenue))

    # Leverage: yfinance reports debtToEquity as a percent (8.9 means 0.089)
    de = info.get("debtToEquity")
    m["de"] = de / 100 if de is not None else _div(latest(bs, "Total Debt"), latest(bs, "Stockholders Equity"))

    # Liquidity
    ca, cl = latest(bs, "Current Assets"), latest(bs, "Current Liabilities")
    m["current_assets"], m["current_liabilities"] = ca, cl
    m["working_capital"] = ca - cl if ca is not None and cl is not None else None
    m["current_ratio"] = info.get("currentRatio") or _div(ca, cl)
    m["quick_ratio"] = info.get("quickRatio")
    if m["quick_ratio"] is None and ca is not None:
        m["quick_ratio"] = _div(ca - (latest(bs, "Inventory") or 0), cl)

    # Efficiency
    m["ar_turnover"] = _div(revenue, average_latest_two(bs, "Accounts Receivable", "Receivables"))
    cogs = latest(inc, "Cost Of Revenue", "Reconciled Cost Of Revenue")
    avg_inventory = average_latest_two(bs, "Inventory")
    m["inventory_turnover"] = _div(cogs, avg_inventory) if avg_inventory else None
    if avg_inventory is None:
        notes["inventory_turnover"] = "No inventory reported"

    # Inputs for qualitative factors
    m["rd_pct"] = _pct(_div(latest(inc, "Research And Development"), revenue))
    rd = series(inc, "Research And Development")
    m["rd_growth"] = _pct(cagr(rd))
    revenues = [v for _, v in annual_run(series(inc, "Total Revenue", "Operating Revenue"))]
    m["revenue_years"] = float(len(revenues)) if len(revenues) >= 3 else None
    m["revenue_declines"] = (
        float(sum(1 for a, b in zip(revenues, revenues[1:]) if b < a)) if len(revenues) >= 3 else None
    )
    capex, ocf = latest(cf, "Capital Expenditure"), latest(cf, "Operating Cash Flow")
    m["capex_to_ocf"] = _pct(_div(abs(capex), ocf)) if capex is not None and ocf and ocf > 0 else None
    m["market_cap"] = data.profile.market_cap
    m["revenue"] = revenue
    return m, notes
