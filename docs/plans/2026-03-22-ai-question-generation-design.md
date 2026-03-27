# AI Similar Question Generation

> Design doc for generating practice questions from existing NZQA exam questions using AI.

## Overview

Administrators select existing exam questions and use AI to generate structurally similar but content-different practice questions. Supports both text-only questions and questions with LaTeX/TikZ diagrams. Generated questions require admin review before becoming visible to students. Local database serves as staging; approved questions sync to remote Neon (production) on demand.

## Data Model Changes

### PracticeQuestion — 4 new fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | `String(20)` | `"original"` | `original` (real exam) / `ai_generated` |
| `status` | `String(20)` | `"approved"` | `draft` / `approved` / `rejected` |
| `source_question_id` | `Integer, FK(practice_questions.id), nullable` | `None` | ID of the original question this was generated from |
| `synced_at` | `DateTime, nullable` | `None` | Timestamp of last sync to remote Neon; `None` = not yet synced |

**Design decisions:**
- Defaults ensure all existing questions remain unaffected (`source="original"`, `status="approved"`).
- Student-facing queries add `WHERE status = 'approved'`.
- AI-generated questions start as `status="draft"`.
- `source_question_id` enables tracing back to the originating question.

**New indexes:**
- `ix_practice_questions_status`
- `ix_practice_questions_source`

## API Endpoints

### AI Generation (Admin)

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/exams/questions/{qid}/generate` | `{ "count": int }` | Generate similar questions from a single question |
| `POST` | `/api/v1/exams/{id}/generate` | `{ "count_per_question": int }` | Generate a full mock exam from an existing paper |

### Review (Admin)

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `GET` | `/api/v1/exams/questions/pending` | — | List draft questions (paginated) |
| `PATCH` | `/api/v1/exams/questions/{qid}/review` | `{ "status": "approved" \| "rejected" }` | Approve or reject a generated question |
| `PUT` | `/api/v1/exams/questions/{qid}` | question fields | Edit a generated question before approving |

### Data Sync (Admin)

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/admin/sync-to-remote` | — | Sync approved AI-generated questions (where `synced_at IS NULL`) to remote Neon |

### Student-Facing Changes

- `GET /api/v1/exams/{id}/questions` adds `WHERE status = 'approved'` filter.
- No other changes; fully transparent to students.

## Prompt Design

### New file: `app/llm/prompts/generate_similar.py`

**System prompt:**
```
你是一位经验丰富的 {subject} 教师，擅长编写练习题。
```

**User prompt:**
```
基于以下原题，生成 {count} 道类似练习题。

要求：
- 考察相同知识点（outcome: {outcome}）
- 相同题型（{question_type}）
- 难度相当（marks: {marks}）
- 数值、情境、措辞必须不同
- 每道题提供正确答案和解析
- 如果题目需要图形，提供完整 TikZ 代码

原题：{question_text}
原答案：{correct_answer}
原解析：{answer_explanation}

输出 JSON 数组：
[{
  "question_text": "...",
  "correct_answer": "...",
  "accepted_answers": ["..."],
  "answer_explanation": "...",
  "question_type": "numeric|multichoice|explanation",
  "tikz_code": null | "\\begin{tikzpicture}...\\end{tikzpicture}"
}]
```

### LLM Selection

- Reuse `select_llm(subject=exam.subject)` — Claude for math/physics, OpenAI for chemistry/biology.
- Use `strong` tier (question generation demands high quality).
- Temperature: 0.7 (more diversity than the 0.1 used for solving).

## TikZ Image Rendering

### New file: `app/utils/tikz_renderer.py`

```python
async def render_tikz_to_png(tikz_code: str) -> bytes | None:
    # 1. Write temporary .tex file with document preamble + tikz code
    # 2. Run pdflatex via subprocess
    # 3. Open PDF with PyMuPDF, render page to PNG bytes
    # 4. Clean up temp files
    # 5. Return PNG bytes, or None on failure
```

**Flow:**
1. AI returns `tikz_code` field (non-null means the question needs a diagram).
2. Backend calls `render_tikz_to_png()` → stores result in `image_data`.
3. Sets `has_image=True`.
4. If LaTeX compilation fails → `has_image=False`, question still usable without image. Admin sees a warning during review.

**System dependency:**
```bash
# Ubuntu/Debian
apt-get install texlive-base texlive-pictures texlive-latex-extra

# macOS
brew install --cask mactex-no-gui
```

## Service Layer

### New file: `app/services/question_generator_service.py`

```
QuestionGeneratorService:

  generate_similar(question_id, count, db) -> list[PracticeQuestion]
    1. Load source question + parent ExamPaper (for subject, level)
    2. select_llm(subject=exam.subject) with strong tier
    3. Build prompt from source question details
    4. Call LLM, parse JSON response
    5. For each generated question:
       - If tikz_code present → render_tikz_to_png() → image_data
       - Create PracticeQuestion(
           exam_paper_id = source.exam_paper_id,
           source = "ai_generated",
           status = "draft",
           source_question_id = source.id,
           question_number = source.question_number,
           sub_question = auto-numbered (e.g. "gen_1"),
           order_index = appended at end
         )
    6. Bulk insert to DB, return results

  generate_exam(exam_id, count_per_question, db) -> list[PracticeQuestion]
    1. Load all approved original questions (source="original") for the ExamPaper
    2. Call generate_similar() for each question
    3. Aggregate and return all generated questions

  sync_to_remote(db) -> SyncResult
    1. Query local: source="ai_generated" AND status="approved" AND synced_at IS NULL
    2. Connect to remote Neon via REMOTE_DATABASE_URL
    3. Batch INSERT (deduplicate by source_question_id + question_text)
    4. On success, set local synced_at = now()
    5. Return SyncResult(synced=N, failed=N, errors=[...])
```

### Error Handling

| Scenario | Behavior |
|----------|----------|
| LLM returns invalid JSON | Retry once; if still fails, log error and skip |
| TikZ compilation fails | Keep question with `has_image=False`; admin sees warning |
| Remote sync partial failure | Per-record tracking; successful records not rolled back |

## Configuration

### New environment variable

```
REMOTE_DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/dbname
```

Added to `app/core/config.py` as optional field.

## File Manifest

### New files

| File | Purpose |
|------|---------|
| `app/llm/prompts/generate_similar.py` | Prompt template for similar question generation |
| `app/services/question_generator_service.py` | Generation + sync service |
| `app/utils/tikz_renderer.py` | TikZ → PNG rendering utility |
| `alembic/versions/022_add_question_generation_fields.py` | Database migration |

### Modified files

| File | Change |
|------|--------|
| `app/models/exam_paper.py` | Add 4 fields to PracticeQuestion |
| `app/schemas/exam.py` | Add request/response schemas for generation, review, sync |
| `app/api/v1/exams.py` | Add 6 admin endpoints |
| `app/api/v1/router.py` | Register new routes (if needed) |
| `app/core/config.py` | Add `REMOTE_DATABASE_URL` |

## Implementation Order

1. Database migration (model fields + alembic)
2. TikZ renderer utility
3. Prompt template
4. Service layer
5. API endpoints
6. Tests
