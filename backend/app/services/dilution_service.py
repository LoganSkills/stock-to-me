"""Dilution Impact Engine — estimates share dilution and repricing."""

from typing import Optional

from app.schemas.schemas import DilutionImpactOut, OfferingOut


def calc_dilution_impact(
    current_price: Optional[float],
    current_shares: Optional[int],
    offering_shares: Optional[int],
    offering_price: Optional[float],
    warrant_shares: Optional[int],
    warrant_exercise_price: Optional[float],
    atm_capacity: Optional[int],
    current_market_cap: Optional[float] = None,
) -> DilutionImpactOut:
    """
    Calculate dilution impact for a financing event.

    If current_market_cap is not provided, derives it from price × shares.
    Scenario multipliers applied per spec:
      mild: 0.95, moderate: 0.85, severe: 0.70
    """

    # Derive market cap
    if current_market_cap is None and current_price and current_shares:
        current_market_cap = current_price * current_shares

    immediate_dilution_pct = None
    potential_total_dilution_pct = None
    new_shares_outstanding = None
    theoretical_price = None
    theoretical_price_mild = None
    theoretical_price_moderate = None
    theoretical_price_severe = None
    warrant_overhang_notes = None

    offering_terms = None
    if offering_shares and current_shares and current_shares > 0:
        immediate_dilution_pct = (offering_shares / current_shares) * 100
        new_shares_outstanding = current_shares + offering_shares

        if current_market_cap and new_shares_outstanding > 0:
            theoretical_price = current_market_cap / new_shares_outstanding
            theoretical_price_mild = theoretical_price * 0.95
            theoretical_price_moderate = theoretical_price * 0.85
            theoretical_price_severe = theoretical_price * 0.70

    # Total dilution including warrants and ATM
    total_new_shares = offering_shares or 0
    if warrant_shares:
        total_new_shares += warrant_shares
    if atm_capacity:
        total_new_shares += atm_capacity

    if total_new_shares and current_shares and current_shares > 0:
        potential_total_dilution_pct = (total_new_shares / current_shares) * 100

    if warrant_shares and warrant_exercise_price and current_price:
        in_the_money = warrant_exercise_price <= current_price
        if in_the_money:
            warrant_overhang_notes = (
                f"Warrants ({warrant_shares:,} shares) are in-the-money "
                f"at ${warrant_exercise_price:.2f} vs current ${current_price:.2f}. "
                "Exercise would add significant supply."
            )
        else:
            warrant_overhang_notes = (
                f"Warrants ({warrant_shares:,} shares) are out-of-the-money "
                f"at ${warrant_exercise_price:.2f} vs current ${current_price:.2f}. "
                "Near-term exercise unlikely but overhang may cap upside."
            )

    if offering_price and current_price:
        offering_terms = OfferingOut(
            id=0,
            company_id=0,
            offering_type="direct_offering",
            announced_at=None,
            offering_price=offering_price,
            shares_offered=offering_shares,
            gross_proceeds=int(offering_shares * offering_price) if offering_shares and offering_price else None,
            warrant_shares=warrant_shares,
            warrant_exercise_price=warrant_exercise_price,
            atm_capacity_remaining=atm_capacity,
            convertible_principal=None,
            convertible_conversion_price=None,
        )

    return DilutionImpactOut(
        company_id=0,
        ticker="",
        current_price=current_price,
        current_shares=current_shares,
        current_market_cap=current_market_cap,
        immediate_dilution_pct=immediate_dilution_pct,
        potential_total_dilution_pct=potential_total_dilution_pct,
        new_shares_outstanding=new_shares_outstanding,
        theoretical_price=theoretical_price,
        theoretical_price_mild=theoretical_price_mild,
        theoretical_price_moderate=theoretical_price_moderate,
        theoretical_price_severe=theoretical_price_severe,
        warrant_overhang_notes=warrant_overhang_notes,
        offering_terms=offering_terms,
    )
