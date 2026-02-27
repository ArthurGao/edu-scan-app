import asyncio
import json
import logging

from app.graph.state import SolveState
from app.llm.registry import get_llm
from app.llm.prompts.verify import build_verify_messages

logger = logging.getLogger(__name__)

VERIFY_TIMEOUT_SECONDS = 5.0


async def quick_verify_node(state: SolveState) -> dict:
    """Synchronous answer verification using Gemini.

    Independently verifies the final answer correctness.
    On timeout or error, gracefully skips (returns verify_passed=None).
    """
    final_answer = ""
    steps_summary = ""

    solution_parsed = state.get("solution_parsed", {})
    if solution_parsed:
        final_answer = solution_parsed.get("final_answer", "")
        steps = solution_parsed.get("steps", [])
        steps_summary = "\n".join(
            f"{s.get('step', '')}. {s.get('description', '')}"
            for s in steps
        )

    if not final_answer:
        # No answer to verify
        return {
            "verify_passed": None,
            "verify_confidence": 0.0,
            "independent_answer": None,
            "verify_error": "no_answer_to_verify",
        }

    try:
        llm = get_llm("verify", "gemini")
        messages = build_verify_messages(
            problem_text=state.get("ocr_text", ""),
            final_answer=final_answer,
            steps_summary=steps_summary,
            subject=state.get("detected_subject", "math"),
        )

        result = await asyncio.wait_for(
            llm.ainvoke(messages),
            timeout=VERIFY_TIMEOUT_SECONDS,
        )

        parsed = json.loads(result.content)
        is_correct = parsed.get("is_correct", False)
        confidence = float(parsed.get("confidence", 0.0))

        # Low confidence treated as uncertain
        if confidence < 0.6:
            verify_passed = None
        else:
            verify_passed = is_correct

        return {
            "verify_passed": verify_passed,
            "verify_confidence": confidence,
            "independent_answer": parsed.get("independent_answer"),
            "verify_error": parsed.get("error_description"),
        }

    except asyncio.TimeoutError:
        logger.warning("quick_verify timed out after %ss", VERIFY_TIMEOUT_SECONDS)
        return {
            "verify_passed": None,
            "verify_confidence": 0.0,
            "independent_answer": None,
            "verify_error": "timeout",
        }
    except Exception as e:
        logger.warning("quick_verify failed: %s", e)
        return {
            "verify_passed": None,
            "verify_confidence": 0.0,
            "independent_answer": None,
            "verify_error": str(e),
        }
