from typing import TypedDict, Optional


class SolveState(TypedDict, total=False):
    """State for the main problem-solving graph."""
    # Input
    image_bytes: Optional[bytes]
    image_url: str
    user_id: int
    subject: Optional[str]
    grade_level: Optional[str]
    preferred_provider: Optional[str]

    # OCR
    ocr_text: str
    ocr_confidence: float

    # Analysis
    detected_subject: str
    problem_type: str
    difficulty: str
    knowledge_points: list[str]

    # Retrieval (RAG)
    related_formulas: list[dict]
    similar_problems: list[dict]

    # Solution
    solution_raw: str
    solution_parsed: dict
    llm_provider: str
    llm_model: str
    prompt_tokens: int
    completion_tokens: int

    # Evaluation
    quality_score: float
    quality_issues: list[str]
    attempt_count: int

    # Enrichment
    final_solution: dict
    related_formula_ids: list[int]

    # Errors
    error: Optional[str]


class FollowUpState(TypedDict, total=False):
    """State for follow-up conversation graph."""
    scan_id: int
    user_message: str
    conversation_history: list[dict]
    solution_context: dict
    subject: str
    grade_level: str
    reply: str
    provider: str
    model: str
    tokens_used: int
