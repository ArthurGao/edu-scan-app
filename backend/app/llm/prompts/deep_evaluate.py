from langchain_core.messages import SystemMessage, HumanMessage

DEEP_EVALUATE_SYSTEM_PROMPT = """你是一位资深教师，正在全面评估一份 K12 学生作业的 AI 解答质量。

请从以下6个维度评分（0.0-1.0），并给出改进建议。

仅返回 JSON，不要包含其他文字：
{
  "correctness": 0.0到1.0,
  "completeness": 0.0到1.0,
  "clarity": 0.0到1.0,
  "pedagogy": 0.0到1.0,
  "format": 0.0到1.0,
  "overall": 0.0到1.0,
  "improvement_suggestions": "具体的改进建议，用中文描述",
  "better_approach": "如果有更优解法则给出概要，否则为null"
}

评分标准：
- correctness: 答案和每一步计算是否数学/逻辑正确
- completeness: 是否覆盖所有考点，有无遗漏步骤
- clarity: 对该年级学生是否易懂，语言是否清晰
- pedagogy: 是否引导学生思考，而非直接给答案；是否有教学价值
- format: LaTeX公式格式、步骤编号、排版是否规范
- overall: 以上五项的加权平均"""


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
            steps_text += f" | 公式: {formula}"
        if calc:
            steps_text += f" | 计算: {calc}"
        steps_text += "\n"

    return [
        SystemMessage(content=DEEP_EVALUATE_SYSTEM_PROMPT),
        HumanMessage(content=f"""科目：{subject}
年级：{grade_level}

题目：
{problem_text}

最终答案：{final_answer}

解题步骤：
{steps_text}

完整解答原文：
{solution_raw}"""),
    ]
