import json
import logging

from app.llm.registry import get_llm
from app.llm.prompts.deep_evaluate import build_deep_evaluate_messages

logger = logging.getLogger(__name__)


async def run_deep_evaluate(
    problem_text: str,
    solution_raw: str,
    final_answer: str,
    steps: list,
    subject: str = "math",
    grade_level: str = "middle school",
) -> dict | None:
    """Run asynchronous deep evaluation using Gemini.

    This is called as a background task after the response is returned to the user.
    Returns the evaluation dict, or None on failure.
    """
    try:
        llm = get_llm("evaluate", "gemini")
        messages = build_deep_evaluate_messages(
            problem_text=problem_text,
            solution_raw=solution_raw,
            final_answer=final_answer,
            steps=steps,
            subject=subject,
            grade_level=grade_level,
        )

        result = await llm.ainvoke(messages)
        parsed = json.loads(result.content)

        # Validate expected fields
        expected_fields = [
            "correctness", "completeness", "clarity",
            "pedagogy", "format", "overall",
        ]
        for field in expected_fields:
            if field not in parsed:
                parsed[field] = 0.0

        return parsed

    except Exception as e:
        logger.warning("deep_evaluate failed: %s", e)
        return None
