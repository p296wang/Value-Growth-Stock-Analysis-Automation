"""The 10-Year EPS Test from the COMM 101 assignment (README section 2.2)."""

from __future__ import annotations

from datetime import date

from stock_analyzer.models import CompanyData, EpsTestResult
from stock_analyzer.ratios import annual_run, years_between


def run_eps_test(
    eps_then: float,
    eps_now: float,
    years: float,
    min_pe: float,
    price: float,
    dividend: float,
    hurdle: float = 0.12,
) -> EpsTestResult:
    """Project the share value `years` ahead and compute the annual compound return from today's price.

    1. growth = (eps_now / eps_then) ** (1 / years) - 1
    2. projected EPS = eps_now * (1 + growth) ** years
    3. projected price = lowest historical P/E * projected EPS
    4. projected value = projected price + years * current dividend (held flat)
    5. annual return = (projected value / price) ** (1 / years) - 1
    """
    result = EpsTestResult(status="na", years=years, eps_then=eps_then, eps_now=eps_now,
                           min_pe=min_pe, price=price, dividend=dividend, hurdle=hurdle)
    if eps_then <= 0 or eps_now <= 0:
        result.note = "EPS growth rate is undefined when either EPS value is zero or negative."
        return result
    if price <= 0 or min_pe <= 0 or years <= 0:
        result.note = "Price, lowest P/E and number of years must be positive."
        return result

    growth = (eps_now / eps_then) ** (1 / years) - 1
    projected_eps = eps_now * (1 + growth) ** years
    projected_price = min_pe * projected_eps
    projected_value = projected_price + years * dividend
    annual_return = (projected_value / price) ** (1 / years) - 1

    result.growth_rate = growth
    result.projected_eps = projected_eps
    result.projected_price = projected_price
    result.projected_value = projected_value
    result.annual_return = annual_return
    result.status = "pass" if annual_return >= hurdle else "fail"
    return result


def lowest_pe(eps_history: dict[str, float], price_lows: dict[str, float]) -> tuple[float | None, str | None]:
    """Lowest annual P/E: each fiscal year's lowest price / that year's EPS (profitable years only)."""
    candidates = [
        (price_lows[end] / eps, end)
        for end, eps in eps_history.items()
        if eps > 0 and end in price_lows
    ]
    if not candidates:
        return None, None
    return min(candidates)


def eps_test_for(
    data: CompanyData,
    hurdle: float = 0.12,
    max_years: int = 10,
    eps_then_override: float | None = None,
    min_pe_override: float | None = None,
    today: date | None = None,
) -> EpsTestResult:
    """Pick inputs from the fetched data (or overrides) and run the test over up to `max_years`."""
    today = today or date.today()
    today_iso = today.isoformat()
    price = data.profile.price
    dividend = data.profile.dividend_rate or 0.0
    history = {
        end: eps for end, eps in annual_run(list(data.eps_history.items()))
        if years_between(end, today_iso) <= max_years + 0.5
    }
    skipped_losses = []
    while history and next(iter(history.values())) <= 0 and eps_then_override is None:
        # growth from a loss is undefined, so start from the first profitable year
        skipped_losses.append(next(iter(history))[:4])
        history.pop(next(iter(history)))

    eps_now = data.info.get("trailingEps")
    now_label = "trailing 12-month EPS"
    if eps_now is None and history:
        eps_now = list(history.values())[-1]
        now_label = f"FY {list(history)[-1][:4]} EPS"

    if eps_then_override is not None:
        eps_then, years = eps_then_override, float(max_years)
        then_label = "EPS 10 years ago (user input)"
    elif history:
        then_end, eps_then = next(iter(history.items()))
        years = round(years_between(then_end, today_iso), 1)
        then_label = f"FY {then_end[:4]} EPS ({data.eps_source})"
    else:
        note = "No EPS history available."
        if skipped_losses:
            note = f"The company had losses in every year with data (FY {', '.join(skipped_losses)})."
        return EpsTestResult(status="na", hurdle=hurdle, eps_now=eps_now, price=price, dividend=dividend, note=note)

    if min_pe_override is not None:
        min_pe, pe_label = min_pe_override, "lowest P/E (user input)"
    else:
        min_pe, pe_year = lowest_pe(history, data.price_lows)
        pe_label = f"lowest P/E in FY {pe_year[:4]}" if pe_year else ""

    missing = [name for name, v in (("current EPS", eps_now), ("lowest P/E", min_pe), ("price", price)) if v is None]
    if missing:
        return EpsTestResult(status="na", eps_then=eps_then, eps_now=eps_now, min_pe=min_pe, price=price,
                             dividend=dividend, years=years, hurdle=hurdle,
                             note=f"Missing inputs: {', '.join(missing)}.")
    loss_note = f"Skipped loss-making years (FY {', '.join(skipped_losses)}). " if skipped_losses else ""
    if years < 2:
        return EpsTestResult(status="na", eps_then=eps_then, eps_now=eps_now, min_pe=min_pe, price=price,
                             dividend=dividend, years=years, hurdle=hurdle,
                             note=f"{loss_note}Only {years:.1f} years of usable EPS history; at least 2 are needed.")

    result = run_eps_test(eps_then, eps_now, years, min_pe, price, dividend, hurdle)
    result.inputs_source = f"{then_label}; {now_label}; {pe_label}"
    notes = [loss_note.strip()] if loss_note else []
    if years < max_years - 0.5 and eps_then_override is None and result.status != "na":
        notes.append(f"Only {years:.1f} years of EPS history available, so this is a shorter test than 10 years.")
    if result.note:
        notes.append(result.note)
    result.note = " ".join(notes)
    return result
