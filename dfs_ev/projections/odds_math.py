"""American-odds <-> implied-probability conversion, with vig removal."""
from __future__ import annotations


def american_to_implied_prob(price: int | float) -> float:
    """Convert an American odds price (e.g. -110, +150) to raw implied probability."""
    price = float(price)
    if price == 0:
        raise ValueError("American odds price cannot be 0")
    if price > 0:
        return 100.0 / (price + 100.0)
    return -price / (-price + 100.0)


def implied_prob_to_american(prob: float) -> float:
    if not 0 < prob < 1:
        raise ValueError("probability must be in (0, 1)")
    if prob >= 0.5:
        return -100.0 * prob / (1.0 - prob)
    return 100.0 * (1.0 - prob) / prob


def no_vig_probability(over_price: int | float, under_price: int | float) -> tuple[float, float]:
    """Remove the vig from a two-sided market, returning (p_over, p_under) that sum to 1."""
    p_over_raw = american_to_implied_prob(over_price)
    p_under_raw = american_to_implied_prob(under_price)
    total = p_over_raw + p_under_raw
    if total <= 0:
        raise ValueError("invalid two-sided market prices")
    return p_over_raw / total, p_under_raw / total


def consensus_probability(prices: list[float]) -> float:
    """Average implied probability across books (already vig-adjusted or one-sided)."""
    if not prices:
        raise ValueError("no prices supplied")
    return sum(prices) / len(prices)
