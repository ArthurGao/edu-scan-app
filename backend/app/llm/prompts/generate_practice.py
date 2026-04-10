from langchain_core.messages import HumanMessage, SystemMessage

GENERATE_PRACTICE_SYSTEM_PROMPT = """You are an experienced {subject} teacher creating practice problems for {grade_level} students.
Generate exactly 3 practice questions based on the original problem, with escalating difficulty.

IMPORTANT: Respond ONLY in valid JSON format.

Math formatting rules:
- Wrap inline math expressions with $ delimiters, e.g. "Solve $2x^2 + 3x - 5 = 0$"
- Use $$ delimiters for display math
- Use LaTeX for fractions (\\frac{{a}}{{b}}), exponents (x^{{2}}), square roots (\\sqrt{{x}}), etc.
- Do NOT use plain text for math like "1/2" or "x^2" — always use LaTeX notation"""


def build_generate_practice_messages(
    ocr_text: str,
    subject: str,
    difficulty: str,
    problem_type: str,
    knowledge_points: list[str],
    solution_steps_summary: str,
    grade_level: str = "high school",
) -> list:
    """Build messages for generating 3 practice questions from a solved problem."""
    system = GENERATE_PRACTICE_SYSTEM_PROMPT.format(
        subject=subject, grade_level=grade_level
    )

    kp_str = ", ".join(knowledge_points) if knowledge_points else "general"

    user_content = f"""## Original Problem
{ocr_text}

## Original Solution Analysis
- Subject: {subject}
- Problem Type: {problem_type}
- Difficulty: {difficulty}
- Knowledge Points: {kp_str}
- Solution approach: {solution_steps_summary}

## Generation Requirements

Generate 3 questions with escalating difficulty:

1. **Same Level** (difficulty_offset=0): Test the same concept with different numbers/context.
   Keep the same problem type and knowledge points.

2. **Harder** (difficulty_offset=1): Add one layer of complexity.
   Examples: combine two concepts, add a constraint, require an extra step, use less obvious numbers.

3. **Hardest** (difficulty_offset=2): Significantly harder or cross-topic.
   Examples: multi-step reasoning, proof-based, real-world application, combine 3+ concepts.

For each question provide:
- question_text: The problem statement (use LaTeX for math)
- question_type: "numeric", "multichoice", or "explanation"
- correct_answer: Concise answer for exact matching (if numeric/multichoice)
- accepted_answers: Array of alternative valid forms, e.g. ["x=2", "2", "2.0"]
- answer_explanation: Detailed step-by-step solution (use LaTeX)
- knowledge_points: Array of concept strings tested
- difficulty: "easy", "medium", "hard", or "very_hard"
- marks: Integer score value (1-5)

## Response Format
{{
  "questions": [
    {{
      "difficulty_offset": 0,
      "question_text": "...",
      "question_type": "numeric",
      "correct_answer": "...",
      "accepted_answers": ["...", "..."],
      "answer_explanation": "Step 1: ... Step 2: ...",
      "knowledge_points": ["algebra", "quadratic_formula"],
      "difficulty": "medium",
      "marks": 3
    }},
    {{ "difficulty_offset": 1, "..." : "..." }},
    {{ "difficulty_offset": 2, "..." : "..." }}
  ]
}}"""

    return [
        SystemMessage(content=system),
        HumanMessage(content=user_content),
    ]
