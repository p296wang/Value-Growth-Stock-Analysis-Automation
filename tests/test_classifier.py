import pytest

from stock_analyzer.classifier import classify, score_statuses
from stock_analyzer.models import CheckResult, EpsTestResult


def checks(*statuses, group="value"):
    return [CheckResult(id=str(i), label=str(i), group=group, op="gt", threshold=0, unit="",
                        actual=1.0, status=s) for i, s in enumerate(statuses)]


def test_score_excludes_na_and_gives_partial_credit():
    s = score_statuses(["pass", "fail", "sector_typical_fail", "na"], sector_typical_weight=0.5)
    assert s.score == pytest.approx(1.5 / 3)
    assert (s.passed, s.evaluated, s.total) == (1, 3, 4)


def test_score_with_nothing_evaluated():
    assert score_statuses(["na", "na"]).score is None


@pytest.mark.parametrize("value,growth,expected", [
    (["pass"] * 5 + ["fail"], ["fail"] * 5 + ["pass"], "Value"),
    (["fail"] * 5 + ["pass"], ["pass"] * 8 + ["fail"], "Growth"),
    (["pass"] * 6, ["pass"] * 8, "Both"),
    (["fail"] * 6, ["fail"] * 8, "Neither"),
])
def test_verdicts(value, growth, expected):
    v = classify(checks(*value), EpsTestResult(status="na"), checks(*growth, group="growth"))
    assert v.label == expected
    assert 0 < v.confidence <= 1


def test_eps_test_counts_toward_value():
    value = checks("pass", "pass", "fail", "fail")  # 50% without the test
    growth = checks("fail", "fail", group="growth")
    assert classify(value, EpsTestResult(status="na"), growth).label == "Neither"
    assert classify(value, EpsTestResult(status="pass"), growth).label == "Value"  # 3/5 = 60%


def test_missing_data_lowers_confidence():
    full = classify(checks("pass", "pass", "pass"), EpsTestResult(status="pass"), checks("fail", "fail", group="growth"))
    sparse = classify(checks("pass", "na", "na"), EpsTestResult(status="na"), checks("fail", "na", group="growth"))
    assert full.label == sparse.label == "Value"
    assert sparse.confidence < full.confidence
    assert "couldn't be evaluated" in sparse.explanation


def test_price_gate_blocks_value_for_expensive_quality_stock():
    # Passes ROE/ROA/D/E but only 1 of the 3 price checks (like NVDA)
    value = [CheckResult(id=i, label=f"x ({i.upper()})", group="value", op="lt", threshold=1, unit="",
                         actual=1.0, status=s)
             for i, s in (("peg", "pass"), ("pe", "fail"), ("pb", "fail"),
                          ("roe", "pass"), ("roa", "pass"), ("de", "pass"))]
    growth = checks("fail", "fail", group="growth")
    ungated = classify(value, EpsTestResult(status="pass"), growth)
    gated = classify(value, EpsTestResult(status="pass"), growth, value_price_gate=(["peg", "pe", "pb"], 2))
    assert ungated.label == "Value"
    assert gated.label == "Neither"
    assert "isn't cheap enough" in gated.explanation


def test_min_coverage_blocks_sparse_profile():
    # 3/5 evaluated growth checks pass, but 6 of 11 are N/A (like a bank)
    growth = checks("pass", "pass", "pass", "fail", "fail", *["na"] * 6, group="growth")
    value = checks("fail", "fail", "fail")
    assert classify(value, EpsTestResult(status="fail"), growth).label == "Growth"
    blocked = classify(value, EpsTestResult(status="fail"), growth, min_coverage=0.5)
    assert blocked.label == "Neither"
    assert "Too few growth checks" in blocked.explanation


def test_tie_breaks_on_revenue_growth():
    value, growth = checks("pass", "fail"), checks("pass", "fail", group="growth")
    assert classify(value, EpsTestResult(status="na"), growth, revenue_cagr=25).lean == "Growth"
    assert classify(value, EpsTestResult(status="na"), growth, revenue_cagr=2).lean == "Value"
