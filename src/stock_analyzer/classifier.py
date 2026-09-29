"""Turns checklist results into a Value / Growth / Both / Neither verdict with a confidence score."""

from __future__ import annotations

from dataclasses import dataclass

from stock_analyzer.models import CheckResult, EpsTestResult, Verdict


@dataclass
class Score:
    score: float | None  # weighted pass rate over evaluated checks, 0-1
    passed: int
    evaluated: int
    total: int


def score_statuses(statuses: list[str], sector_typical_weight: float = 0.5) -> Score:
    weights = {"pass": 1.0, "sector_typical_fail": sector_typical_weight, "fail": 0.0}
    evaluated = [s for s in statuses if s in weights]
    passed = sum(1 for s in evaluated if s == "pass")
    if not evaluated:
        return Score(None, 0, 0, len(statuses))
    return Score(sum(weights[s] for s in evaluated) / len(evaluated), passed, len(evaluated), len(statuses))


def classify(
    value_checks: list[CheckResult],
    eps_test: EpsTestResult,
    growth_checks: list[CheckResult],
    verdict_threshold: float = 0.6,
    sector_typical_weight: float = 0.5,
    revenue_cagr: float | None = None,
    min_coverage: float = 0.0,
    value_price_gate: tuple[list[str], int] | None = None,
) -> Verdict:
    value = score_statuses([c.status for c in value_checks] + [eps_test.status], sector_typical_weight)
    growth = score_statuses([c.status for c in growth_checks], sector_typical_weight)
    v = value.score if value.score is not None else 0.0
    g = growth.score if growth.score is not None else 0.0
    t = verdict_threshold

    blockers = []
    value_ok = value.total > 0 and value.evaluated / value.total >= min_coverage
    growth_ok = growth.total > 0 and growth.evaluated / growth.total >= min_coverage
    if not value_ok and v >= t:
        blockers.append(f"Too few value checks could be evaluated ({value.evaluated}/{value.total}) "
                        "to call it a value stock.")
    if not growth_ok and g >= t:
        blockers.append(f"Too few growth checks could be evaluated ({growth.evaluated}/{growth.total}) "
                        "to call it a growth stock.")
    if value_price_gate is not None:
        gate_ids, min_pass = value_price_gate
        gate = [c for c in value_checks if c.id in gate_ids]
        gate_passed = sum(1 for c in gate if c.status == "pass")
        if gate_passed < min_pass:
            value_ok = False
            if v >= t:
                names = ", ".join(c.label.split(" (")[-1].rstrip(")") for c in gate)
                blockers.append(f"Only {gate_passed} of {len(gate)} price checks ({names}) passed, so the stock "
                                "isn't cheap enough to count as a value stock despite its quality ratios.")

    evaluated = value.evaluated + growth.evaluated
    total = value.total + growth.total
    coverage = evaluated / total if total else 0.0
    coverage_factor = 0.7 + 0.3 * coverage  # missing data lowers confidence

    if abs(v - g) >= 0.05:
        lean = "Value" if v > g else "Growth"
    else:  # near tie: fall back on sales growth, the clearest growth signal
        lean = "Growth" if revenue_cagr is not None and revenue_cagr > 10 else "Value"

    is_value, is_growth = v >= t and value_ok, g >= t and growth_ok
    # Single-profile confidence: how clearly the winner beats the other profile or clears the threshold
    if is_value and not is_growth:
        label, strength = "Value", min(1.0, max((v - g) / 0.5, (v - t) / max(1 - t, 1e-9)))
    elif is_growth and not is_value:
        label, strength = "Growth", min(1.0, max((g - v) / 0.5, (g - t) / max(1 - t, 1e-9)))
    elif is_value and is_growth:
        label, strength = "Both", min(1.0, (min(v, g) - t) / (1 - t)) if t < 1 else 1.0
    else:
        label, strength = "Neither", min(1.0, (t - max(v, g)) / t) if t > 0 else 1.0
    strength = max(0.0, strength)
    confidence = round((0.5 + 0.5 * strength) * coverage_factor, 2)

    summary = (
        f"Value checklist: {value.passed}/{value.evaluated} passed (score {v:.0%}). "
        f"Growth checklist: {growth.passed}/{growth.evaluated} passed (score {g:.0%}). "
        f"A profile needs a score of at least {t:.0%}."
    )
    if blockers:
        summary += " " + " ".join(blockers)
    if label == "Value":
        explanation = f"{summary} The stock fits the value profile and not the growth profile."
    elif label == "Growth":
        explanation = f"{summary} The stock fits the growth profile and not the value profile."
    elif label == "Both":
        explanation = f"{summary} It fits both profiles (growth at a reasonable price), leaning {lean.lower()}."
    else:
        explanation = f"{summary} It doesn't clearly fit either profile; the closer fit is {lean.lower()}."
    if evaluated < total:
        explanation += f" {total - evaluated} of {total} checks couldn't be evaluated and were left out."

    return Verdict(
        label=label,
        confidence=confidence,
        value_score=value.score,
        growth_score=growth.score,
        lean=lean if label in ("Both", "Neither") else label,
        explanation=explanation,
    )
