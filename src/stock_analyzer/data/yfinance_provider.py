"""Primary data source: Yahoo Finance via yfinance, with SEC EDGAR for long EPS history."""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import yfinance as yf

from stock_analyzer.data.provider import TickerNotFound
from stock_analyzer.data.sec_edgar import SecEdgarClient
from stock_analyzer.models import CompanyData, CompanyProfile, InsiderTransaction, Statement

log = logging.getLogger(__name__)

# Raw ratio fields kept from Ticker.info (yfinance reports most as fractions; D/E as a percent)
INFO_FIELDS = (
    "trailingPE", "forwardPE", "trailingPegRatio", "priceToBook", "returnOnEquity", "returnOnAssets",
    "debtToEquity", "grossMargins", "operatingMargins", "profitMargins", "currentRatio", "quickRatio",
    "trailingEps", "forwardEps", "revenueGrowth", "earningsGrowth", "totalRevenue", "bookValue",
)


class YFinanceProvider:
    def __init__(self, sec: SecEdgarClient | None = None):
        self.sec = sec

    def fetch(self, ticker: str) -> CompanyData:
        ticker = ticker.strip().upper()
        tk = yf.Ticker(ticker)
        try:
            info = tk.info or {}
        except Exception as exc:  # yfinance raises assorted errors for unknown symbols
            raise TickerNotFound(f"No data found for '{ticker}' ({exc})") from exc
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price or not (info.get("longName") or info.get("shortName")):
            raise TickerNotFound(f"No data found for '{ticker}'. Check the ticker symbol.")

        profile = CompanyProfile(
            ticker=ticker,
            name=info.get("longName") or info.get("shortName"),
            sector=info.get("sector"),
            industry=info.get("industry"),
            country=info.get("country"),
            currency=info.get("currency"),
            market_cap=_num(info.get("marketCap")),
            price=_num(price),
            dividend_rate=_num(info.get("dividendRate")),
            employees=info.get("fullTimeEmployees"),
            summary=info.get("longBusinessSummary"),
        )
        data = CompanyData(
            profile=profile,
            info={k: _num(info.get(k)) for k in INFO_FIELDS},
            income=_safe(lambda: _statement(tk.financials), {}),
            balance=_safe(lambda: _statement(tk.balance_sheet), {}),
            cashflow=_safe(lambda: _statement(tk.cashflow), {}),
            growth_estimates=_safe(lambda: _growth_estimates(tk), {}),
            insiders=_safe(lambda: _insiders(tk), []),
            fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            sources=["Yahoo Finance (yfinance): price, ratios, financial statements, insider transactions"],
        )

        splits = _safe(lambda: tk.splits, pd.Series(dtype=float))
        data.eps_history, data.eps_source = self._eps_history(ticker, data.income, splits)
        if data.eps_source.startswith("SEC"):
            data.sources.append("SEC EDGAR XBRL company facts: annual EPS history")
        data.price_lows = _safe(lambda: _price_lows(tk, list(data.eps_history)), {})
        return data

    def _eps_history(self, ticker: str, income: Statement, splits: pd.Series) -> tuple[dict[str, float], str]:
        if self.sec is not None:
            try:
                records = self.sec.annual_eps(ticker)
            except Exception as exc:
                log.warning("SEC EDGAR lookup failed for %s: %s", ticker, exc)
                records = []
            if records:
                history = {r.end: round(r.eps / _split_factor_after(splits, r.filed), 4) for r in records}
                return history, "SEC EDGAR (10-K filings)"
        row = income.get("Diluted EPS") or income.get("Basic EPS") or {}
        return dict(sorted(row.items())), "Yahoo Finance (annual statements)"


def _num(v: Any) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def _safe(fn, default):
    try:
        result = fn()
        return default if result is None else result
    except Exception as exc:
        log.warning("yfinance lookup failed: %s", exc)
        return default


def _statement(df: pd.DataFrame | None) -> Statement:
    if df is None or df.empty:
        return {}
    out: Statement = {}
    for row, series in df.iterrows():
        values = {pd.Timestamp(col).date().isoformat(): float(v) for col, v in series.items() if pd.notna(v)}
        if values:
            out[str(row)] = dict(sorted(values.items()))
    return out


def _growth_estimates(tk: yf.Ticker) -> dict[str, float]:
    df = tk.growth_estimates
    if df is None or df.empty or "stockTrend" not in df:
        return {}
    return {str(k): float(v) for k, v in df["stockTrend"].items() if pd.notna(v)}


def _insiders(tk: yf.Ticker) -> list[InsiderTransaction]:
    df = tk.insider_transactions
    if df is None or df.empty:
        return []
    out = []
    for _, r in df.iterrows():
        text = str(r.get("Text") or "")
        lowered = f"{text} {r.get('Transaction') or ''}".lower()
        kind = "buy" if "purchase" in lowered else "sell" if "sale" in lowered else "other"
        start = r.get("Start Date")
        out.append(InsiderTransaction(
            date=pd.Timestamp(start).date().isoformat() if pd.notna(start) else "",
            insider=str(r.get("Insider") or ""),
            position=str(r.get("Position") or ""),
            kind=kind,
            shares=_num(r.get("Shares")),
            value=_num(r.get("Value")),
            text=text,
        ))
    return out


def _price_lows(tk: yf.Ticker, fiscal_year_ends: list[str]) -> dict[str, float]:
    """Lowest daily price during each fiscal year (the 12 months ending on the fiscal year end)."""
    if not fiscal_year_ends:
        return {}
    hist = tk.history(period="max", interval="1d", auto_adjust=False)
    if hist.empty:
        return {}
    lows = hist["Low"]
    lows.index = pd.DatetimeIndex(lows.index).tz_localize(None).normalize()
    out = {}
    for end in fiscal_year_ends:
        end_ts = pd.Timestamp(end)
        window = lows[(lows.index > end_ts - timedelta(days=365)) & (lows.index <= end_ts)]
        # skip partial years (e.g. the IPO year) so the minimum isn't taken over a few weeks
        if len(window) >= 200:
            out[end] = round(float(window.min()), 4)
    return out


def _split_factor_after(splits: pd.Series, filed: str) -> float:
    """Combined split ratio for splits after a filing date (EPS filed earlier is pre-split)."""
    if splits is None or splits.empty:
        return 1.0
    idx = pd.DatetimeIndex(splits.index).tz_localize(None)
    factor = 1.0
    for when, ratio in zip(idx, splits.values):
        if when > pd.Timestamp(filed) and ratio > 0:
            factor *= float(ratio)
    return factor
