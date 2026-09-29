import pytest

from stock_analyzer.criteria import evaluate_check, load_config, passes
from stock_analyzer.models import CompanyProfile

TECH = CompanyProfile(ticker="T", sector="Technology", industry="Software - Application")
CHIPS = CompanyProfile(ticker="C", sector="Technology", industry="Semiconductors")
BANK = CompanyProfile(ticker="B", sector="Financial Services", industry="Banks - Diversified")


def check(metric, op, threshold, unit="x"):
    return {"id": metric, "label": metric, "metric": metric, "op": op, "threshold": threshold, "unit": unit}


@pytest.mark.parametrize("op,actual,threshold,expected", [
    ("lt", 7.5, 15, True), ("lt", 15, 15, False),
    ("gt", 17.1, 15, True), ("gt", 15, 15, False),
    ("between", 14.7, [10, 25], True), ("between", 25, [10, 25], True), ("between", 30, [10, 25], False),
])
def test_passes(op, actual, threshold, expected):
    assert passes(op, actual, threshold) is expected


def test_missing_value_is_na():
    r = evaluate_check(check("pe", "lt", 15), "value", {"pe": None}, {}, TECH)
    assert r.status == "na"


def test_negative_pe_is_na_not_pass():
    r = evaluate_check(check("pe", "lt", 15), "value", {"pe": -4.0}, {}, TECH)
    assert r.status == "na"


def test_operating_margin_above_range_fails_with_note():
    r = evaluate_check(check("operating_margin", "between", [10, 25], "%"), "growth",
                       {"operating_margin": 40.0}, {}, TECH)
    assert r.status == "fail"
    assert "Above the range" in r.note


def test_semiconductor_inventory_turnover_is_sector_typical():
    c = check("inventory_turnover", "gt", 7.3)
    assert evaluate_check(c, "growth", {"inventory_turnover": 2.17}, {}, CHIPS).status == "sector_typical_fail"
    assert evaluate_check(c, "growth", {"inventory_turnover": 2.17}, {}, TECH).status == "fail"


def test_liquidity_ratios_not_applicable_for_financials():
    r = evaluate_check(check("current_ratio", "gt", 2), "growth", {"current_ratio": 0.7}, {}, BANK)
    assert r.status == "na"
    assert "financial" in r.note


def test_bank_roa_is_sector_typical():
    r = evaluate_check(check("roa", "gt", 4, "%"), "value", {"roa": 0.76}, {}, BANK)
    assert r.status == "sector_typical_fail"


def test_default_config_has_assignment_thresholds():
    cfg = load_config()
    value = {c["id"]: c["threshold"] for c in cfg["value_checks"]}
    growth = {c["id"]: c["threshold"] for c in cfg["growth_checks"]}
    assert value == {"peg": 1, "pe": 15, "pb": 1, "roe": 15, "roa": 4, "de": 1}
    assert growth["operating_margin"] == [10, 25]
    assert growth["inventory_turnover"] == 7.3
    assert cfg["eps_test"]["hurdle"] == 12
