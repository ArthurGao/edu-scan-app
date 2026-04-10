import json
from app.graph.state import SolveState
from app.llm.registry import get_llm, select_llm, SUBJECT_PROVIDER_MAP
from app.llm.prompts.solve import build_solve_messages
from app.llm.prompts.framework import build_solve_with_framework_messages


def _build_context(formulas: list[dict], similar_problems: list[dict]) -> str:
    """Build context string from retrieved formulas and similar problems."""
    parts = []
    if formulas:
        parts.append("## Related Formulas")
        for f in formulas:
            parts.append(f"- **{f.get('name', '')}**: `{f.get('latex', '')}` — {f.get('description', '')}")
    if similar_problems:
        parts.append("\n## Similar Problems (for reference)")
        for p in similar_problems:
            parts.append(f"- {p.get('ocr_text', '')[:200]}")
    return "\n".join(parts)


async def solve_node(state: SolveState) -> dict:
    """Generate step-by-step solution.

    Layer 3 (cache_layer=3): Haiku guided by a stored solution_framework (~20x cheaper).
    Layer 4 (default):       Sonnet full reasoning.
    """
    cache_layer = state.get("cache_layer", 4)
    framework = state.get("solution_framework")
    subject = state.get("detected_subject", "math")
    grade_level = state.get("grade_level", "middle school")
    ocr_text = state.get("ocr_text", "")

    # ── Layer 3: framework reuse with Haiku ─────────────────────────────────
    if cache_layer == 3 and framework:
        provider = state.get("preferred_provider") or SUBJECT_PROVIDER_MAP.get(subject, "claude")
        llm = get_llm("fast", provider)
        messages = build_solve_with_framework_messages(
            ocr_text=ocr_text,
            framework=framework,
            subject=subject,
            grade_level=grade_level,
        )
    # ── Layer 4: full Sonnet reasoning ──────────────────────────────────────
    else:
        llm = select_llm(
            preferred=state.get("preferred_provider"),
            subject=subject,
            attempt=state.get("attempt_count", 0),
            user_tier=state.get("user_tier", "paid"),
        )
        context = _build_context(
            state.get("related_formulas", []),
            state.get("similar_problems", []),
        )
        messages = build_solve_messages(
            ocr_text=ocr_text,
            subject=subject,
            grade_level=grade_level,
            context=context,
        )

    try:
        result = await llm.ainvoke(messages)
        usage = result.usage_metadata or {}

        try:
            parsed = json.loads(result.content)
        except json.JSONDecodeError:
            content = result.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
            else:
                parsed = {
                    "question_type": "unknown",
                    "knowledge_points": [],
                    "steps": [],
                    "final_answer": content,
                    "explanation": "",
                    "tips": "",
                }

        provider_name = getattr(llm, "_llm_type", "unknown")
        model_name = getattr(llm, "model_name", getattr(llm, "model", "unknown"))

        return {
            "solution_raw": result.content,
            "solution_parsed": parsed,
            "llm_provider": provider_name,
            "llm_model": str(model_name),
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        }
    except Exception as e:
        return {"error": f"Solve failed: {str(e)}"}
