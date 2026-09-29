"""Local web view: `analyze-web`, then open http://127.0.0.1:8000."""

from __future__ import annotations

import argparse
import logging
import time
import webbrowser
from datetime import date
from pathlib import Path
from threading import Timer

from flask import Flask, Response, render_template, request

from stock_analyzer import criteria, formatting as fmt
from stock_analyzer.analysis import build_report
from stock_analyzer.data.provider import FixtureProvider, TickerNotFound
from stock_analyzer.data.sec_edgar import SecEdgarClient, SecEdgarError
from stock_analyzer.models import CheckResult, Report
from stock_analyzer.report import markdown
from stock_analyzer.report.common import DISCLAIMER, check_rows, eps_rows, factor_mark, profile_rows

log = logging.getLogger(__name__)
CACHE_TTL_SECONDS = 600
EXAMPLES = ("LIEN", "ALAB", "NVDA", "AAPL", "KO", "JPM")
STATUS_CLASSES = {"pass": "pass", "fail": "fail", "sector_typical_fail": "warn", "na": "na"}
SIGNAL_CLASSES = {"Supports": "pass", "Against": "fail", "Neutral": "na"}


def create_app(fixture_dir: Path | None = None) -> Flask:
    app = Flask(__name__)
    cache: dict[tuple, tuple[float, Report]] = {}

    def fetch_report(ticker: str, eps_10y_ago: float | None, min_pe: float | None) -> Report:
        key = (ticker, eps_10y_ago, min_pe)
        hit = cache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL_SECONDS:
            return hit[1]
        if fixture_dir is not None:
            path = fixture_dir / f"{ticker}.json"
            if not path.exists():
                raise TickerNotFound(f"No saved data for '{ticker}' in {fixture_dir}.")
            provider = FixtureProvider(path)
        else:
            from stock_analyzer.data.yfinance_provider import YFinanceProvider

            try:
                sec = SecEdgarClient.from_env()
            except SecEdgarError as exc:
                log.warning("Skipping SEC EDGAR: %s", exc)
                sec = None
            provider = YFinanceProvider(sec=sec)
        report = build_report(provider.fetch(ticker), criteria.load_config(),
                              eps_then_override=eps_10y_ago, min_pe_override=min_pe)
        cache[key] = (time.time(), report)
        return report

    def read_args() -> tuple[str, float | None, float | None]:
        ticker = (request.args.get("ticker") or "").strip().upper()
        return ticker, request.args.get("eps_10y_ago", type=float), request.args.get("min_pe", type=float)

    @app.get("/")
    def index():
        ticker, eps_10y_ago, min_pe = read_args()
        context = {"ticker": ticker, "eps_10y_ago": eps_10y_ago, "min_pe": min_pe,
                   "examples": EXAMPLES, "disclaimer": DISCLAIMER, "error": None, "view": None}
        if ticker:
            try:
                context["view"] = build_view(fetch_report(ticker, eps_10y_ago, min_pe))
            except TickerNotFound as exc:
                context["error"] = str(exc)
            except Exception as exc:  # network errors, provider changes
                log.exception("analysis failed for %s", ticker)
                context["error"] = f"Couldn't analyze {ticker}: {exc}"
        return render_template("index.html", **context)

    @app.get("/report.md")
    def report_markdown():
        ticker, eps_10y_ago, min_pe = read_args()
        if not ticker:
            return Response("ticker is required", status=400)
        try:
            report = fetch_report(ticker, eps_10y_ago, min_pe)
        except TickerNotFound as exc:
            return Response(str(exc), status=404)
        return Response(
            markdown.render(report),
            mimetype="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{ticker}_{report.fetched_at[:10]}.md"'},
        )

    return app


def _check_views(checks: list[CheckResult], report: Report) -> list[dict]:
    return [{"label": r.label, "threshold": r.threshold, "actual": r.actual, "status": r.status,
             "status_class": STATUS_CLASSES[r.check.status], "note": r.note,
             "signal": r.check.group == "growth_signal"}
            for r in check_rows(checks, report)]


def build_view(report: Report) -> dict:
    v, e = report.verdict, report.eps_test

    def factors(profile: str) -> list[dict]:
        return [{"name": f.name, "signal": factor_mark(f.supports),
                 "signal_class": SIGNAL_CLASSES[factor_mark(f.supports)], "evidence": f.evidence}
                for f in report.qualitative if f.profile == profile]

    return {
        "report": report,
        "verdict_class": v.label.lower(),
        "value_pct": round((v.value_score or 0) * 100),
        "growth_pct": round((v.growth_score or 0) * 100),
        "confidence_pct": round(v.confidence * 100),
        "profile_rows": profile_rows(report.profile),
        "value_rows": _check_views(report.value_checks, report),
        "growth_rows": _check_views(report.growth_checks, report),
        "eps_rows": eps_rows(e),
        "eps_status": fmt.STATUS_LABELS[e.status],
        "eps_status_class": STATUS_CLASSES[e.status],
        "value_factors": factors("value"),
        "growth_factors": factors("growth"),
        "value_counts": _counts([c.status for c in report.value_checks] + [e.status]),
        "growth_counts": _counts([c.status for c in report.growth_checks]),
        **_price_header(report),
        "charts": report.history,
    }


def _long_date(iso: str | None) -> str | None:
    if not iso:
        return None
    d = date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}, {d.year}"


def _signed_pct(frac: float) -> str:
    return f"{'+' if frac >= 0 else '−'}{abs(frac) * 100:.1f}%"


def _price_header(report: Report) -> dict:
    """Hero price figure, daily change and the stat tiles under it."""
    p, m = report.profile, report.metrics
    stats = report.history.get("stats", {})
    price = stats.get("last") or p.price
    change = stats.get("change_1d")
    tiles = []

    r1y = stats.get("return_1y")
    tiles.append({"label": "1-year return", "value": _signed_pct(r1y) if r1y is not None else "N/A",
                  "delta": ("up" if r1y >= 0 else "down") if r1y is not None else None})
    low, high = stats.get("low_52w"), stats.get("high_52w")
    if low is not None and high is not None and high > low:
        tiles.append({"label": "52-week range", "value": f"${low:,.2f} – ${high:,.2f}",
                      "range_pct": round((price - low) / (high - low) * 100, 1)})
    tiles.append({"label": "Market cap", "value": fmt.money(p.market_cap)})
    pe = m.get("pe")
    tiles.append({"label": "P/E (trailing)", "value": f"{pe:.1f}" if pe and pe > 0 else "N/A"})
    dy = p.dividend_rate / price if p.dividend_rate and price else None
    tiles.append({"label": "Dividend yield", "value": f"{dy * 100:.2f}%" if dy else "None"})

    return {
        "price": f"${price:,.2f}" if price is not None else "N/A",
        "price_currency": p.currency if p.currency and p.currency != "USD" else "",
        "price_date": _long_date(stats.get("last_date")),
        "change_1d": _signed_pct(change) if change is not None else None,
        "change_class": ("up" if change >= 0 else "down") if change is not None else None,
        "tiles": tiles,
    }


def _counts(statuses: list[str]) -> str:
    parts = [
        f"{statuses.count('pass')} passed",
        f"{statuses.count('fail') + statuses.count('sector_typical_fail')} failed",
    ]
    if "na" in statuses:
        parts.append(f"{statuses.count('na')} N/A")
    return " · ".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the stock analyzer web view locally.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--offline-dir", type=Path, help="Serve saved <TICKER>.json fixtures instead of live data.")
    parser.add_argument("--no-browser", action="store_true", help="Don't open a browser tab on start.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING)
    url = f"http://{args.host}:{args.port}"
    print(f"Stock analyzer running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        Timer(1.0, webbrowser.open, [url]).start()
    create_app(args.offline_dir).run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
