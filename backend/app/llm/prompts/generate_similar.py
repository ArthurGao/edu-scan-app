from langchain_core.messages import HumanMessage, SystemMessage

GENERATE_SIMILAR_SYSTEM_PROMPT = """You are an experienced {subject} teacher who creates high-quality practice questions for K12 students.
Your goal is to generate questions that test the same concepts and skills as the original, but with different numbers, contexts, or scenarios.

IMPORTANT: Respond ONLY in valid JSON format — a JSON array of question objects."""


def build_generate_similar_messages(
    question_text: str,
    correct_answer: str | None = None,
    answer_explanation: str | None = None,
    question_type: str | None = None,
    marks: str | None = None,
    outcome: int | None = None,
    count: int = 3,
) -> list:
    """Build LangChain messages for generating similar practice questions."""
    system = GENERATE_SIMILAR_SYSTEM_PROMPT.format(subject="mathematics")
    user_content = f"""Generate {count} new practice questions that are similar to the original question below.
Each generated question must test the same skills and concepts but use different values, contexts, or scenarios.

Requirements:
1. Keep the same difficulty level and question style
2. Each question must have a clear, unambiguous correct answer
3. Provide a concise explanation for each answer
4. Classify the question type (numeric, multichoice, or explanation)
5. If the original question involves a diagram or graph, provide TikZ code to generate a similar diagram; otherwise set tikz_code to null

Math formatting rules:
- In "question_text", "answer_explanation" fields: wrap math expressions with $ delimiters for inline math, e.g. "Calculate $3 \\times 7$"
- Use $$ delimiters for display math in text fields, e.g. "$$x^2 + 2x + 1 = 0$$"
- In "correct_answer" field: use pure LaTeX for math answers (no $ delimiters), e.g. "\\frac{{3}}{{4}}"
- Use LaTeX for fractions (\\frac{{a}}{{b}}), exponents (x^{{2}}), square roots (\\sqrt{{x}}), etc.
- Do NOT use plain text for math like "1/2" or "x^2" — always use LaTeX notation

## Original Question
{question_text}
"""

    if correct_answer:
        user_content += f"""
## Correct Answer
{correct_answer}
"""

    if answer_explanation:
        user_content += f"""
## Answer Explanation
{answer_explanation}
"""

    if question_type:
        user_content += f"""
## Question Type
{question_type}
"""

    if marks:
        user_content += f"""
## Marks
{marks}
"""

    if outcome is not None:
        user_content += f"""
## Achievement Outcome
{outcome}
"""

    user_content += f"""
Respond with a JSON array of exactly {count} objects, each with these fields:
[
  {{
    "question_text": "The full question text",
    "correct_answer": "The correct answer (pure LaTeX for math)",
    "accepted_answers": ["alternative accepted answer 1", "alternative 2"],
    "answer_explanation": "Step-by-step explanation of the solution",
    "question_type": "numeric|multichoice|explanation",
    "tikz_code": null
  }}
]"""

    return [
        SystemMessage(content=system),
        HumanMessage(content=user_content),
    ]
