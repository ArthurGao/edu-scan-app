"""Backfill answers per-question using AI.

Processes each question individually for better accuracy.

Usage:
    cd edu-scan-app/backend
    python -m scripts.backfill_answers_v2
"""

import asyncio
import logging
import sys

sys.path.insert(0, ".")

from sqlalchemy import func, select  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.exam_paper import ExamPaper, PracticeQuestion  # noqa: E402

logging.basicConfig(level=logging.WARNING)

PROMPT = (
    "You are an expert exam marker. Given this exam question, "
    "provide ONLY the correct answer. No explanation, no working. "
    "Just the answer value or text. If it is a calculation, give the numeric result."
)


async def main():
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.llm.registry import get_llm

    llm = get_llm(tier="fast", provider="gemini")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(PracticeQuestion)
            .join(ExamPaper)
            .where(PracticeQuestion.correct_answer.is_(None))
            .where(~PracticeQuestion.sub_question.like("passage%"))
            .where(PracticeQuestion.question_text.isnot(None))
            .where(func.length(PracticeQuestion.question_text) > 20)
            .order_by(PracticeQuestion.exam_paper_id, PracticeQuestion.order_index)
        )
        questions = result.scalars().all()
        print(f"Found {len(questions)} questions without answers", flush=True)

        batch_size = 5
        updated = 0
        errors = 0

        for i in range(0, len(questions), batch_size):
            batch = questions[i : i + batch_size]
            tasks = []
            for q in batch:
                text = (q.question_text or "")[:500]
                opts = ""
                if q.options:
                    opts = "\nOptions: " + " | ".join(q.options)
                tasks.append(
                    llm.ainvoke(
                        [
                            SystemMessage(content=PROMPT),
                            HumanMessage(content=f"{text}{opts}"),
                        ]
                    )
                )

            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for q, res in zip(batch, results):
                    if isinstance(res, Exception):
                        errors += 1
                        continue
                    answer = res.content.strip()
                    if len(answer) > 500:
                        answer = answer[:500]
                    q.correct_answer = answer
                    updated += 1

                await db.commit()
                pct = int((i + batch_size) / len(questions) * 100)
                print(
                    f"  [{pct:3d}%] {updated} updated, {errors} errors",
                    flush=True,
                )
            except Exception as e:
                print(f"  Batch error: {e}", flush=True)
                errors += len(batch)

        print(f"\nDone! Updated {updated} questions, {errors} errors.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
