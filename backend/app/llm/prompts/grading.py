from langchain_core.messages import HumanMessage, SystemMessage

GRADING_SYSTEM_PROMPT = """You are a strict but fair {subject} grading teacher.
Your job is to grade student answers accurately and provide constructive feedback.

IMPORTANT: Respond ONLY in valid JSON format — a JSON array with one object per question.

Grading principles:
- Key points correct but incomplete → award partial credit proportional to completeness
- Process/working correct but final answer wrong → award process credit (at least 30-50% of max score)
- Off-topic, irrelevant, or blank answers → 0 points
- Accept answers written in Chinese (中文) or English — grade on content, not language
- Be precise with scoring: use the full range from 0 to max_score
- For explanation questions, focus on whether the student demonstrates understanding of key concepts"""


def build_grading_messages(questions: list[dict]) -> list:
    """Build messages for AI grading of a batch of explanation questions.

    Each question dict should contain:
        - question_id: int
        - question_text: str
        - correct_answer: str
        - answer_explanation: str | None
        - max_score: float
        - student_answer: str
    """
    system = GRADING_SYSTEM_PROMPT.format(
        subject=questions[0].get("subject", "general") if questions else "general"
    )

    questions_block = ""
    for i, q in enumerate(questions, 1):
        questions_block += f"""
--- Question {i} (ID: {q['question_id']}) ---
Question: {q['question_text']}
Correct Answer: {q['correct_answer']}
Answer Explanation: {q.get('answer_explanation') or 'N/A'}
Max Score: {q['max_score']}
Student Answer: {q['student_answer'] or '(blank)'}
"""

    user_content = f"""Grade the following {len(questions)} student answer(s).

{questions_block}

Respond with a JSON array. Each element must have exactly these fields:
[
  {{
    "question_id": <int>,
    "score": <float between 0 and max_score>,
    "is_correct": <boolean — true only if full marks awarded>,
    "feedback": "<brief explanation of why this score was given, mention what was correct/incorrect>"
  }}
]"""

    return [
        SystemMessage(content=system),
        HumanMessage(content=user_content),
    ]
