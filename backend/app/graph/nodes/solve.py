import json
from app.graph.state import SolveState
from app.llm.registry import select_llm
from app.llm.prompts.solve import build_solve_messages


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
    """Generate step-by-step solution using the selected LLM."""
    llm = select_llm(
        preferred=state.get("preferred_provider"),
        subject=state.get("detected_subject", "math"),
        attempt=state.get("attempt_count", 0),
    )

    context = _build_context(
        state.get("related_formulas", []),
        state.get("similar_problems", []),
    )

    messages = build_solve_messages(
        ocr_text=state.get("ocr_text", ""),
        subject=state.get("detected_subject", "math"),
        grade_level=state.get("grade_level", "middle school"),
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

        provider = getattr(llm, "_llm_type", "unknown")
        model = getattr(llm, "model_name", getattr(llm, "model", "unknown"))

        return {
            "solution_raw": result.content,
            "solution_parsed": parsed,
            "llm_provider": provider,
            "llm_model": str(model),
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        }
    except Exception as e:
        return {"error": f"Solve failed: {str(e)}"}
