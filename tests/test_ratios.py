from pathlib import Path

import pytest

from stock_analyzer.data.provider import load_fixture
from stock_analyzer.data.sec_edgar import parse_annual_eps
from stock_analyzer.models import CompanyData, CompanyProfile
from stock_analyzer.ratios import annual_run, cagr, compute_metrics

FIXTURES = Path(__file__).parent / "fixtures"


def test_cagr_basic():
    pts = [("2020-12-31", 100.0), ("2021-12-31", 110.0), ("2022-12-31", 121.0)]
    assert cagr(pts) == pytest.approx(0.10, abs=1e-3)


def test_cagr_undefined_for_non_positive_base():
    assert cagr([("2020-12-31", -5.0), ("2021-12-31", 10.0)]) is None


def test_annual_run_drops_points_before_irregular_gap():
    pts = [("2022-03-31", 1.0), ("2023-12-31", 10.0), ("2024-12-31", 18.0), ("2025-12-31", 40.0)]
    assert [d for d, _ in annual_run(pts)] == ["2023-12-31", "2024-12-31", "2025-12-31"]


def test_metrics_from_info_and_statements():
    data = CompanyData(
        profile=CompanyProfile(ticker="T", price=50.0, market_cap=1e9),
        info={"trailingPE": 20.0, "debtToEquity": 45.0, "returnOnEquity": 0.18, "grossMargins": 0.5},
        income={"Total Revenue": {"2023-12-31": 800.0, "2024-12-31": 1000.0},
                "Cost Of Revenue": {"2024-12-31": 500.0},
                "Research And Development": {"2024-12-31": 150.0}},
        balance={"Accounts Receivable": {"2023-12-31": 90.0, "2024-12-31": 110.0},
                 "Inventory": {"2023-12-31": 40.0, "2024-12-31": 60.0},
                 "Current Assets": {"2024-12-31": 600.0},
                 "Current Liabilities": {"2024-12-31": 200.0}},
        growth_estimates={"+1y": 0.25},
    )
    m, notes = compute_metrics(data)
    assert m["de"] == pytest.approx(0.45)  # yfinance reports D/E as a percent
    assert m["roe"] == pytest.approx(18.0)
    assert m["gross_margin"] == pytest.approx(50.0)
    assert m["ar_turnover"] == pytest.approx(10.0)
    assert m["inventory_turnover"] == pytest.approx(10.0)
    assert m["working_capital"] == 400.0
    assert m["current_ratio"] == pytest.approx(3.0)
    assert m["rd_pct"] == pytest.approx(15.0)
    assert m["revenue_cagr"] == pytest.approx(25.0, abs=0.2)
    assert m["peg"] == pytest.approx(20.0 / 25.0)
    assert "next-year" in notes["peg"]


def test_negative_earnings_leave_pe_undefined():
    data = CompanyData(profile=CompanyProfile(ticker="T", price=10.0), info={"trailingEps": -1.2})
    m, notes = compute_metrics(data)
    assert m["pe"] is None
    assert "not profitable" in notes["pe"]


def test_fixture_metrics_alab():
    m, _ = compute_metrics(load_fixture(FIXTURES / "ALAB.json"))
    assert m["gross_margin"] > 40
    assert m["de"] < 1
    assert m["inventory_turnover"] is not None


def test_parse_sec_annual_eps_keeps_full_years_and_latest_filing():
    facts = {"facts": {"us-gaap": {"EarningsPerShareDiluted": {"units": {"USD/shares": [
        {"start": "2022-01-01", "end": "2022-12-31", "val": 1.0, "form": "10-K", "filed": "2023-02-01"},
        {"start": "2022-01-01", "end": "2022-12-31", "val": 1.1, "form": "10-K", "filed": "2024-02-01"},
        {"start": "2023-10-01", "end": "2023-12-31", "val": 0.4, "form": "10-K", "filed": "2024-02-01"},
        {"start": "2023-01-01", "end": "2023-12-31", "val": 1.5, "form": "10-K", "filed": "2024-02-01"},
        {"start": "2023-01-01", "end": "2023-12-31", "val": 9.9, "form": "8-K", "filed": "2024-01-15"},
    ]}}}}}
    eps = parse_annual_eps(facts)
    assert [(e.end, e.eps) for e in eps] == [("2022-12-31", 1.1), ("2023-12-31", 1.5)]
