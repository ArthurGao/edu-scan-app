"""AI prompt templates for problem solving."""

SYSTEM_PROMPT = """You are an experienced {subject} teacher helping a {grade_level} student.
Your goal is to provide clear, educational explanations that help the student understand the solution process."""

SOLVE_PROMPT = """Please solve the following problem step by step.

Requirements:
1. Identify the problem type and key concepts
2. List all formulas needed (in LaTeX format)
3. Show detailed solution steps with explanations
4. Provide the final answer
5. Give tips for solving similar problems

Problem:
{problem_text}

Respond in JSON format:
{{
  "question_type": "type of problem",
  "knowledge_points": ["concept1", "concept2"],
  "formulas": [
    {{"name": "formula name", "latex": "LaTeX formula"}}
  ],
  "steps": [
    {{"step": 1, "description": "what we do", "formula": "formula used if any", "calculation": "actual calculation"}}
  ],
  "final_answer": "the answer",
  "explanation": "brief explanation of the approach",
  "tips": "tips for similar problems"
}}"""

FORMULA_ASSOCIATION_PROMPT = """Based on the following problem, identify all related formulas and theorems.

Problem:
{problem_text}

Subject: {subject}

List formulas that are:
1. Directly used in solving this problem
2. Related concepts that might be useful
3. Alternative approaches

Respond in JSON format:
{{
  "direct_formulas": [
    {{"name": "formula name", "latex": "LaTeX", "usage": "how it's used"}}
  ],
  "related_formulas": [
    {{"name": "formula name", "latex": "LaTeX", "relationship": "why it's related"}}
  ]
}}"""


def build_solve_prompt(
    problem_text: str,
    subject: str = "math",
    grade_level: str = "middle school",
) -> list[dict]:
    """Build messages for AI completion."""
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(subject=subject, grade_level=grade_level),
        },
        {
            "role": "user",
            "content": SOLVE_PROMPT.format(problem_text=problem_text),
        },
    ]


def build_formula_prompt(problem_text: str, subject: str = "math") -> list[dict]:
    """Build messages for formula association."""
    return [
        {
            "role": "user",
            "content": FORMULA_ASSOCIATION_PROMPT.format(
                problem_text=problem_text, subject=subject
            ),
        },
    ]
