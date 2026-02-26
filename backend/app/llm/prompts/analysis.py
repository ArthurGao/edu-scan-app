from langchain_core.messages import SystemMessage, HumanMessage

ANALYSIS_SYSTEM_PROMPT = """You are an expert education AI that classifies student homework problems.
Analyze the given problem text and identify:
1. Subject (math, physics, chemistry, biology, english, chinese)
2. Problem type (equation, geometry, word_problem, proof, multiple_choice, fill_in_blank)
3. Difficulty (easy, medium, hard)
4. Key knowledge points

Respond ONLY in JSON:
{
  "subject": "math",
  "problem_type": "equation",
  "difficulty": "medium",
  "knowledge_points": ["algebra", "linear_equations"]
}"""


def build_analysis_messages(
    ocr_text: str,
    grade_level: str = "unknown",
) -> list:
    return [
        SystemMessage(content=ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(content=f"Grade Level: {grade_level}\n\nProblem:\n{ocr_text}"),
    ]
