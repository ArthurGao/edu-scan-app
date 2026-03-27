"""Re-process question images for all existing exams.

Downloads PDFs from source_url, re-extracts cropped images using the
updated PDFParserService, and updates image_data in practice_questions.
Also creates passage entries for reading context pages.

Usage:
    cd edu-scan-app/backend
    python -m scripts.reprocess_exam_images
"""

import asyncio
import logging
import sys

import httpx
from sqlalchemy import select

# Ensure project root is importable
sys.path.insert(0, ".")

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.exam_paper import ExamPaper, PracticeQuestion  # noqa: E402
from app.services.pdf_parser_service import PDFParserService  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def reprocess_all():
    parser = PDFParserService()

    async with AsyncSessionLocal() as db:
        # Get all exams with a source_url
        result = await db.execute(
            select(ExamPaper).where(ExamPaper.source_url.isnot(None))
        )
        exams = result.scalars().all()

        if not exams:
            logger.info("No exams with source_url found.")
            return

        logger.info("Found %d exams to reprocess.", len(exams))

        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            for exam in exams:
                logger.info("--- Processing: %s (id=%s) ---", exam.title, exam.id)

                # Download the exam PDF
                try:
                    resp = await client.get(exam.source_url)
                    resp.raise_for_status()
                    pdf_bytes = resp.content
                    logger.info("  Downloaded PDF: %d bytes", len(pdf_bytes))
                except Exception as e:
                    logger.error("  Failed to download %s: %s", exam.source_url, e)
                    continue

                # Re-extract images with fixed cropping
                try:
                    import fitz
                    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                    question_images = parser.extract_question_images(doc)
                    doc.close()
                    logger.info("  Extracted %d images (incl. passages)", len(question_images))
                except Exception as e:
                    logger.error("  Failed to extract images: %s", e)
                    continue

                # Get existing questions for this exam
                q_result = await db.execute(
                    select(PracticeQuestion)
                    .where(PracticeQuestion.exam_paper_id == exam.id)
                    .order_by(PracticeQuestion.order_index)
                )
                questions = q_result.scalars().all()

                # Update existing sub-question images
                existing_keys = set()
                updated = 0
                for q in questions:
                    key = f"Q{q.question_number}_{q.sub_question}"
                    # Normalize: DB uses "passage-0" but images use "passage_0"
                    img_key = key.replace("passage-", "passage_")
                    existing_keys.add(key)
                    if img_key in question_images:
                        q.image_data = question_images[img_key]
                        q.has_image = True
                        updated += 1
                    else:
                        q.image_data = None
                        q.has_image = False

                # Create new passage entries that don't exist yet
                passage_created = 0
                passage_keys = sorted(
                    k for k in question_images if "_passage_" in k
                )
                for pk in passage_keys:
                    # "Q1_passage_0" → q_num="1", sub="passage-0"
                    parts = pk.split("_")
                    q_num = parts[0][1:]  # strip "Q"
                    page_idx = parts[2]
                    sub = f"passage-{page_idx}"
                    check_key = f"Q{q_num}_{sub}"

                    if check_key in existing_keys:
                        continue  # already exists

                    # Find the min order_index for this question's subs
                    min_order = min(
                        (q.order_index for q in questions
                         if q.question_number == q_num),
                        default=0,
                    )

                    new_q = PracticeQuestion(
                        exam_paper_id=exam.id,
                        question_number=q_num,
                        sub_question=sub,
                        question_text="[Reading passage]",
                        question_type="passage",
                        has_image=True,
                        image_data=question_images[pk],
                        order_index=min_order - 1 - int(page_idx),
                    )
                    db.add(new_q)
                    existing_keys.add(check_key)
                    passage_created += 1

                # Update total_questions count
                exam.total_questions = len(existing_keys)

                await db.commit()
                logger.info(
                    "  Updated %d images, created %d passages (%d total)",
                    updated, passage_created, len(existing_keys),
                )

    logger.info("Done! All exams reprocessed.")


if __name__ == "__main__":
    asyncio.run(reprocess_all())
