import pytest

from stock_analyzer.history import annual_financials, build_history, price_stats
from stock_analyzer.models import CompanyData, CompanyProfile


def test_price_stats():
    prices = {"2024-09-20": 90.0, "2024-09-27": 100.0, "2025-03-28": 80.0, "2025-09-25": 110.0, "2025-09-26": 120.0}
    s = price_stats(prices)
    assert s["last"] == 120.0
    assert s["change_1d"] == pytest.approx(120 / 110 - 1)
    assert s["return_1y"] == pytest.approx(0.2)  # base is the first close within the last 365 days
    assert (s["low_52w"], s["high_52w"]) == (80.0, 120.0)


def test_price_stats_without_a_full_year_has_no_1y_return():
    s = price_stats({"2025-06-01": 10.0, "2025-09-01": 12.0})
    assert s["return_1y"] is None


def test_price_stats_empty():
    assert price_stats({}) == {}


def test_annual_financials_uses_consecutive_years_and_margins():
    data = CompanyData(
        profile=CompanyProfile(ticker="T"),
        income={
            "Total Revenue": {"2022-03-31": 1.0, "2023-12-31": 100.0, "2024-12-31": 200.0},
            "Net Income": {"2023-12-31": 10.0, "2024-12-31": -20.0},
            "Gross Profit": {"2024-12-31": 150.0},
        },
    )
    rows = annual_financials(data)
    assert [r["year"] for r in rows] == ["2023", "2024"]  # 2022 stub period dropped
    assert rows[1]["net_margin"] == pytest.approx(-10.0)
    assert rows[1]["gross_margin"] == pytest.approx(75.0)
    assert rows[0]["gross_margin"] is None


def test_build_history_shape():
    data = CompanyData(profile=CompanyProfile(ticker="T", currency="USD"),
                       price_history={"2025-01-02": 5.0, "2025-01-03": 6.0},
                       eps_history={"2023-12-31": 1.0, "2024-12-31": 1.5}, eps_source="test")
    h = build_history(data)
    assert h["prices"] == [("2025-01-02", 5.0), ("2025-01-03", 6.0)]
    assert [e["eps"] for e in h["eps"]] == [1.0, 1.5]
    assert h["currency"] == "USD"
