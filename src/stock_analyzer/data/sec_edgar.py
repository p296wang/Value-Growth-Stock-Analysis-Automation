"""Long-run annual EPS history from SEC EDGAR XBRL company facts.

The SEC requires a User-Agent that identifies the caller with contact details,
for example "Jane Doe jane@example.com". It is read from the SEC_USER_AGENT
environment variable; without it EDGAR is skipped.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import requests

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
EPS_CONCEPTS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")
CACHE_TTL_SECONDS = 24 * 60 * 60
MIN_REQUEST_INTERVAL = 0.12  # SEC allows at most 10 requests per second


def default_cache_dir() -> Path:
    return Path(os.environ.get("STOCK_ANALYZER_CACHE", Path.home() / ".cache" / "stock_analyzer")) / "sec"


@dataclass
class AnnualEps:
    end: str  # fiscal year end, ISO date
    eps: float
    filed: str  # filing date of the reported value, ISO date


class SecEdgarError(Exception):
    pass


class SecEdgarClient:
    def __init__(self, user_agent: str, cache_dir: Path | None = None, session: requests.Session | None = None):
        if not user_agent or "@" not in user_agent:
            raise SecEdgarError("SEC_USER_AGENT must include contact details, e.g. 'Jane Doe jane@example.com'")
        self.cache_dir = cache_dir or default_cache_dir()
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"})
        self._last_request = 0.0

    @classmethod
    def from_env(cls) -> SecEdgarClient | None:
        agent = os.environ.get("SEC_USER_AGENT", "").strip()
        return cls(agent) if agent else None

    def _get_json(self, url: str, cache_name: str) -> dict:
        path = self.cache_dir / cache_name
        if path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL_SECONDS:
            return json.loads(path.read_text(encoding="utf-8"))

        wait = MIN_REQUEST_INTERVAL - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        self._last_request = time.monotonic()
        resp = self.session.get(url, timeout=30)
        if resp.status_code == 404:
            raise SecEdgarError(f"not found: {url}")
        resp.raise_for_status()
        data = resp.json()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
        return data

    def cik_for(self, ticker: str) -> int | None:
        table = self._get_json(TICKERS_URL, "company_tickers.json")
        wanted = ticker.upper().replace(".", "-")
        for row in table.values():
            if row["ticker"].upper() == wanted:
                return int(row["cik_str"])
        return None

    def annual_eps(self, ticker: str) -> list[AnnualEps]:
        """Fiscal-year diluted EPS (basic if diluted is missing), oldest first."""
        cik = self.cik_for(ticker)
        if cik is None:
            return []
        facts = self._get_json(FACTS_URL.format(cik=cik), f"facts_{cik}.json")
        return parse_annual_eps(facts)


def parse_annual_eps(facts: dict) -> list[AnnualEps]:
    gaap = facts.get("facts", {}).get("us-gaap", {})
    for concept in EPS_CONCEPTS:
        units = gaap.get(concept, {}).get("units", {})
        records = units.get("USD/shares") or next(iter(units.values()), [])
        by_end: dict[str, AnnualEps] = {}
        for r in records:
            if not str(r.get("form", "")).startswith("10-K") or "start" not in r:
                continue
            days = (date.fromisoformat(r["end"]) - date.fromisoformat(r["start"])).days
            if not 350 <= days <= 380:  # full fiscal year only, not quarters
                continue
            current = by_end.get(r["end"])
            if current is None or r["filed"] > current.filed:  # latest filing wins (restatements)
                by_end[r["end"]] = AnnualEps(r["end"], float(r["val"]), r["filed"])
        if by_end:
            return sorted(by_end.values(), key=lambda e: e.end)
    return []
