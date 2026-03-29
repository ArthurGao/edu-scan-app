"""Backfill answers for exams missing marking schedules.

Step 1: Try to re-download marking schedules from NZQA source URLs.
Step 2: For remaining exams without answers, use AI to generate answers.

Usage:
    cd edu-scan-app/backend
    python -m scripts.backfill_answers
"""

import asyncio
import json
import logging
import re
import sys

import httpx

sys.path.insert(0, ".")

from sqlalchemy import func, select  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.exam_paper import ExamPaper, PracticeQuestion  # noqa: E402
from app.services.exam_crawler_service import ExamCrawlerService  # noqa: E402
from app.services.pdf_parser_service import PDFParserService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def find_schedule_url(exam_url: str, client: httpx.AsyncClient) -> str | None:
    """Try to find a marking schedule PDF URL near the exam URL on NZQA."""
    # Schedule URLs typically follow patterns:
    # exam: .../91946-exm-2023.pdf → schedule: .../91946-ass-2023.pdf
    # exam: .../32406B-2-exm-2025.pdf → schedule: .../32406B-2-ass-2025.pdf
    schedule_patterns = [
        # Replace -exm- with -ass- (assessment schedule)
        (r"-exm-", "-ass-"),
        # Replace -exam- with -schedule-
        (r"-exam-", "-schedule-"),
        # Replace "Questions" with "Assessment-Schedule" (literacy)
        (r"Questions", "Assessment-Schedule"),
        # Replace "assessment-paper" with "assessment-schedule"
        (r"assessment-paper", "assessment-schedule"),
        # Replace "exam" at end with "schedule"
        (r"-exam-(\d{4})", r"-schedule-\1"),
    ]

    for pattern, replacement in schedule_patterns:
        candidate = re.sub(pattern, replacement, exam_url)
        if candidate != exam_url:
            try:
                resp = await client.head(candidate, follow_redirects=True)
                if resp.status_code == 200:
                    content_type = resp.headers.get("content-type", "")
                    if "pdf" in content_type or candidate.endswith(".pdf"):
                        return candidate
            except Exception:
                continue

    return None


async def step1_crawl_schedules():
    """Try to find and download marking schedules from NZQA."""
    parser = PDFParserService()
    updated_exams = 0

    async with AsyncSessionLocal() as db:
        # Get exams with no answers
        has_answers = (await db.execute(
            select(PracticeQuestion.exam_paper_id).where(
                PracticeQuestion.correct_answer.isnot(None)
            ).distinct()
        )).scalars().all()
        has_set = set(has_answers)

        all_exams = (await db.execute(
            select(ExamPaper).where(ExamPaper.source_url.isnot(None))
        )).scalars().all()

        missing = [e for e in all_exams if e.id not in has_set]
        logger.info("Step 1: %d exams missing answers, trying to find schedules...", len(missing))

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for exam in missing:
                schedule_url = await find_schedule_url(exam.source_url, client)
                if not schedule_url:
                    continue

                logger.info("  [%d] Found schedule: %s", exam.id, schedule_url[:80])
                try:
                    resp = await client.get(schedule_url)
                    resp.raise_for_status()
                    schedule_answers = await parser.parse_schedule_pdf(resp.content)
                    answer_map = parser.get_answer_map(schedule_answers)

                    if not answer_map:
                        logger.info("    No answers parsed from schedule")
                        continue

                    # Get questions and match answers
                    questions = (await db.execute(
                        select(PracticeQuestion)
                        .where(PracticeQuestion.exam_paper_id == exam.id)
                        .where(~PracticeQuestion.sub_question.like("passage%"))
                    )).scalars().all()

                    matched = 0
                    for q in questions:
                        key = f"{q.question_number}_{q.sub_question}"
                        if key in answer_map:
                            a = answer_map[key]
                            q.correct_answer = a.correct_answer
                            q.accepted_answers = a.accepted_answers or []
                            q.answer_explanation = a.explanation
                            q.marks = a.marks
                            if a.question_type:
                                q.question_type = a.question_type
                            matched += 1

                    await db.commit()
                    logger.info("    Matched %d/%d answers", matched, len(questions))
                    if matched > 0:
                        updated_exams += 1
                except Exception as e:
                    logger.error("    Failed: %s", e)
                    continue

    logger.info("Step 1 done: updated %d exams with schedules", updated_exams)
    return updated_exams


async def step2_ai_generate_answers():
    """Use AI to generate answers for remaining exams without schedules."""
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.llm.registry import get_llm

    SYSTEM_PROMPT = """You are an expert exam marker. Given exam questions, provide the correct answer for each question.

For numeric questions: give the final numeric value.
For multichoice questions: state the correct option text.
For explanation questions: give a concise model answer (1-2 sentences).

Use simple numbering: "1", "2", "3" (not "ONE", "TWO").

You MUST respond with ONLY a JSON array. No text before or after. No markdown fences.
Example:
[{"question_number":"1","sub_question":"a","correct_answer":"42","explanation":"Because 6 times 7 is 42"}]"""

    llm = get_llm(tier="fast", provider="gemini")
    updated_exams = 0

    async with AsyncSessionLocal() as db:
        # Get exams STILL with no answers after step 1
        has_answers = (await db.execute(
            select(PracticeQuestion.exam_paper_id).where(
                PracticeQuestion.correct_answer.isnot(None)
            ).distinct()
        )).scalars().all()
        has_set = set(has_answers)

        all_exams = (await db.execute(select(ExamPaper))).scalars().all()
        missing = [e for e in all_exams if e.id not in has_set and e.raw_text]
        logger.info("Step 2: %d exams still missing answers, using AI...", len(missing))

        for exam in missing:
            if not exam.raw_text or len(exam.raw_text.strip()) < 50:
                continue

            logger.info("  [%d] %s (%s)", exam.id, exam.title, exam.subject)

            try:
                messages = [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=f"Exam: {exam.title}\nSubject: {exam.subject}\n\n{exam.raw_text[:8000]}"),
                ]
                result = await llm.ainvoke(messages)

                # Parse JSON
                content = result.content.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    lines = [l for l in lines if not l.strip().startswith("```")]
                    content = "\n".join(lines).strip()

                start = content.find("[")
                end = content.rfind("]") + 1
                if start < 0 or end <= start:
                    logger.info("    No JSON array in response")
                    continue

                parsed = json.loads(content[start:end])
                logger.info("    AI generated %d answers", len(parsed))

                # Build lookup
                answer_map = {}
                for item in parsed:
                    key = f"{item['question_number']}_{item['sub_question']}"
                    answer_map[key] = item

                # Get questions
                questions = (await db.execute(
                    select(PracticeQuestion)
                    .where(PracticeQuestion.exam_paper_id == exam.id)
                    .where(~PracticeQuestion.sub_question.like("passage%"))
                    .where(PracticeQuestion.correct_answer.is_(None))
                )).scalars().all()

                matched = 0
                for q in questions:
                    key = f"{q.question_number}_{q.sub_question}"
                    if key in answer_map:
                        a = answer_map[key]
                        q.correct_answer = a.get("correct_answer", "")
                        q.answer_explanation = a.get("explanation", "")
                        matched += 1

                await db.commit()
                logger.info("    Matched %d/%d questions", matched, len(questions))
                if matched > 0:
                    updated_exams += 1

            except Exception as e:
                logger.error("    AI failed: %s", e)
                continue

    logger.info("Step 2 done: AI-filled %d exams", updated_exams)
    return updated_exams


async def main():
    logger.info("=== Backfilling answers for exams without marking schedules ===\n")

    s1 = await step1_crawl_schedules()
    print()
    s2 = await step2_ai_generate_answers()

    logger.info("\n=== Summary ===")
    logger.info("Schedules found & parsed: %d exams", s1)
    logger.info("AI-generated answers: %d exams", s2)
    logger.info("Done!")


if __name__ == "__main__":
    asyncio.run(main())
