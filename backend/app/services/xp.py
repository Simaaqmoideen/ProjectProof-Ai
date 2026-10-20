"""Business rule BR-1: XP calculation.

Formula: round(min(cap, base_per_day * duration_days * difficulty_multiplier * evaluation_multiplier))
See docs/01-product-requirements.md BR-1.
"""
from app.config import settings


def get_evaluation_multiplier(overall_score: int) -> float:
    if overall_score < 60:
        raise ValueError("Overall score below 60 cannot be approved")
    elif overall_score < 75:
        return settings.evaluation_multipliers.get("tier1", 1.0)
    elif overall_score < 90:
        return settings.evaluation_multipliers.get("tier2", 1.1)
    else:
        return settings.evaluation_multipliers.get("tier3", 1.2)


def compute_xp(duration_days: int, difficulty: str, overall_score: int) -> int:
    """Compute XP awarded for project completion according to BR-1."""
    eval_mult = get_evaluation_multiplier(overall_score)
    diff_mult = settings.difficulty_multiplier.get(difficulty.lower(), 1.0)
    base = settings.xp_base_per_day
    cap = settings.xp_cap
    raw = base * duration_days * diff_mult * eval_mult
    return round(min(float(cap), raw))


def compute_max_xp(duration_days: int, difficulty: str) -> int:
    """Compute maximum XP possible (assuming max evaluation multiplier 1.2)."""
    diff_mult = settings.difficulty_multiplier.get(difficulty.lower(), 1.0)
    base = settings.xp_base_per_day
    cap = settings.xp_cap
    raw = base * duration_days * diff_mult * 1.2
    return round(min(float(cap), raw))
