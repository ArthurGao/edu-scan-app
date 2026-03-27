# Exam Practice & AI Grading System

> Design doc for a practice exam system with random quiz generation, timed/untimed modes, and hybrid grading (programmatic for objective questions, AI for subjective questions).

## Overview

Students select a real exam paper or generate a random quiz from the question pool, filtered by subject, level, and question type. After answering, the system grades automatically: multichoice and numeric questions are matched programmatically; explanation/essay/multi-step questions are graded by AI (Gemini) against the standard answer. Results show per-question scores with wrong-answer explanations.

## Core Flow

```
Student chooses exam type
  ├─ Real exam → Select ExamPaper → Load all questions in original order
  └─ Random quiz → Select subject + level + question type + count → Draw from pool

Start exam
  ├─ Timed mode → Set duration, countdown, auto-submit on expiry
  └─ Practice mode → No time limit, submit whenever ready

Answer questions → Submit all answers

Grading
  ├─ numeric → Programmatic match against correct_answer + accepted_answers
  ├─ multichoice → Programmatic exact match
  └─ explanation → AI grading (Gemini, compare against standard answer)

Result page
  → Total score + per-question score + wrong-answer explanations
```

## Grading Strategy

| Question Type | Method | Logic |
|---------------|--------|-------|
| `multichoice` | Programmatic exact match | Correct = full marks, wrong = 0 |
| `numeric` | Programmatic match with tolerance | Compare against `correct_answer` + `accepted_answers`, normalize whitespace and decimal format |
| `explanation` | AI grading (Gemini 2.5 Flash) | Compare student answer against standard answer, award partial credit |

**AI model choice:** All AI grading uses Gemini 2.5 Flash (`get_llm(tier="strong", provider="gemini")`) regardless of user tier. Grading is simpler than open-ended solving — comparing against a known standard answer does not require the strongest model. This avoids consuming paid API quota.

## Data Model

### New Table: `exam_sessions`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | Integer, PK | auto | Primary key |
| `user_id` | Integer, FK(users.id) | — | Student |
| `exam_paper_id` | Integer, FK(exam_papers.id), nullable | None | Real exam paper ID; null for random quiz |
| `session_type` | String(20) | — | `real_exam` / `random_practice` |
| `mode` | String(20) | — | `timed` / `practice` |
| `time_limit_minutes` | Integer, nullable | None | Duration for timed mode; null for practice |
| `status` | String(20) | `"in_progress"` | `in_progress` / `submitted` / `graded` |
| `total_score` | Float, nullable | None | Total score after grading |
| `max_score` | Float, nullable | None | Maximum possible score |
| `started_at` | DateTime | now() | Exam start time |
| `submitted_at` | DateTime, nullable | None | Submission time |
| `graded_at` | DateTime, nullable | None | Grading completion time |
| `filter_criteria` | JSONB, nullable | None | Random quiz filter (subject, level, question_type, count) |
| `created_at` | DateTime | now() | Record created |

### New Table: `exam_answers`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | Integer, PK | auto | Primary key |
| `session_id` | Integer, FK(exam_sessions.id) | — | Parent exam session |
| `question_id` | Integer, FK(practice_questions.id) | — | Question answered |
| `student_answer` | Text | — | Student's submitted answer |
| `is_correct` | Boolean, nullable | None | Grading result |
| `score` | Float, nullable | None | Points awarded |
| `max_score` | Float | 1.0 | Maximum points for this question |
| `grading_method` | String(20) | — | `exact_match` / `ai_grading` |
| `ai_feedback` | Text, nullable | None | AI grading feedback (deduction reasons) |
| `graded_at` | DateTime, nullable | None | When this answer was graded |

**Constraints:**
- UNIQUE on `(session_id, question_id)`
- INDEX on `(user_id, status)` on exam_sessions
- INDEX on `(session_id)` on exam_answers

### Design Decisions

- `ExamSession` represents one complete exam attempt, whether real or random.
- For random quizzes, `exam_paper_id` is null; the specific questions are tracked via `ExamAnswer.question_id`; `filter_criteria` records what filters were used for reproducibility.
- `max_score` per question derives from the `marks` field on PracticeQuestion. Current values "A"/"H" (achievement/heuristic) need a mapping to numeric scores.
- `ai_feedback` is only populated for `explanation` type questions.

## API Endpoints

### Start Exam

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/exam-sessions/start` | `{ "exam_paper_id": int, "mode": "timed"\|"practice", "time_limit_minutes": int\|null }` | Start a real exam paper |
| `POST` | `/api/v1/exam-sessions/start-random` | `{ "subject": str, "level": int, "question_types": [str], "count": int, "mode": "timed"\|"practice", "time_limit_minutes": int\|null }` | Start a random quiz |

**Returns:** `ExamSessionResponse` — session_id + question list (without answers).

### Random Quiz Assembly Logic

```
1. Query PracticeQuestion WHERE
     exam_paper.subject = filter subject (via JOIN)
     AND exam_paper.level = filter level
     AND question_type IN filter types (optional)
     AND status = "approved"
2. Random selection: ORDER BY RANDOM() LIMIT count
3. Create ExamSession(session_type="random_practice", filter_criteria=filters)
4. Create empty ExamAnswer records for each selected question
```

### Answer & Submit

| Method | Endpoint | Body | Description |
|--------|----------|------|-------------|
| `PUT` | `/api/v1/exam-sessions/{sid}/answers/{qid}` | `{ "student_answer": str }` | Save/update single answer (auto-save) |
| `POST` | `/api/v1/exam-sessions/{sid}/submit` | — | Submit exam, trigger grading |
| `GET` | `/api/v1/exam-sessions/{sid}` | — | Get exam status (in_progress/submitted/graded) |
| `GET` | `/api/v1/exam-sessions/{sid}/result` | — | Get grading result (requires status="graded") |

### Timer Control

- On submit, check: if `mode == "timed" AND now() > started_at + time_limit_minutes` → still accept, but mark `late_submit=True`.
- Frontend drives the countdown; auto-calls submit endpoint when timer reaches 0.
- Backend does not enforce timeout via background jobs (avoids cron complexity); frontend drives submission.

### Student History

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/exam-sessions` | List student's exam history (paginated, filter by status) |

## Grading System

### Programmatic Grading (multichoice + numeric)

```python
# multichoice
is_correct = student_answer.strip().upper() == correct_answer.strip().upper()
score = max_score if is_correct else 0

# numeric
normalized_student = normalize_numeric(student_answer)
all_accepted = [correct_answer] + (accepted_answers or [])
is_correct = any(normalized_student == normalize_numeric(a) for a in all_accepted)
score = max_score if is_correct else 0
```

### AI Grading (explanation)

**New prompt file:** `app/llm/prompts/grading.py`

```
System: 你是一位严谨的 {subject} 阅卷老师，根据标准答案和评分标准给学生答案打分。

User:
题目：{question_text}
标准答案：{correct_answer}
评分标准：{answer_explanation}
满分：{max_score} 分
学生答案：{student_answer}

请评分并输出 JSON：
{
  "score": float,          // 0 到 max_score 之间
  "is_correct": bool,      // 是否完全正确
  "feedback": "..."        // 简短点评：扣分原因或正确的肯定
}

评分原则：
- 关键知识点正确但表述不完整 → 给部分分
- 计算过程正确但最终答案有误 → 给过程分
- 完全偏题或空白 → 0 分
- 用中文或英文作答均可接受
```

### Batch Optimization

- Pack up to 5 explanation questions per LLM call to reduce API requests.
- Prompt accepts array input, returns array output.
- Single question failure does not block others; failed questions retry once.

### Grading Performance

- Programmatic (multichoice + numeric): milliseconds.
- AI grading: ~2-5 seconds per batch of 5 questions.
- Total grading time estimate: < 10 seconds for a typical exam.
- Frontend polls session status or uses SSE for real-time updates.

## Result Response Structure

```json
{
  "session_id": 1,
  "status": "graded",
  "total_score": 15.5,
  "max_score": 24.0,
  "percentage": 64.6,
  "duration_minutes": 35,
  "summary": {
    "total_questions": 12,
    "correct": 7,
    "partial": 2,
    "incorrect": 3
  },
  "answers": [
    {
      "question_id": 101,
      "question_text": "...",
      "question_type": "multichoice",
      "student_answer": "B",
      "correct_answer": "C",
      "is_correct": false,
      "score": 0,
      "max_score": 1,
      "grading_method": "exact_match",
      "answer_explanation": "...",
      "ai_feedback": null
    },
    {
      "question_id": 105,
      "question_type": "explanation",
      "student_answer": "The reaction produces...",
      "is_correct": false,
      "score": 2.5,
      "max_score": 4,
      "grading_method": "ai_grading",
      "answer_explanation": "...",
      "ai_feedback": "关键点'催化剂作用'未提及，扣1.5分"
    }
  ]
}
```

## File Manifest

### New files

| File | Purpose |
|------|---------|
| `app/models/exam_session.py` | ExamSession + ExamAnswer models |
| `app/schemas/exam_session.py` | Request/response schemas |
| `app/services/exam_session_service.py` | Quiz assembly, answer saving, submission |
| `app/services/grading_service.py` | Programmatic grading + AI grading |
| `app/llm/prompts/grading.py` | AI grading prompt template |
| `app/api/v1/exam_sessions.py` | Exam session API endpoints |
| `alembic/versions/024_add_exam_session_tables.py` | Database migration |

### Modified files

| File | Change |
|------|--------|
| `app/api/v1/router.py` | Register exam_sessions routes |
| `app/models/__init__.py` | Export new models |

## Implementation Order

1. Database migration (models + alembic)
2. Grading prompt template
3. GradingService (programmatic + AI grading)
4. ExamSessionService (quiz assembly + answer saving + submission)
5. API endpoints
6. Tests
