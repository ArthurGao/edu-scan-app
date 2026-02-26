import json
from app.graph.state import SolveState
from app.llm.registry import get_llm
from app.llm.prompts.analysis import build_analysis_messages

SUBJECT_KEYWORDS = {
    "math": ["x", "y", "solve", "equation", "angle", "triangle", "calculate", "sum", "product"],
    "physics": ["force", "mass", "acceleration", "velocity", "energy", "momentum", "wave"],
    "chemistry": ["atom", "molecule", "reaction", "acid", "base", "element", "compound"],
}


def _detect_subject_fallback(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for subject, keywords in SUBJECT_KEYWORDS.items():
        scores[subject] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "math"


async def analyze_node(state: SolveState) -> dict:
    """Classify the problem: subject, type, difficulty, knowledge points."""
    ocr_text = state.get("ocr_text", "")
    grade_level = state.get("grade_level", "unknown")

    try:
        llm = get_llm("fast")
        messages = build_analysis_messages(ocr_text, grade_level)
        result = await llm.ainvoke(messages)
        parsed = json.loads(result.content)

        detected_subject = state.get("subject") or parsed.get("subject", "math")
        return {
            "detected_subject": detected_subject,
            "problem_type": parsed.get("problem_type", "unknown"),
            "difficulty": parsed.get("difficulty", "medium"),
            "knowledge_points": parsed.get("knowledge_points", []),
        }
    except Exception:
        detected_subject = state.get("subject") or _detect_subject_fallback(ocr_text)
        return {
            "detected_subject": detected_subject,
            "problem_type": "unknown",
            "difficulty": "medium",
            "knowledge_points": [],
        }
