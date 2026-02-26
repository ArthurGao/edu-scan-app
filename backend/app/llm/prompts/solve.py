from langchain_core.messages import SystemMessage, HumanMessage

SOLVE_SYSTEM_PROMPT = """You are an experienced {subject} teacher helping a {grade_level} student.
Your goal is to provide clear, educational explanations that help the student understand the solution process.

IMPORTANT: Respond ONLY in valid JSON format."""


def build_solve_messages(
    ocr_text: str,
    subject: str = "math",
    grade_level: str = "middle school",
    context: str = "",
) -> list:
    system = SOLVE_SYSTEM_PROMPT.format(subject=subject, grade_level=grade_level)
    user_content = """Please solve the following problem step by step.

Requirements:
1. Identify the problem type and key concepts
2. List all formulas needed (in LaTeX format)
3. Show detailed solution steps with explanations
4. Provide the final answer
5. Give tips for solving similar problems
"""
    if context:
        user_content += f"""
## Reference Context
{context}
"""
    user_content += f"""
## Problem
{ocr_text}

Respond in JSON format:
{{
  "question_type": "type of problem",
  "knowledge_points": ["concept1", "concept2"],
  "steps": [
    {{
      "step": 1,
      "description": "what this step does",
      "formula": "LaTeX formula if applicable",
      "calculation": "the actual calculation"
    }}
  ],
  "final_answer": "the answer",
  "explanation": "brief summary explanation",
  "tips": "tips for similar problems"
}}"""

    return [
        SystemMessage(content=system),
        HumanMessage(content=user_content),
    ]
