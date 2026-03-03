from langchain_core.messages import SystemMessage, HumanMessage

VERIFY_SYSTEM_PROMPT = """You are a math/science verification assistant. Please independently verify whether the given answer to the following problem is correct.

Requirements:
1. Independently calculate the correct answer yourself
2. Compare it with the given answer
3. Check key steps for logical errors

Return ONLY JSON, no other text:
{
  "independent_answer": "your calculated answer",
  "is_correct": true or false,
  "error_description": "if incorrect, explain which step went wrong; if correct, null",
  "confidence": a number from 0.0 to 1.0
}"""


def build_verify_messages(
    problem_text: str,
    final_answer: str,
    steps_summary: str,
    subject: str = "math",
) -> list:
    return [
        SystemMessage(content=VERIFY_SYSTEM_PROMPT),
        HumanMessage(content=f"""Subject: {subject}

Problem:
{problem_text}

Given answer: {final_answer}

Solution steps summary:
{steps_summary}"""),
    ]
