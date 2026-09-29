from datetime import date

import pytest

from stock_analyzer.eps_test import eps_test_for, lowest_pe, run_eps_test
from stock_analyzer.models import CompanyData, CompanyProfile


def test_readme_example():
    r = run_eps_test(eps_then=2.00, eps_now=3.00, years=10, min_pe=12, price=18.00, dividend=1.00)
    assert r.growth_rate == pytest.approx(0.0414, abs=1e-4)
    assert r.projected_eps == pytest.approx(4.50)
    assert r.projected_price == pytest.approx(54.00)
    assert r.projected_value == pytest.approx(64.00)
    assert r.annual_return == pytest.approx(0.135, abs=5e-4)
    assert r.status == "pass"


def test_matches_hand_calculated_example():
    r = run_eps_test(eps_then=1.23, eps_now=2.11, years=10, min_pe=5.65, price=10.83, dividend=1.88)
    assert r.growth_rate == pytest.approx(0.0555, abs=1e-4)
    assert r.projected_eps == pytest.approx(3.62, abs=0.01)
    assert r.projected_price == pytest.approx(20.45, abs=0.05)
    assert r.projected_value == pytest.approx(39.25, abs=0.05)
    assert r.annual_return == pytest.approx(0.1374, abs=5e-4)
    assert r.status == "pass"


def test_fails_below_hurdle():
    r = run_eps_test(eps_then=2.0, eps_now=2.1, years=10, min_pe=10, price=30, dividend=0)
    assert r.status == "fail"
    assert r.annual_return < 0.12


@pytest.mark.parametrize("eps_then,eps_now", [(-1.0, 2.0), (1.0, -0.5), (0.0, 1.0)])
def test_undefined_for_non_positive_eps(eps_then, eps_now):
    r = run_eps_test(eps_then, eps_now, 10, 8, 20, 0)
    assert r.status == "na"
    assert "undefined" in r.note


def test_lowest_pe_ignores_loss_years_and_missing_prices():
    eps = {"2020-12-31": -1.0, "2021-12-31": 2.0, "2022-12-31": 4.0, "2023-12-31": 5.0}
    lows = {"2020-12-31": 5.0, "2021-12-31": 20.0, "2022-12-31": 24.0}
    assert lowest_pe(eps, lows) == (6.0, "2022-12-31")


def _data(eps_history, price_lows, trailing_eps=3.0):
    return CompanyData(
        profile=CompanyProfile(ticker="TEST", price=30.0, dividend_rate=1.0),
        info={"trailingEps": trailing_eps},
        eps_history=eps_history,
        price_lows=price_lows,
        eps_source="test",
    )


def test_eps_test_for_skips_leading_loss_years():
    data = _data(
        {"2019-12-31": -0.5, "2020-12-31": 1.0, "2021-12-31": 1.5, "2022-12-31": 2.0, "2023-12-31": 2.5},
        {"2020-12-31": 8.0, "2021-12-31": 15.0, "2022-12-31": 20.0, "2023-12-31": 25.0},
    )
    r = eps_test_for(data, today=date(2025, 12, 31))
    assert r.eps_then == 1.0
    assert r.min_pe == pytest.approx(8.0)
    assert r.years == pytest.approx(5.0, abs=0.1)
    assert "Skipped loss-making years (FY 2019)" in r.note
    assert r.status in ("pass", "fail")


def test_eps_test_for_uses_overrides():
    data = _data({"2023-12-31": 2.0, "2024-12-31": 2.1}, {})
    r = eps_test_for(data, eps_then_override=1.23, min_pe_override=5.65, today=date(2025, 1, 1))
    assert r.years == 10
    assert r.min_pe == 5.65
    assert r.status != "na"


def test_eps_test_for_needs_two_years():
    data = _data({"2024-12-31": 2.0}, {"2024-12-31": 20.0})
    r = eps_test_for(data, today=date(2025, 6, 30))
    assert r.status == "na"
    assert "at least 2" in r.note


def test_eps_test_for_all_losses():
    data = _data({"2023-12-31": -1.0, "2024-12-31": -0.5}, {})
    r = eps_test_for(data, today=date(2025, 6, 30))
    assert r.status == "na"
    assert "losses" in r.note
