"""Rule-based evidence for the qualitative factors in README section 2.4.

Each factor returns supports=True/False, or None when the evidence is neutral or missing.
"""

from __future__ import annotations

from datetime import date, timedelta

from stock_analyzer.formatting import money
from stock_analyzer.models import CompanyData, QualitativeFactor

Metrics = dict[str, float | None]

RECURRING_KEYWORDS = (
    "subscription", "recurring", "interest income", "loan", "lending", "royalt", "insurance",
    "lease", "rent", "long-term contract", "utility", "annuity",
)
COMMODITY_SECTORS = ("Energy", "Basic Materials")
COMMODITY_KEYWORDS = ("oil", "gas", "mining", "gold", "silver", "copper", "steel", "coal", "agricultur", "lumber")
HIGH_GROWTH_KEYWORDS = (
    "semiconductor", "software", "internet", "biotech", "solar", "cloud", "artificial intelligence",
    " ai ", "cybersecurity", "electric vehicle", "medical device", "e-commerce", "data center",
)


def _text(data: CompanyData) -> str:
    p = data.profile
    return f" {p.industry or ''} {p.summary or ''} ".lower()


def _pct(v: float | None) -> str:
    return "N/A" if v is None else f"{v:.1f}%"


# ---- value factors ---------------------------------------------------------------

def small_is_beautiful(data: CompanyData, m: Metrics) -> QualitativeFactor:
    cap = data.profile.market_cap
    name = "Small is Beautiful"
    if cap is None:
        return QualitativeFactor(name, "value", None, "Market capitalization not available.")
    if cap < 2e9:
        return QualitativeFactor(name, "value", True,
            f"Small-cap company ({money(cap)} market cap). Smaller firms are often overlooked by large "
            "institutional investors, which leaves more room for value investors to find mispriced shares.")
    if cap < 10e9:
        return QualitativeFactor(name, "value", None,
            f"Mid-cap company ({money(cap)} market cap): followed by some institutions, but less "
            "closely than large caps.")
    return QualitativeFactor(name, "value", False,
        f"Large-cap company ({money(cap)} market cap). It is widely followed by analysts and big "
        "investors, so the market is less likely to overlook it.")


def annuity_business(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "Annuity Business"
    declines, years = m.get("revenue_declines"), m.get("revenue_years")
    keywords = [k.strip() for k in RECURRING_KEYWORDS if k in _text(data)]
    evidence = []
    if keywords:
        evidence.append(f"the business description points to recurring income ({', '.join(keywords[:3])})")
    if declines is not None:
        evidence.append(f"revenue fell in {declines:.0f} of the last {years - 1:.0f} years")
    if not evidence:
        return QualitativeFactor(name, "value", None, "Not enough revenue history to judge how predictable income is.")
    if keywords and not declines:
        supports = True
        lead = ("Income looks regular and predictable, which value investors like because it holds up "
                "through economic cycles")
    elif declines:
        supports = False
        lead = "Income has not been a steady, recurring stream"
    else:
        supports = None
        lead = "Revenue has been steady, but there is no clear sign it comes from recurring contracts"
    return QualitativeFactor(name, "value", supports, f"{lead}: {'; '.join(evidence)}.")


def durable_competitive_advantage(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "Durable Competitive Advantage"
    gm, nm, roe = m.get("gross_margin"), m.get("net_margin"), m.get("roe")
    if data.profile.sector == "Financial Services":
        if roe is None or nm is None:
            return QualitativeFactor(name, "value", None, "Not enough profitability data.")
        supports = roe >= 12 and nm >= 20
        return QualitativeFactor(name, "value", supports,
            f"ROE of {_pct(roe)} and net margin of {_pct(nm)} "
            + ("suggest it earns above-average returns in its niche, a sign of pricing power."
               if supports else "don't show a clear edge over other financial firms."))
    if gm is None:
        return QualitativeFactor(name, "value", None, "Gross margin not available.")
    supports = gm >= 40 and (nm or 0) >= 10
    return QualitativeFactor(name, "value", supports,
        f"Gross margin of {_pct(gm)} and net margin of {_pct(nm)} "
        + ("show pricing power that competitors haven't eroded, a sign of a moat."
           if supports else "don't point to strong pricing power."))


def revenues_and_commodity(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "Revenues & Commodity"
    p = data.profile
    tied = p.sector in COMMODITY_SECTORS or any(k in (p.industry or "").lower() for k in COMMODITY_KEYWORDS)
    if tied:
        return QualitativeFactor(name, "value", False,
            f"As a {p.industry or p.sector} company, its revenue depends on commodity prices, which makes "
            "earnings harder to predict.")
    return QualitativeFactor(name, "value", True,
        f"Revenue from {p.industry or 'its business'} isn't tied to commodity prices, so earnings are "
        "more predictable.")


def need_for_capital(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "Need for Capital"
    de, capex = m.get("de"), m.get("capex_to_ocf")
    if de is None and capex is None:
        return QualitativeFactor(name, "value", None, "Debt and capital spending data not available.")
    parts, supports = [], True
    if de is not None:
        parts.append(f"debt-to-equity is {de:.2f} (threshold: below 1)")
        supports &= de < 1
    if capex is not None:
        parts.append(f"capital spending uses {capex:.0f}% of operating cash flow")
        supports &= capex < 50
    lead = ("The business funds itself without heavy borrowing or spending" if supports
            else "The business needs significant debt or capital spending")
    return QualitativeFactor(name, "value", supports, f"{lead}: {'; '.join(parts)}.")


def insider_buying(data: CompanyData, m: Metrics, today: date | None = None) -> QualitativeFactor:
    name = "Insider Buying"
    cutoff = ((today or date.today()) - timedelta(days=730)).isoformat()
    recent = [t for t in data.insiders if t.date and t.date >= cutoff]
    if not recent:
        return QualitativeFactor(name, "value", None, "No insider transactions reported in the past two years.")
    buys = [t for t in recent if t.kind == "buy"]
    sells = [t for t in recent if t.kind == "sell"]
    buy_value = sum(t.value or 0 for t in buys)
    sell_value = sum(t.value or 0 for t in sells)
    buyers = sorted({f"{t.insider.title()} ({t.position})" for t in buys})
    summary = (f"In the past two years insiders made {len(buys)} purchases ({money(buy_value)}) "
               f"and {len(sells)} sales ({money(sell_value)}).")
    if buys and buy_value >= sell_value:
        return QualitativeFactor(name, "value", True,
            f"{summary} Buyers include {', '.join(buyers[:3])}. Executives buying with their own money "
            "suggests they believe the stock is undervalued.")
    if buys:
        return QualitativeFactor(name, "value", None,
            f"{summary} Some insiders are buying, but sales outweigh purchases.")
    return QualitativeFactor(name, "value", False,
        f"{summary} No insider buying, so there's no signal that management sees the stock as undervalued.")


# ---- growth factors --------------------------------------------------------------

def market_potential(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "Market Potential"
    rc = m.get("revenue_cagr")
    hits = [k.strip() for k in HIGH_GROWTH_KEYWORDS if k in _text(data)]
    fast = rc is not None and rc > 15
    if not hits and rc is None:
        return QualitativeFactor(name, "growth", None, "Not enough data on the company's market.")
    parts = []
    if hits:
        parts.append(f"it operates in fast-growing areas ({', '.join(hits[:3])})")
    if rc is not None:
        parts.append(f"revenue has grown {_pct(rc)} per year")
    supports = (bool(hits) and (rc is None or rc > 5)) or fast
    lead = ("It has a large, expanding market to grow into" if supports
            else "Its market doesn't look like a fast-growing one")
    return QualitativeFactor(name, "growth", supports, f"{lead}: {'; '.join(parts)}.")


def new_products(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "New Goods/Services & Customer Orientation"
    rdg, rc = m.get("rd_growth"), m.get("revenue_cagr")
    if rdg is None or rc is None:
        return QualitativeFactor(name, "growth", None,
            "Not enough R&D and revenue history to judge the product pipeline.")
    supports = rdg > 10 and rc > 10
    return QualitativeFactor(name, "growth", supports,
        f"R&D spending has grown {_pct(rdg)} per year alongside {_pct(rc)} annual revenue growth, "
        + ("showing that new products are turning into sales." if supports
           else "which doesn't show a strong pipeline of new products turning into sales."))


def research_and_development(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "Research & Development"
    rd = m.get("rd_pct")
    if rd is None:
        return QualitativeFactor(name, "growth", False if data.profile.sector == "Financial Services" else None,
            "No R&D expense reported, so the company isn't investing in new technology through R&D.")
    if rd >= 10:
        return QualitativeFactor(name, "growth", True,
            f"R&D is {_pct(rd)} of revenue, a heavy investment that keeps products competitive and in demand.")
    if rd >= 3:
        return QualitativeFactor(name, "growth", None, f"R&D is {_pct(rd)} of revenue, a moderate investment.")
    return QualitativeFactor(name, "growth", False, f"R&D is only {_pct(rd)} of revenue.")


def profit_margins(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "Profit Margins"
    gm, om, nm = m.get("gross_margin"), m.get("operating_margin"), m.get("net_margin")
    if gm is None and nm is None:
        return QualitativeFactor(name, "growth", None, "Margin data not available.")
    supports = (gm or 0) > 40 and (nm or 0) > 10
    return QualitativeFactor(name, "growth", supports,
        f"Gross {_pct(gm)}, operating {_pct(om)}, net {_pct(nm)}. "
        + ("High margins show customers are willing to pay for its products."
           if supports else "Margins are not high enough to signal strong pricing power."))


def market_share(data: CompanyData, m: Metrics) -> QualitativeFactor:
    name = "Market Share"
    rc, cap = m.get("revenue_cagr"), data.profile.market_cap
    if rc is None:
        return QualitativeFactor(name, "growth", None, "Not enough revenue history to judge market share.")
    if rc > 15 and (cap is None or cap < 200e9):
        return QualitativeFactor(name, "growth", True,
            f"Revenue growth of {_pct(rc)} per year suggests it is taking market share, and at "
            f"{money(cap)} it still has room to expand.")
    if cap is not None and cap >= 200e9:
        return QualitativeFactor(name, "growth", None,
            f"At {money(cap)} it is already a dominant player, so there's less room to gain share "
            f"(revenue growth {_pct(rc)} per year).")
    if rc < 5:
        return QualitativeFactor(name, "growth", False,
            f"Revenue growth of {_pct(rc)} per year suggests it isn't gaining market share.")
    return QualitativeFactor(name, "growth", None, f"Revenue growth of {_pct(rc)} per year is moderate.")


VALUE_FACTORS = (small_is_beautiful, annuity_business, durable_competitive_advantage,
                 revenues_and_commodity, need_for_capital, insider_buying)
GROWTH_FACTORS = (market_potential, new_products, research_and_development, profit_margins, market_share)


def analyze(data: CompanyData, metrics: Metrics) -> list[QualitativeFactor]:
    return [f(data, metrics) for f in VALUE_FACTORS + GROWTH_FACTORS]
