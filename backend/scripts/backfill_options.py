"""Backfill options for multichoice questions from raw exam text.

Uses the AI to re-parse options from the stored raw_text of each exam paper.

Usage:
    cd edu-scan-app/backend
    python -m scripts.backfill_options
"""

import asyncio
import json
import logging
import sys

sys.path.insert(0, ".")

from sqlalchemy import select  # noqa: E402
from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.llm.registry import get_llm  # noqa: E402
from app.models.exam_paper import ExamPaper, PracticeQuestion  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

EXTRACT_OPTIONS_PROMPT = """You are given the raw text of an exam paper. Extract the multiple-choice options for each sub-question.

Rules:
- Only extract options for questions that have multiple-choice answers (tick/circle/select from a list of options).
- Skip questions that ask for written explanations, numbers, or calculations.
- Use simple question numbering: "1", "2", "3" (not "ONE", "TWO").
- Extract each option as its full text.

Return ONLY a JSON array (no markdown):
[
  {
    "question_number": "1",
    "sub_question": "a",
    "options": ["option 1 text", "option 2 text", "option 3 text", "option 4 text"]
  },
  ...
]

If no multichoice questions are found, return an empty array: []"""


def _extract_json_array(content: str) -> list[dict]:
    content = content.strip()
    if content.startswith("```"):
        lines = content.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        content = "\n".join(lines).strip()
    try:
        parsed = json.loads(content)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(content[start:end])
            except json.JSONDecodeError:
                pass
        return []


async def backfill():
    llm = get_llm(tier="fast", provider="gemini")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ExamPaper).where(ExamPaper.raw_text.isnot(None))
        )
        exams = result.scalars().all()
        logger.info("Found %d exams with raw_text to process.", len(exams))

        for exam in exams:
            logger.info("--- %s (id=%s) ---", exam.title, exam.id)

            if not exam.raw_text or len(exam.raw_text.strip()) < 50:
                logger.info("  Skipping: no/short raw_text")
                continue

            try:
                messages = [
                    SystemMessage(content=EXTRACT_OPTIONS_PROMPT),
                    HumanMessage(content=f"Extract options from:\n\n{exam.raw_text[:8000]}"),
                ]
                result_msg = await llm.ainvoke(messages)
                parsed = _extract_json_array(result_msg.content)
                logger.info("  AI extracted %d option sets", len(parsed))
            except Exception as e:
                logger.error("  AI failed: %s", e)
                continue

            if not parsed:
                continue

            # Build lookup: "1_a" -> ["opt1", "opt2", ...]
            options_map = {}
            for item in parsed:
                key = f"{item['question_number']}_{item['sub_question']}"
                options_map[key] = item.get("options", [])

            # Update matching questions
            q_result = await db.execute(
                select(PracticeQuestion)
                .where(PracticeQuestion.exam_paper_id == exam.id)
                .where(~PracticeQuestion.sub_question.like("passage%"))
            )
            questions = q_result.scalars().all()

            updated = 0
            for q in questions:
                key = f"{q.question_number}_{q.sub_question}"
                if key in options_map and options_map[key]:
                    q.options = options_map[key]
                    q.question_type = "multichoice"
                    updated += 1

            await db.commit()
            logger.info("  Updated %d questions with options", updated)

    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(backfill())
