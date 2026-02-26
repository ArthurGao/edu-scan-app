from langchain_core.messages import SystemMessage, HumanMessage

EVALUATE_SYSTEM_PROMPT = """You are a senior teacher reviewing a student solution for correctness and quality.
Score each criterion from 0.0 to 1.0. Be strict on correctness.

Respond ONLY in JSON:
{
  "scores": {
    "correctness": 0.9,
    "completeness": 0.8,
    "clarity": 0.85,
    "format": 0.9,
    "relevance": 0.8
  },
  "overall": 0.85,
  "issues": ["list of specific issues found"],
  "pass": true
}"""


def build_evaluate_messages(
    problem_text: str,
    solution: str,
    subject: str = "math",
    grade_level: str = "middle school",
) -> list:
    return [
        SystemMessage(content=EVALUATE_SYSTEM_PROMPT),
        HumanMessage(content=f"""Subject: {subject}
Grade Level: {grade_level}

Problem:
{problem_text}

Solution to Review:
{solution}"""),
    ]
