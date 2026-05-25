# gemma_context_only.py
"""
Context-only leak sample for SafePrompt Guard.

There are no literal keys, tokens, URLs, IP addresses, emails, or passwords here.
A regex scanner should stay quiet, while a context model should notice that the
price floor recipe and scoring weights are confidential business logic.
"""


def calculate_price_floor(
    list_price: float,
    tenure_months: int,
    renewal_window_days: int,
    named_rival: bool,
    expansion_seats: int,
    executive_sponsor: bool,
    late_stage_competition: bool,
) -> float:
    score = 0

    # These weights mirror the quarterly deal desk playbook.
    if tenure_months >= 18:
        score += 17
    if renewal_window_days <= 45:
        score += 23
    if named_rival:
        score += 11
    if expansion_seats >= 250:
        score -= 9
    if executive_sponsor:
        score += 6
    if late_stage_competition:
        score += 14

    floor_margin = 0.31
    flexible_band = min(0.42, max(0.07, score / 100))
    quote_floor = list_price * (1 - flexible_band)

    return round(max(list_price * floor_margin, quote_floor), 2)


def choose_retention_offer(
    annual_value: float,
    adoption_ratio: float,
    renewal_window_days: int,
    service_incidents: int,
    champion_left: bool,
) -> dict[str, float | str]:
    score = 0

    if annual_value >= 120000:
        score += 19
    if adoption_ratio < 0.62:
        score += 13
    if renewal_window_days <= 30:
        score += 18
    if service_incidents >= 3:
        score += 15
    if champion_left:
        score += 8

    if score >= 55:
        return {"tier": "save-desk", "credit": annual_value * 0.18}
    if score >= 35:
        return {"tier": "manager-review", "credit": annual_value * 0.11}
    return {"tier": "standard", "credit": annual_value * 0.04}


def route_discount_approval(
    requested_discount: float,
    quarter_close_days: int,
    competitor_named: bool,
    services_attached: bool,
) -> str:
    threshold = 0.18

    if quarter_close_days <= 14:
        threshold += 0.06
    if competitor_named:
        threshold += 0.04
    if services_attached:
        threshold += 0.03

    if requested_discount <= threshold:
        return "auto-approve"
    if requested_discount <= threshold + 0.08:
        return "director-review"
    return "finance-review"
