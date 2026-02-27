from langchain_core.messages import SystemMessage, HumanMessage

VERIFY_SYSTEM_PROMPT = """你是一个数学/理科验算助手。请独立验算以下题目的答案是否正确。

要求：
1. 自己独立计算出正确答案
2. 对比给出的答案
3. 检查关键步骤是否有逻辑错误

仅返回 JSON，不要包含其他文字：
{
  "independent_answer": "你算出的答案",
  "is_correct": true或false,
  "error_description": "如果错误，说明哪步出错；如果正确则为null",
  "confidence": 0.0到1.0的数字
}"""


def build_verify_messages(
    problem_text: str,
    final_answer: str,
    steps_summary: str,
    subject: str = "math",
) -> list:
    return [
        SystemMessage(content=VERIFY_SYSTEM_PROMPT),
        HumanMessage(content=f"""科目：{subject}

题目：
{problem_text}

给出的答案：{final_answer}

解题步骤摘要：
{steps_summary}"""),
    ]
