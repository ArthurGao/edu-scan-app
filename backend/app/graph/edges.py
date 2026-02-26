from typing import Literal
from app.graph.state import SolveState
from app.config import get_settings


def should_retry(state: SolveState) -> Literal["retry", "enrich", "fallback"]:
    """Decide whether to retry, fallback, or accept the solution."""
    settings = get_settings()
    score = state.get("quality_score", 0)
    attempts = state.get("attempt_count", 0)
    min_score = settings.min_quality_score
    max_attempts = settings.max_solve_attempts

    if score >= min_score:
        return "enrich"
    elif attempts < max_attempts:
        return "retry"
    else:
        return "fallback"
