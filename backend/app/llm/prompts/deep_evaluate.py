from langchain_core.messages import SystemMessage, HumanMessage

DEEP_EVALUATE_SYSTEM_PROMPT = """You are a senior teacher comprehensively evaluating the quality of an AI-generated solution for a K12 student homework problem.

Score across the following 6 dimensions (0.0-1.0) and provide improvement suggestions.

Return ONLY JSON, no other text:
{
  "correctness": 0.0 to 1.0,
  "completeness": 0.0 to 1.0,
  "clarity": 0.0 to 1.0,
  "pedagogy": 0.0 to 1.0,
  "format": 0.0 to 1.0,
  "overall": 0.0 to 1.0,
  "improvement_suggestions": "specific improvement suggestions",
  "better_approach": "outline of a better approach if one exists, otherwise null"
}

Scoring criteria:
- correctness: Whether the answer and every calculation step is mathematically/logically correct
- completeness: Whether all key concepts are covered, whether any steps are missing
- clarity: Whether it is easy to understand for students at this grade level, whether the language is clear
- pedagogy: Whether it guides the student to think rather than just giving the answer; whether it has educational value
- format: Whether LaTeX formula formatting, step numbering, and layout are well-structured
- overall: Weighted average of the above five dimensions"""


def build_deep_evaluate_messages(
    problem_text: str,
    solution_raw: str,
    final_answer: str,
    steps: list,
    subject: str = "math",
    grade_level: str = "middle school",
) -> list:
    steps_text = ""
    for s in steps:
        step_num = s.get("step", "")
        desc = s.get("description", "")
        formula = s.get("formula", "")
        calc = s.get("calculation", "")
        steps_text += f"  {step_num}. {desc}"
        if formula:
            steps_text += f" | Formula: {formula}"
        if calc:
            steps_text += f" | Calculation: {calc}"
        steps_text += "\n"

    return [
        SystemMessage(content=DEEP_EVALUATE_SYSTEM_PROMPT),
        HumanMessage(content=f"""Subject: {subject}
Grade level: {grade_level}

Problem:
{problem_text}

Final answer: {final_answer}

Solution steps:
{steps_text}

Full solution text:
{solution_raw}"""),
    ]
