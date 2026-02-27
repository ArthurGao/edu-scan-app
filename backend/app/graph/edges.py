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


def should_retry_after_verify(state: SolveState) -> Literal["enrich", "solve", "caution"]:
    """Decide next step based on quick_verify results."""
    verify_passed = state.get("verify_passed")
    verify_confidence = state.get("verify_confidence", 0.0)
    attempt_count = state.get("attempt_count", 0)

    # Verified correct with high confidence
    if verify_passed is True and verify_confidence >= 0.8:
        return "enrich"

    # Verification skipped (timeout, error, low confidence)
    if verify_passed is None:
        return "enrich"

    # Verification failed — retry with different provider if attempts remain
    if attempt_count < 2:
        return "solve"

    # Max retries reached — return with caution flag
    return "caution"
