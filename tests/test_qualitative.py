from datetime import date

from stock_analyzer import qualitative as q
from stock_analyzer.models import CompanyData, CompanyProfile, InsiderTransaction


def company(**profile):
    return CompanyData(profile=CompanyProfile(ticker="T", **profile))


def test_small_cap_supports_value():
    assert q.small_is_beautiful(company(market_cap=5e8), {}).supports is True
    assert q.small_is_beautiful(company(market_cap=5e10), {}).supports is False
    assert q.small_is_beautiful(company(), {}).supports is None


def test_commodity_sector_is_against_value():
    assert q.revenues_and_commodity(company(sector="Energy", industry="Oil & Gas E&P"), {}).supports is False
    assert q.revenues_and_commodity(company(sector="Technology", industry="Software"), {}).supports is True


def test_insider_buying():
    data = company()
    data.insiders = [
        InsiderTransaction("2025-05-01", "DOE JANE", "CEO", "buy", 1000, 50_000, ""),
        InsiderTransaction("2025-06-01", "ROE RICH", "CFO", "sell", 100, 10_000, ""),
        InsiderTransaction("2020-01-01", "OLD SALE", "CFO", "sell", 100, 9e9, ""),  # outside 2-year window
    ]
    f = q.insider_buying(data, {}, today=date(2025, 12, 31))
    assert f.supports is True
    assert "Doe Jane (CEO)" in f.evidence


def test_no_insider_data_is_neutral():
    assert q.insider_buying(company(), {}, today=date(2025, 12, 31)).supports is None


def test_annuity_business_uses_keywords_and_declines():
    lender = company(summary="A specialty finance company earning interest income from loans.")
    assert q.annuity_business(lender, {"revenue_declines": 0.0, "revenue_years": 4.0}).supports is True
    assert q.annuity_business(company(summary="Makes widgets."), {"revenue_declines": 2.0, "revenue_years": 4.0}).supports is False


def test_rd_intensity():
    assert q.research_and_development(company(), {"rd_pct": 25.0}).supports is True
    assert q.research_and_development(company(), {"rd_pct": 1.0}).supports is False


def test_analyze_returns_all_factors():
    factors = q.analyze(company(market_cap=1e9), {})
    assert len([f for f in factors if f.profile == "value"]) == 6
    assert len([f for f in factors if f.profile == "growth"]) == 5
