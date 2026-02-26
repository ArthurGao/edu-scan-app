import json
from app.graph.state import SolveState
from app.llm.registry import get_llm
from app.llm.prompts.evaluate import build_evaluate_messages


async def evaluate_node(state: SolveState) -> dict:
    """Auto-grade the solution quality."""
    attempt_count = state.get("attempt_count", 0)

    try:
        llm = get_llm("fast")
        messages = build_evaluate_messages(
            problem_text=state.get("ocr_text", ""),
            solution=state.get("solution_raw", ""),
            subject=state.get("detected_subject", "math"),
            grade_level=state.get("grade_level", "middle school"),
        )
        result = await llm.ainvoke(messages)
        parsed = json.loads(result.content)

        return {
            "quality_score": parsed.get("overall", 0.5),
            "quality_issues": parsed.get("issues", []),
            "attempt_count": attempt_count + 1,
        }
    except Exception:
        return {
            "quality_score": 0.75,
            "quality_issues": ["evaluation_failed"],
            "attempt_count": attempt_count + 1,
        }
