"""Exam paper upload and practice question endpoints.

Endpoint design:
  Admin (require_admin):
    POST   /exams/upload                          Upload exam + schedule PDF
    POST   /exams/crawl                           Crawl NZQA page
    GET    /exams/{id}/questions/admin             All questions WITH answers (paginated)
    DELETE /exams/{id}                             Delete an exam paper

  Student (public):
    GET    /exams                                  List exam papers (paginated, filterable)
    GET    /exams/{id}/questions                   Questions WITHOUT answers (paginated, filterable by type)
    GET    /exams/{id}/questions/{qid}             Single question (no answer)
    POST   /exams/{id}/questions/{qid}/answer      Reveal answer after student submits attempt
    GET    /exams/questions/{qid}/image            Serve cropped question image
"""

import math
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.database import get_db
from app.models.exam_paper import ExamPaper, PracticeQuestion
from app.schemas.common import PaginatedResponse
from app.schemas.exam import (
    CrawlRequest,
    CrawlResponse,
    CrawledPaperSummary,
    ExamPaperResponse,
    ExamUploadResponse,
    PracticeQuestionResponse,
    PracticeQuestionWithAnswerResponse,
    QuestionAnswerResponse,
)
from app.services.exam_crawler_service import ExamCrawlerService
from app.services.pdf_parser_service import PDFParserService

router = APIRouter()


# ===========================================================================
# Admin: Upload
# ===========================================================================


@router.post(
    "/upload",
    response_model=ExamUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def upload_exam_pdf(
    exam_pdf: UploadFile = File(...),
    schedule_pdf: Optional[UploadFile] = File(None),
    title: str = Form(...),
    year: int = Form(...),
    subject: str = Form("numeracy"),
    level: int = Form(1),
    exam_code: str = Form("32406"),
    language: str = Form("english"),
    source_url: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload an exam PDF (and optional marking schedule) to parse into practice questions."""
    if not exam_pdf.filename or not exam_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Exam file must be a PDF")

    parser = PDFParserService()

    exam_bytes = await exam_pdf.read()
    parsed_exam = await parser.parse_exam_pdf(exam_bytes)

    if not parsed_exam.questions:
        raise HTTPException(status_code=422, detail="No questions could be parsed from the exam PDF")

    # Parse marking schedule if provided
    answer_map = {}
    if schedule_pdf:
        if not schedule_pdf.filename or not schedule_pdf.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail="Schedule file must be a PDF")
        schedule_bytes = await schedule_pdf.read()
        schedule_answers = await parser.parse_schedule_pdf(schedule_bytes)
        answer_map = parser.get_answer_map(schedule_answers)

    # Create exam paper record
    exam_paper = ExamPaper(
        title=title,
        source_url=source_url,
        year=year,
        subject=subject,
        level=level,
        exam_code=exam_code,
        paper_type="exam",
        language=language,
        total_questions=len(parsed_exam.questions),
        raw_text=parsed_exam.raw_text,
    )
    db.add(exam_paper)
    await db.flush()

    # Create practice question records
    question_models = []
    for pq in parsed_exam.questions:
        key = f"{pq.question_number}_{pq.sub_question}"
        answer = answer_map.get(key)

        question = PracticeQuestion(
            exam_paper_id=exam_paper.id,
            question_number=pq.question_number,
            sub_question=pq.sub_question,
            question_text=pq.text,
            question_type=answer.question_type if answer else None,
            correct_answer=answer.correct_answer if answer else None,
            accepted_answers=answer.accepted_answers if answer else None,
            answer_explanation=answer.explanation if answer else None,
            marks=answer.marks if answer else None,
            outcome=answer.outcome if answer else None,
            has_image=pq.has_image,
            image_data=pq.image_bytes,
            order_index=pq.order_index,
        )
        db.add(question)
        question_models.append(question)

    await db.commit()
    await db.refresh(exam_paper)
    for q in question_models:
        await db.refresh(q)

    return ExamUploadResponse(
        exam_paper=_paper_response(exam_paper),
        total_questions_parsed=len(question_models),
        questions=[_admin_question_response(q) for q in question_models],
    )


# ===========================================================================
# Admin: Crawl NZQA page
# ===========================================================================


@router.post(
    "/crawl",
    response_model=CrawlResponse,
    dependencies=[Depends(require_admin)],
)
async def crawl_exam_page(
    request: CrawlRequest,
    db: AsyncSession = Depends(get_db),
):
    """Crawl an NZQA page to discover, download, parse and store exam PDFs.

    Uses concurrent download+parse for speed, then saves to DB sequentially.
    """
    import asyncio
    import logging

    logger = logging.getLogger(__name__)
    from app.services.exam_crawler_service import EXAM_CODE_MAP

    crawler = ExamCrawlerService()
    parser = PDFParserService()

    all_pdfs = await crawler.discover_pdfs(request.url)
    filtered = crawler.filter_exam_pdfs(all_pdfs, language=request.language)
    pairs = crawler.pair_exams_with_schedules(filtered)

    papers_imported: list[CrawledPaperSummary] = []
    skipped: list[str] = []
    failed: list[str] = []
    errors: list[str] = []
    total_questions = 0

    # --- Phase 1: Filter out duplicates (fast, DB only) ---
    new_pairs = []
    for pair in pairs:
        exam_title = pair.exam.title or pair.exam.url.split("/")[-1]
        dup = (await db.execute(
            select(ExamPaper).where(ExamPaper.source_url == pair.exam.url)
        )).scalar_one_or_none()
        if dup:
            skipped.append(f"{exam_title} ({pair.exam.year})")
            logger.info("Skipping existing: %s", exam_title)
        else:
            new_pairs.append(pair)

    if not new_pairs:
        return CrawlResponse(
            url=request.url,
            total_pdfs_discovered=len(all_pdfs),
            total_papers_imported=0,
            total_questions_parsed=0,
            total_skipped=len(skipped),
            papers=[], skipped=skipped, failed=failed, errors=errors,
        )

    # --- Phase 2: Download + parse concurrently (3 at a time) ---
    CONCURRENCY = 3
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async def process_pair(pair):
        """Download and parse a single exam+schedule pair. Returns parsed data or error."""
        exam_title = pair.exam.title or pair.exam.url.split("/")[-1]
        async with semaphore:
            try:
                exam_bytes = await crawler.download_pdf(pair.exam.url)
                parsed_exam = await parser.parse_exam_pdf(exam_bytes)
                if not parsed_exam.questions:
                    return {"status": "failed", "title": exam_title, "year": pair.exam.year,
                            "msg": "0 questions parsed", "url": pair.exam.url}

                answer_map = {}
                if pair.schedule:
                    try:
                        schedule_bytes = await crawler.download_pdf(pair.schedule.url)
                        schedule_answers = await parser.parse_schedule_pdf(schedule_bytes)
                        answer_map = parser.get_answer_map(schedule_answers)
                    except Exception as e:
                        return {"status": "ok", "pair": pair, "parsed": parsed_exam,
                                "answers": answer_map, "warning": f"Schedule failed: {e}"}

                return {"status": "ok", "pair": pair, "parsed": parsed_exam, "answers": answer_map}
            except Exception as e:
                return {"status": "failed", "title": exam_title, "year": pair.exam.year,
                        "msg": str(e), "url": pair.exam.url}

    logger.info("Processing %d new papers (concurrency=%d)...", len(new_pairs), CONCURRENCY)
    results = await asyncio.gather(*[process_pair(p) for p in new_pairs])

    # --- Phase 3: Save to DB sequentially ---
    for result in results:
        if result["status"] == "failed":
            failed.append(f"{result['title']} ({result['year']}) — {result['msg']}, URL: {result['url']}")
            continue

        pair = result["pair"]
        parsed_exam = result["parsed"]
        answer_map = result["answers"]
        exam_title = pair.exam.title or pair.exam.url.split("/")[-1]

        if result.get("warning"):
            errors.append(f"{exam_title}: {result['warning']}")

        try:
            detected_code = pair.exam.exam_code or request.exam_code
            code_info = EXAM_CODE_MAP.get(detected_code, {})

            exam_paper = ExamPaper(
                title=pair.exam.title or parsed_exam.title,
                source_url=pair.exam.url,
                year=pair.exam.year,
                subject=str(code_info.get("subject", request.subject)),
                level=int(code_info.get("level", request.level)),
                exam_code=detected_code,
                paper_type="exam",
                language=request.language,
                total_questions=len(parsed_exam.questions),
                raw_text=parsed_exam.raw_text,
            )
            db.add(exam_paper)
            await db.flush()

            for pq in parsed_exam.questions:
                key = f"{pq.question_number}_{pq.sub_question}"
                answer = answer_map.get(key)
                question = PracticeQuestion(
                    exam_paper_id=exam_paper.id,
                    question_number=pq.question_number,
                    sub_question=pq.sub_question,
                    question_text=pq.text,
                    question_type=answer.question_type if answer else None,
                    correct_answer=answer.correct_answer if answer else None,
                    accepted_answers=answer.accepted_answers if answer else None,
                    answer_explanation=answer.explanation if answer else None,
                    marks=answer.marks if answer else None,
                    outcome=answer.outcome if answer else None,
                    has_image=pq.has_image,
                    image_data=pq.image_bytes,
                    order_index=pq.order_index,
                )
                db.add(question)

            await db.commit()

            total_questions += len(parsed_exam.questions)
            papers_imported.append(CrawledPaperSummary(
                title=exam_paper.title,
                year=exam_paper.year,
                total_questions=len(parsed_exam.questions),
                exam_paper_id=str(exam_paper.id),
            ))
            logger.info("Imported: %s (%d questions)", exam_paper.title, len(parsed_exam.questions))

        except Exception as e:
            await db.rollback()
            failed.append(f"{exam_title} ({pair.exam.year}) — {str(e)}, URL: {pair.exam.url}")
            logger.exception("Failed to save %s", pair.exam.url)

    return CrawlResponse(
        url=request.url,
        total_pdfs_discovered=len(all_pdfs),
        total_papers_imported=len(papers_imported),
        total_questions_parsed=total_questions,
        total_skipped=len(skipped),
        papers=papers_imported,
        skipped=skipped,
        failed=failed,
        errors=errors,
    )


# ===========================================================================
# Admin: Upload marking schedule to existing exam
# ===========================================================================


@router.post(
    "/{exam_id}/schedule",
    dependencies=[Depends(require_admin)],
)
async def upload_schedule(
    exam_id: int,
    schedule_pdf: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a marking schedule PDF to add/update answers for an existing exam."""
    paper = await _require_exam(exam_id, db)

    if not schedule_pdf.filename or not schedule_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="File must be a PDF")

    parser = PDFParserService()
    schedule_bytes = await schedule_pdf.read()
    schedule_answers = await parser.parse_schedule_pdf(schedule_bytes)
    answer_map = parser.get_answer_map(schedule_answers)

    if not answer_map:
        raise HTTPException(status_code=422, detail="No answers could be parsed from the schedule PDF")

    # Update existing questions with answers
    query = select(PracticeQuestion).where(PracticeQuestion.exam_paper_id == exam_id)
    questions = (await db.execute(query)).scalars().all()

    updated = 0
    for q in questions:
        key = f"{q.question_number}_{q.sub_question}"
        answer = answer_map.get(key)
        if answer:
            q.correct_answer = answer.correct_answer
            q.accepted_answers = answer.accepted_answers
            q.answer_explanation = answer.explanation
            q.marks = answer.marks
            q.outcome = answer.outcome
            if answer.question_type:
                q.question_type = answer.question_type
            updated += 1

    await db.commit()

    return {
        "exam_id": exam_id,
        "title": paper.title,
        "total_questions": len(questions),
        "answers_updated": updated,
        "answers_parsed": len(answer_map),
    }


# ===========================================================================
# Admin: List questions WITH answers
# ===========================================================================


@router.get(
    "/{exam_id}/questions/admin",
    response_model=PaginatedResponse[PracticeQuestionWithAnswerResponse],
    dependencies=[Depends(require_admin)],
)
async def list_questions_admin(
    exam_id: int,
    question_type: Optional[str] = Query(None, description="Filter: numeric, multichoice, explanation"),
    question_number: Optional[str] = Query(None, description="Filter by main question number"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list all questions with answers for an exam paper."""
    await _require_exam(exam_id, db)

    query = select(PracticeQuestion).where(PracticeQuestion.exam_paper_id == exam_id)
    count_query = select(func.count(PracticeQuestion.id)).where(PracticeQuestion.exam_paper_id == exam_id)

    query, count_query = _apply_question_filters(query, count_query, question_type, question_number)

    total = (await db.execute(count_query)).scalar() or 0
    pages = max(1, math.ceil(total / limit))

    query = query.order_by(PracticeQuestion.order_index).offset((page - 1) * limit).limit(limit)
    questions = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=[_admin_question_response(q) for q in questions],
        total=total, page=page, pages=pages, limit=limit,
    )


# ===========================================================================
# Admin: Delete exam paper
# ===========================================================================


@router.delete(
    "/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_exam_paper(
    exam_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete an exam paper and all its questions."""
    paper = await _require_exam(exam_id, db)
    await db.delete(paper)
    await db.commit()


# ===========================================================================
# Public: List exam papers
# ===========================================================================


@router.get("", response_model=PaginatedResponse[ExamPaperResponse])
async def list_exam_papers(
    year: Optional[int] = Query(None),
    subject: Optional[str] = Query(None),
    level: Optional[int] = Query(None, description="NCEA Level: 1, 2, or 3"),
    language: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List available exam papers with optional filtering."""
    query = select(ExamPaper)
    count_query = select(func.count(ExamPaper.id))

    if year:
        query = query.where(ExamPaper.year == year)
        count_query = count_query.where(ExamPaper.year == year)
    if subject:
        query = query.where(ExamPaper.subject == subject)
        count_query = count_query.where(ExamPaper.subject == subject)
    if level:
        query = query.where(ExamPaper.level == level)
        count_query = count_query.where(ExamPaper.level == level)
    if language:
        query = query.where(ExamPaper.language == language)
        count_query = count_query.where(ExamPaper.language == language)

    total = (await db.execute(count_query)).scalar() or 0
    pages = max(1, math.ceil(total / limit))

    query = query.order_by(ExamPaper.year.desc(), ExamPaper.created_at.desc())
    query = query.offset((page - 1) * limit).limit(limit)
    papers = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=[_paper_response(p) for p in papers],
        total=total, page=page, pages=pages, limit=limit,
    )


# ===========================================================================
# Student: List questions WITHOUT answers (filterable by type)
# ===========================================================================


@router.get(
    "/{exam_id}/questions",
    response_model=PaginatedResponse[PracticeQuestionResponse],
)
async def list_questions_student(
    exam_id: int,
    question_type: Optional[str] = Query(None, description="Filter: numeric, multichoice, explanation"),
    question_number: Optional[str] = Query(None, description="Filter by main question number, e.g. '1', '2'"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Student: list questions for an exam — no answers included."""
    await _require_exam(exam_id, db)

    query = select(PracticeQuestion).where(PracticeQuestion.exam_paper_id == exam_id)
    count_query = select(func.count(PracticeQuestion.id)).where(PracticeQuestion.exam_paper_id == exam_id)

    query, count_query = _apply_question_filters(query, count_query, question_type, question_number)

    total = (await db.execute(count_query)).scalar() or 0
    pages = max(1, math.ceil(total / limit))

    query = query.order_by(PracticeQuestion.order_index).offset((page - 1) * limit).limit(limit)
    questions = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        items=[_student_question_response(q) for q in questions],
        total=total, page=page, pages=pages, limit=limit,
    )


# ===========================================================================
# Student: Get single question (no answer)
# ===========================================================================


@router.get(
    "/{exam_id}/questions/{question_id}",
    response_model=PracticeQuestionResponse,
)
async def get_question(
    exam_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Student: get a single question without its answer."""
    question = await _require_question(exam_id, question_id, db)
    return _student_question_response(question)


# ===========================================================================
# Student: Reveal answer (after attempting)
# ===========================================================================


@router.post(
    "/{exam_id}/questions/{question_id}/answer",
    response_model=QuestionAnswerResponse,
)
async def reveal_answer(
    exam_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Student: reveal the correct answer after submitting an attempt.

    This is POST (not GET) because revealing an answer is an intentional action
    and may later be used to record that the student requested the answer.
    """
    question = await _require_question(exam_id, question_id, db)

    return QuestionAnswerResponse(
        id=str(question.id),
        correct_answer=question.correct_answer,
        accepted_answers=question.accepted_answers,
        answer_explanation=question.answer_explanation,
        marks=question.marks,
        outcome=question.outcome,
    )


# ===========================================================================
# Public: Serve question image
# ===========================================================================


@router.get("/questions/{question_id}/image")
async def get_question_image(
    question_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Serve the cropped PNG image for a question."""
    question = (await db.execute(
        select(PracticeQuestion).where(PracticeQuestion.id == question_id)
    )).scalar_one_or_none()

    if not question or not question.image_data:
        raise HTTPException(status_code=404, detail="Question image not found")

    return Response(
        content=question.image_data,
        media_type="image/png",
        headers={"Cache-Control": "no-cache"},
    )


# ===========================================================================
# Helpers
# ===========================================================================


async def _require_exam(exam_id: int, db: AsyncSession) -> ExamPaper:
    paper = await db.get(ExamPaper, exam_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Exam paper not found")
    return paper


async def _require_question(
    exam_id: int, question_id: int, db: AsyncSession,
) -> PracticeQuestion:
    query = select(PracticeQuestion).where(
        PracticeQuestion.id == question_id,
        PracticeQuestion.exam_paper_id == exam_id,
    )
    question = (await db.execute(query)).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


def _apply_question_filters(query, count_query, question_type, question_number):
    """Apply shared filters for question listing endpoints."""
    if question_type:
        query = query.where(PracticeQuestion.question_type == question_type)
        count_query = count_query.where(PracticeQuestion.question_type == question_type)
    if question_number:
        query = query.where(PracticeQuestion.question_number == question_number)
        count_query = count_query.where(PracticeQuestion.question_number == question_number)
    return query, count_query


def _paper_response(paper: ExamPaper) -> ExamPaperResponse:
    return ExamPaperResponse(
        id=str(paper.id),
        title=paper.title,
        year=paper.year,
        subject=paper.subject,
        level=paper.level,
        exam_code=paper.exam_code,
        paper_type=paper.paper_type,
        language=paper.language,
        total_questions=paper.total_questions,
        created_at=paper.created_at,
    )


def _student_question_response(q: PracticeQuestion) -> PracticeQuestionResponse:
    """Build student-facing response — no answer fields."""
    return PracticeQuestionResponse(
        id=str(q.id),
        exam_paper_id=str(q.exam_paper_id),
        question_number=q.question_number,
        sub_question=q.sub_question,
        question_text=q.question_text,
        question_type=q.question_type,
        options=q.options,
        has_image=q.has_image,
        image_url=f"/api/v1/exams/questions/{q.id}/image" if q.has_image else None,
        order_index=q.order_index,
    )


def _admin_question_response(q: PracticeQuestion) -> PracticeQuestionWithAnswerResponse:
    """Build admin-facing response — includes answer fields."""
    return PracticeQuestionWithAnswerResponse(
        id=str(q.id),
        exam_paper_id=str(q.exam_paper_id),
        question_number=q.question_number,
        sub_question=q.sub_question,
        question_text=q.question_text,
        question_type=q.question_type,
        has_image=q.has_image,
        image_url=f"/api/v1/exams/questions/{q.id}/image" if q.has_image else None,
        order_index=q.order_index,
        correct_answer=q.correct_answer,
        accepted_answers=q.accepted_answers,
        answer_explanation=q.answer_explanation,
        marks=q.marks,
        outcome=q.outcome,
    )
