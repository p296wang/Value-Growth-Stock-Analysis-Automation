"""Plain data containers passed between the pipeline stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Annual financial statement: {row name: {fiscal year end (ISO date): value}}
Statement = dict[str, dict[str, float]]


@dataclass
class CompanyProfile:
    ticker: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    country: str | None = None
    currency: str | None = None
    market_cap: float | None = None
    price: float | None = None
    dividend_rate: float | None = None
    employees: int | None = None
    summary: str | None = None


@dataclass
class InsiderTransaction:
    date: str
    insider: str
    position: str
    kind: str  # "buy", "sell" or "other"
    shares: float | None
    value: float | None
    text: str


@dataclass
class CompanyData:
    """Everything fetched for one ticker. Serializable to JSON for offline fixtures."""

    profile: CompanyProfile
    info: dict[str, Any] = field(default_factory=dict)  # raw provider ratios (fractions, as reported)
    income: Statement = field(default_factory=dict)
    balance: Statement = field(default_factory=dict)
    cashflow: Statement = field(default_factory=dict)
    eps_history: dict[str, float] = field(default_factory=dict)  # fiscal year end -> diluted EPS
    eps_source: str = "none"
    price_lows: dict[str, float] = field(default_factory=dict)  # fiscal year end -> lowest price in that year
    price_history: dict[str, float] = field(default_factory=dict)  # date -> close (daily 2y, weekly before)
    growth_estimates: dict[str, float] = field(default_factory=dict)  # e.g. {"+1y": 0.58}
    insiders: list[InsiderTransaction] = field(default_factory=list)
    fetched_at: str = ""
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> CompanyData:
        d = dict(d)
        d["profile"] = CompanyProfile(**d["profile"])
        d["insiders"] = [InsiderTransaction(**t) for t in d.get("insiders", [])]
        return cls(**d)


@dataclass
class CheckResult:
    id: str
    label: str
    group: str  # "value", "growth" or "growth_signal"
    op: str
    threshold: Any
    unit: str
    actual: float | None
    status: str  # "pass", "fail", "sector_typical_fail" or "na"
    rationale: str = ""
    note: str = ""


@dataclass
class EpsTestResult:
    status: str  # "pass", "fail" or "na"
    years: float | None = None
    eps_then: float | None = None
    eps_now: float | None = None
    min_pe: float | None = None
    price: float | None = None
    dividend: float | None = None
    growth_rate: float | None = None  # fraction
    projected_eps: float | None = None
    projected_price: float | None = None
    projected_value: float | None = None
    annual_return: float | None = None  # fraction
    hurdle: float = 0.12
    note: str = ""
    inputs_source: str = ""


@dataclass
class QualitativeFactor:
    name: str
    profile: str  # "value" or "growth"
    supports: bool | None  # None when the evidence is neutral or missing
    evidence: str


@dataclass
class Verdict:
    label: str  # "Value", "Growth", "Both" or "Neither"
    confidence: float
    value_score: float | None
    growth_score: float | None
    lean: str | None
    explanation: str


@dataclass
class Report:
    profile: CompanyProfile
    metrics: dict[str, float | None]
    value_checks: list[CheckResult]
    eps_test: EpsTestResult
    growth_checks: list[CheckResult]
    verdict: Verdict
    qualitative: list[QualitativeFactor]
    caveats: list[str]
    sources: list[str]
    fetched_at: str
    history: dict[str, Any] = field(default_factory=dict)  # chart series, see history.build_history
