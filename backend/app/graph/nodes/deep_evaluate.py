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
        content = result.content

        # Gemini thinking models may return empty content with output in thinking field
        if not content or not content.strip():
            logger.warning("deep_evaluate: empty content from model, skipping")
            return None

        # Strip markdown code fences if present
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("```", 2)[1]
            if stripped.startswith("json"):
                stripped = stripped[4:]
            stripped = stripped.rsplit("```", 1)[0].strip()

        # Extract JSON object if there's surrounding text
        start, end = stripped.find("{"), stripped.rfind("}") + 1
        if start >= 0 and end > start:
            stripped = stripped[start:end]

        parsed = json.loads(stripped)

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
