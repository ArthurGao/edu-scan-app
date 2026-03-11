from langchain_core.messages import SystemMessage, HumanMessage

FRAMEWORK_SYSTEM_PROMPT = """You are an expert educator who abstracts reusable solution strategies from worked examples.
Your task is to extract a solution framework — the abstract reasoning structure — from a solved problem.
The framework should be general enough to guide solving similar problems, NOT specific to this problem's numbers or context.

IMPORTANT: Respond ONLY in valid JSON format."""


def build_framework_messages(problem_text: str, solution_json: str, subject: str = "math") -> list:
    """Build messages for generating a solution_framework from a completed solution."""
    return [
        SystemMessage(content=FRAMEWORK_SYSTEM_PROMPT),
        HumanMessage(content=f"""Extract a reusable solution framework from this solved {subject} problem.

## Problem
{problem_text}

## Solution
{solution_json}

Output a JSON framework that captures HOW to solve this type of problem (not the specific answer).
The framework must include:
- "topic": the problem category/concept
- "reasoning_chain": ordered list of abstract steps (use general language, no specific numbers)
- "key_principles": formulas or theorems applied
- "what_to_identify": what to look for in similar problems
- "common_mistakes": typical errors to avoid

Respond in JSON:
{{
  "topic": "brief topic name",
  "reasoning_chain": ["step 1 description", "step 2 description"],
  "key_principles": ["principle or formula"],
  "what_to_identify": ["what to look for"],
  "common_mistakes": ["mistake to avoid"]
}}"""),
    ]


FRAMEWORK_SOLVE_SYSTEM = """You are an experienced teacher helping a {grade_level} student solve a {subject} problem.
A solution framework from a similar problem is provided as a guide.
Follow the framework's reasoning chain, but apply it to this specific problem.

IMPORTANT: Respond ONLY in valid JSON format."""


def build_solve_with_framework_messages(
    ocr_text: str,
    framework: dict,
    subject: str = "math",
    grade_level: str = "middle school",
) -> list:
    """Build messages for Layer 3 solve: Haiku guided by a solution framework."""
    import json
    framework_str = json.dumps(framework, ensure_ascii=False, indent=2)

    system = FRAMEWORK_SOLVE_SYSTEM.format(subject=subject, grade_level=grade_level)
    user = f"""A similar problem was solved using this framework:
{framework_str}

Follow this framework's reasoning chain to solve the problem below.

Math formatting rules:
- In "formula" fields: use pure LaTeX (no $ delimiters)
- In text fields: wrap math with $ for inline, $$ for display math
- Use LaTeX for fractions (\\frac{{a}}{{b}}), exponents (x^{{2}}), roots (\\sqrt{{x}})

## Problem
{ocr_text}

Respond in JSON:
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

    return [SystemMessage(content=system), HumanMessage(content=user)]
