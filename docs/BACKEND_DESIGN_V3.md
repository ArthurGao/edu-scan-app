# EduScan Backend Design v3 — LangGraph + pgvector

> Supersedes: DESIGN.md (v2.0, Jan 2025) and VECTOR_DB_FUTURE.md
> Date: February 2026

---

## 1. Goals

| # | Goal | Why |
|---|------|-----|
| 1 | Replace LiteLLM with LangGraph | Multi-step orchestration with conditional branching, retry, and per-node LLM selection |
| 2 | LLM-agnostic via LangChain ChatModel | Swap Claude/GPT/Gemini/DeepSeek/local models with zero code change |
| 3 | pgvector for embeddings | Semantic formula search, similar-problem retrieval, future RAG |
| 4 | Conversation memory | Students can ask follow-up questions ("explain step 3 more") |
| 5 | Auto-evaluation | Grade solution quality, detect errors, adjust difficulty |
| 6 | Clean database design | Relational tables for history, mistakes, formulas + vector columns |

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    React Native Mobile App                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ REST + SSE
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                                 │
│                                                                      │
│  ┌──────────┐  ┌──────────────────────────────────────────────────┐  │
│  │  Auth    │  │           LangGraph Pipeline                     │  │
│  │  Service │  │                                                  │  │
│  │          │  │  ┌─────┐  ┌────────┐  ┌────────┐  ┌──────────┐  │  │
│  │  JWT     │  │  │ OCR │→│Analysis│→│Solution│→│ Formula  │  │  │
│  │  Users   │  │  │     │  │        │  │ Gen    │  │ Matching │  │  │
│  └──────────┘  │  └─────┘  └────────┘  └────────┘  └──────────┘  │  │
│                │       │         │          │            │         │  │
│  ┌──────────┐  │       ▼         ▼          ▼            ▼         │  │
│  │ History  │  │  ┌──────────────────────────────────────────┐    │  │
│  │ Mistakes │  │  │          Quality Evaluator               │    │  │
│  │ Formulas │  │  │  (pass → output, fail → retry/reroute)   │    │  │
│  │ Stats    │  │  └──────────────────────────────────────────┘    │  │
│  └──────────┘  │                                                  │  │
│                │  ┌──────────────────────────────────────────┐    │  │
│  ┌──────────┐  │  │      Conversation Memory (per session)   │    │  │
│  │  RAG     │  │  │  follow-up questions use prior context   │    │  │
│  │  Service │  │  └──────────────────────────────────────────┘    │  │
│  └──────────┘  └──────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌────────────┐   ┌────────────┐   ┌────────────┐
   │ PostgreSQL │   │   Redis    │   │  S3/MinIO  │
   │ + pgvector │   │  Cache +   │   │   Images   │
   │            │   │  Sessions  │   │            │
   └────────────┘   └────────────┘   └────────────┘
```

---

## 3. LangGraph Pipeline Design

### 3.1 Graph Overview

The core solving pipeline is a `StateGraph` that replaces the current single-call `ai_service.solve()`.

```
                    ┌─────────┐
                    │  START  │
                    └────┬────┘
                         ▼
                   ┌───────────┐
                   │    OCR    │  (extract text from image)
                   └─────┬─────┘
                         ▼
                  ┌────────────┐
                  │  Analyze   │  (classify problem, detect subject)
                  └──────┬─────┘
                         ▼
                  ┌────────────┐
              ┌───│  Retrieve  │  (vector search: related formulas + similar problems)
              │   └──────┬─────┘
              │          ▼
              │   ┌────────────┐
              │   │   Solve    │  (LLM generates step-by-step solution)
              │   └──────┬─────┘
              │          ▼
              │   ┌────────────┐
              │   │  Evaluate  │  (auto-grade solution quality)
              │   └──────┬─────┘
              │          │
              │     ┌────┴────┐
              │     ▼         ▼
              │  [pass]    [fail]──→ retry (max 2) ──→ fallback LLM
              │     │
              │     ▼
              │  ┌────────────┐
              │  │  Enrich    │  (attach formulas, tips, difficulty)
              │  └──────┬─────┘
              │         ▼
              │      ┌─────┐
              └──────│ END │
                     └─────┘
```

### 3.2 Graph State

```python
from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, START, END

class SolveState(TypedDict):
    # --- Input ---
    image_bytes: Optional[bytes]
    image_url: str
    user_id: int
    subject: Optional[str]           # user-specified or auto-detected
    grade_level: Optional[str]
    preferred_provider: Optional[str] # "claude" | "openai" | "gemini" | ...

    # --- OCR ---
    ocr_text: str
    ocr_confidence: float

    # --- Analysis ---
    detected_subject: str
    problem_type: str                # "equation", "geometry", "word_problem", ...
    difficulty: str                  # "easy", "medium", "hard"
    knowledge_points: list[str]

    # --- Retrieval (RAG) ---
    related_formulas: list[dict]     # from pgvector similarity search
    similar_problems: list[dict]     # past problems with high embedding similarity

    # --- Solution ---
    solution_raw: str                # raw LLM response
    solution_parsed: dict            # parsed structured solution
    llm_provider: str                # which LLM actually generated
    llm_model: str
    prompt_tokens: int
    completion_tokens: int

    # --- Evaluation ---
    quality_score: float             # 0.0 - 1.0
    quality_issues: list[str]        # ["missing_step", "wrong_calculation", ...]
    attempt_count: int               # retry counter (max 3)

    # --- Enrichment ---
    final_solution: dict             # enriched solution with formulas + tips
    related_formula_ids: list[int]

    # --- Errors ---
    error: Optional[str]
```

### 3.3 Graph Nodes

Each node is an async function `(state: SolveState) -> dict` that returns partial state updates.

#### Node: `ocr`

```python
async def ocr_node(state: SolveState) -> dict:
    """Extract text from image using OCR provider."""
    text, confidence = await ocr_service.extract_text(state["image_bytes"])
    return {"ocr_text": text, "ocr_confidence": confidence}
```

- Provider: Google Cloud Vision / Baidu OCR / Tesseract (unchanged from current)
- No LLM needed

#### Node: `analyze`

```python
async def analyze_node(state: SolveState) -> dict:
    """Classify the problem: subject, type, difficulty, knowledge points."""
    # Uses a fast/cheap model (e.g., Haiku or GPT-4o-mini)
    llm = get_llm("fast")  # configured in settings
    result = await llm.ainvoke(analysis_prompt.format(
        ocr_text=state["ocr_text"],
        grade_level=state.get("grade_level", "unknown"),
    ))
    parsed = parse_analysis(result.content)
    return {
        "detected_subject": state.get("subject") or parsed["subject"],
        "problem_type": parsed["problem_type"],
        "difficulty": parsed["difficulty"],
        "knowledge_points": parsed["knowledge_points"],
    }
```

- LLM: fast/cheap model (Claude Haiku, GPT-4o-mini) — classification doesn't need strong reasoning
- Falls back to keyword-based detection if LLM fails

#### Node: `retrieve`

```python
async def retrieve_node(state: SolveState) -> dict:
    """Vector search for related formulas and similar past problems."""
    embedding = await embed(state["ocr_text"])

    related_formulas = await db.execute(
        select(Formula)
        .order_by(Formula.embedding.cosine_distance(embedding))
        .limit(5)
    )

    similar_problems = await db.execute(
        select(ScanRecord)
        .where(ScanRecord.embedding.isnot(None))
        .order_by(ScanRecord.embedding.cosine_distance(embedding))
        .limit(3)
    )

    return {
        "related_formulas": [f.to_dict() for f in related_formulas],
        "similar_problems": [p.to_dict() for p in similar_problems],
    }
```

- Uses pgvector cosine distance search
- Embedding model: `text-embedding-3-small` (OpenAI) or configurable

#### Node: `solve`

```python
async def solve_node(state: SolveState) -> dict:
    """Generate step-by-step solution using the primary LLM."""
    llm = select_llm(
        preferred=state.get("preferred_provider"),
        subject=state["detected_subject"],
        attempt=state.get("attempt_count", 0),
    )

    context = build_context(
        formulas=state.get("related_formulas", []),
        similar_problems=state.get("similar_problems", []),
    )

    result = await llm.ainvoke(solve_prompt.format(
        subject=state["detected_subject"],
        grade_level=state.get("grade_level", ""),
        problem_text=state["ocr_text"],
        context=context,
    ))

    parsed = parse_solution(result.content)
    usage = result.usage_metadata or {}

    return {
        "solution_raw": result.content,
        "solution_parsed": parsed,
        "llm_provider": llm.provider,
        "llm_model": llm.model_name,
        "prompt_tokens": usage.get("input_tokens", 0),
        "completion_tokens": usage.get("output_tokens", 0),
    }
```

- LLM: selected by subject + user preference + retry fallback
- Context includes RAG-retrieved formulas and similar problems

#### Node: `evaluate`

```python
async def evaluate_node(state: SolveState) -> dict:
    """Auto-grade the solution quality."""
    llm = get_llm("fast")  # use cheap model for evaluation
    result = await llm.ainvoke(evaluate_prompt.format(
        problem=state["ocr_text"],
        solution=state["solution_raw"],
        subject=state["detected_subject"],
    ))
    parsed = parse_evaluation(result.content)
    return {
        "quality_score": parsed["score"],
        "quality_issues": parsed["issues"],
        "attempt_count": state.get("attempt_count", 0) + 1,
    }
```

- Uses a different LLM than the one that generated the solution (cross-check)
- Checks: mathematical correctness, step completeness, grade-appropriate language

#### Node: `enrich`

```python
async def enrich_node(state: SolveState) -> dict:
    """Attach formula references, tips, and metadata to the solution."""
    solution = state["solution_parsed"]
    solution["related_formulas"] = state.get("related_formulas", [])
    solution["difficulty"] = state.get("difficulty", "medium")
    solution["quality_score"] = state.get("quality_score", 0)

    formula_ids = [f["id"] for f in state.get("related_formulas", [])]

    return {
        "final_solution": solution,
        "related_formula_ids": formula_ids,
    }
```

- Pure data transformation, no LLM call

### 3.4 Conditional Edges

```python
def should_retry(state: SolveState) -> Literal["retry", "enrich", "fallback"]:
    """Decide whether to retry, fallback, or accept the solution."""
    score = state.get("quality_score", 0)
    attempts = state.get("attempt_count", 0)

    if score >= 0.7:
        return "enrich"           # quality is good enough
    elif attempts < 3:
        return "retry"            # try again with same or different prompt
    else:
        return "fallback"         # give up, use best attempt so far


def select_fallback(state: SolveState) -> str:
    """On retry, switch to a different LLM provider."""
    # Rotates through providers: claude → openai → gemini → claude
    return "solve"  # re-enter solve node (select_llm uses attempt_count for rotation)
```

### 3.5 Graph Compilation

```python
from langgraph.graph import StateGraph, START, END

def build_solve_graph() -> StateGraph:
    graph = StateGraph(SolveState)

    # Add nodes
    graph.add_node("ocr", ocr_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("solve", solve_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("enrich", enrich_node)

    # Linear flow: START → ocr → analyze → retrieve → solve
    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_edge("retrieve", "solve")
    graph.add_edge("solve", "evaluate")

    # Conditional: evaluate → enrich (pass) or solve (retry)
    graph.add_conditional_edges(
        "evaluate",
        should_retry,
        {
            "enrich": "enrich",
            "retry": "solve",       # retry with rotated LLM
            "fallback": "enrich",   # accept best attempt
        },
    )

    graph.add_edge("enrich", END)

    return graph.compile()

# Singleton
solve_graph = build_solve_graph()
```

### 3.6 LLM Provider Abstraction

Instead of LiteLLM, we use LangChain's `ChatModel` interface which LangGraph natively supports.

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

LLM_REGISTRY: dict[str, type] = {
    "claude":  ChatAnthropic,
    "openai":  ChatOpenAI,
    "gemini":  ChatGoogleGenerativeAI,
}

# Model tiers
MODEL_CONFIG = {
    "claude": {
        "strong": "claude-sonnet-4-20250514",
        "fast":   "claude-haiku-4-5-20251001",
    },
    "openai": {
        "strong": "gpt-4o",
        "fast":   "gpt-4o-mini",
    },
    "gemini": {
        "strong": "gemini-2.0-flash",
        "fast":   "gemini-2.0-flash-lite",
    },
}

# Subject → preferred provider mapping
SUBJECT_PROVIDER_MAP = {
    "math":      "claude",    # best at mathematical reasoning
    "physics":   "claude",
    "chemistry": "openai",
    "biology":   "openai",
    "english":   "openai",
    "chinese":   "claude",
}

def get_llm(tier: str = "strong", provider: str = None) -> BaseChatModel:
    """Get a ChatModel instance by tier and provider."""
    provider = provider or settings.default_ai_provider
    cls = LLM_REGISTRY[provider]
    model = MODEL_CONFIG[provider][tier]
    return cls(model=model, temperature=0.1)

def select_llm(
    preferred: str | None,
    subject: str,
    attempt: int = 0,
) -> BaseChatModel:
    """Select LLM based on preference, subject, and retry rotation."""
    if attempt == 0:
        provider = preferred or SUBJECT_PROVIDER_MAP.get(subject, "claude")
    else:
        # Rotate on retry
        providers = list(LLM_REGISTRY.keys())
        base = preferred or SUBJECT_PROVIDER_MAP.get(subject, "claude")
        idx = providers.index(base)
        provider = providers[(idx + attempt) % len(providers)]

    return get_llm("strong", provider)
```

**Adding a new LLM provider** requires only:
1. `pip install langchain-<provider>`
2. Add to `LLM_REGISTRY` and `MODEL_CONFIG`
3. No graph or service code changes

---

## 4. Conversation Memory

Students should be able to ask follow-up questions after receiving a solution:
- "Explain step 3 in more detail"
- "What if the number was negative?"
- "Show me a similar problem"

### 4.1 Design

Each scan creates a **conversation session**. Follow-up messages append to the session history, and the LLM receives full context.

```
Session: scan_123
  [0] system: You are a math teacher...
  [1] user: Solve 2x + 5 = 15
  [2] assistant: {step-by-step solution}
  [3] user: Explain step 2 more          ← follow-up
  [4] assistant: {detailed explanation}
  [5] user: What if it was 2x + 5 = -3?  ← follow-up
  [6] assistant: {new solution}
```

### 4.2 Storage

Conversation messages are stored in a `conversation_messages` table (see Section 6). For active sessions, messages are also cached in Redis for fast retrieval.

```python
# Redis key format
conversation:{scan_id}:messages → List[JSON messages]
conversation:{scan_id}:ttl     → 24 hours
```

### 4.3 Follow-up Graph

Follow-up questions use a simplified graph (no OCR, no retrieval):

```
START → build_context → generate_reply → END
```

```python
class FollowUpState(TypedDict):
    scan_id: int
    user_message: str
    conversation_history: list[dict]  # prior messages
    solution_context: dict            # original solution
    reply: str

def build_followup_graph() -> StateGraph:
    graph = StateGraph(FollowUpState)
    graph.add_node("build_context", build_context_node)
    graph.add_node("generate_reply", generate_reply_node)
    graph.add_edge(START, "build_context")
    graph.add_edge("build_context", "generate_reply")
    graph.add_edge("generate_reply", END)
    return graph.compile()
```

### 4.4 API

```
POST /api/v1/scan/{scan_id}/followup
  Request:  { "message": "Explain step 3 more" }
  Response: { "reply": "...", "message_id": "..." }

GET /api/v1/scan/{scan_id}/conversation
  Response: { "messages": [...] }
```

---

## 5. Auto-Evaluation System

### 5.1 Purpose

The evaluator checks every generated solution before returning it to the student. This prevents wrong answers, incomplete steps, or grade-inappropriate explanations.

### 5.2 Evaluation Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Correctness | 0.35 | Is the final answer mathematically correct? |
| Completeness | 0.25 | Are all steps shown? No jumps in logic? |
| Clarity | 0.20 | Is the language appropriate for the grade level? |
| Format | 0.10 | Are formulas in LaTeX? Steps properly numbered? |
| Relevance | 0.10 | Are knowledge points and tips relevant? |

### 5.3 Evaluation Prompt

```
You are a senior {subject} teacher reviewing a student solution.

Problem: {problem_text}
Grade Level: {grade_level}
Solution to Review:
{solution}

Score each criterion (0.0 - 1.0):
1. Correctness: Is the final answer correct?
2. Completeness: Are all steps shown?
3. Clarity: Is it understandable for a {grade_level} student?
4. Format: Proper LaTeX, numbered steps?
5. Relevance: Are tips and knowledge points helpful?

Respond in JSON:
{
  "scores": {"correctness": 0.9, "completeness": 0.8, ...},
  "overall": 0.85,
  "issues": ["step 3 skips simplification"],
  "pass": true
}
```

### 5.4 Retry Strategy

```
Attempt 1: Primary LLM (e.g., Claude)
  → Evaluate → score < 0.7 → retry

Attempt 2: Same LLM with refined prompt (include issues from evaluation)
  → Evaluate → score < 0.7 → fallback

Attempt 3: Different LLM (e.g., GPT-4o)
  → Evaluate → accept regardless (use best of 3 attempts)
```

### 5.5 Evaluation Metrics Storage

Every evaluation is saved for analytics:

```sql
-- See evaluation_logs table in Section 6
-- Enables: model quality comparison, subject-level accuracy tracking,
--          identifying weak spots in AI responses
```

---

## 6. Database Design

### 6.1 Overview

PostgreSQL 15+ with pgvector extension. All tables use `BIGSERIAL` primary keys and `TIMESTAMPTZ` timestamps.

### 6.2 ER Diagram

```
┌──────────────┐       ┌──────────────┐       ┌───────────────┐
│    users     │       │ scan_records │       │   solutions   │
├──────────────┤       ├──────────────┤       ├───────────────┤
│ id (PK)      │──┐    │ id (PK)      │──┐    │ id (PK)       │
│ email        │  │    │ user_id (FK) │  │    │ scan_id (FK)  │
│ phone        │  └───<│ image_url    │  └───<│ provider      │
│ password_hash│       │ ocr_text     │       │ model         │
│ nickname     │       │ subject      │       │ content       │
│ avatar_url   │       │ problem_type │       │ steps (JSONB) │
│ grade_level  │       │ difficulty   │       │ quality_score │
│ preferences  │       │ knowledge_pts│       │ tokens_used   │
│ is_active    │       │ embedding    │←vector│ created_at    │
│ created_at   │       │ created_at   │       └───────────────┘
│ updated_at   │       └──────────────┘
└──────────────┘              │
       │                      │
       │               ┌──────┴───────┐
       │               ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌────────────────────┐
│ mistake_books│ │conversation_ │ │  evaluation_logs   │
├──────────────┤ │  messages    │ ├────────────────────┤
│ id (PK)      │ ├──────────────┤ │ id (PK)            │
│ user_id (FK) │ │ id (PK)      │ │ solution_id (FK)   │
│ scan_id (FK) │ │ scan_id (FK) │ │ evaluator_provider │
│ subject      │ │ role         │ │ evaluator_model    │
│ tags (JSONB) │ │ content      │ │ scores (JSONB)     │
│ notes        │ │ metadata     │ │ overall_score      │
│ mastered     │ │ created_at   │ │ issues (JSONB)     │
│ mastery_level│ └──────────────┘ │ attempt_number     │
│ review_count │                  │ created_at         │
│ next_review  │                  └────────────────────┘
│ created_at   │
└──────────────┘

┌──────────────┐  ┌──────────────────┐  ┌────────────────────┐
│   formulas   │  │ knowledge_base   │  │  learning_stats    │
├──────────────┤  ├──────────────────┤  ├────────────────────┤
│ id (PK)      │  │ id (PK)          │  │ id (PK)            │
│ subject      │  │ title            │  │ user_id (FK)       │
│ category     │  │ content          │  │ stat_date          │
│ name         │  │ subject          │  │ subject            │
│ latex        │  │ category         │  │ scan_count         │
│ description  │  │ grade_levels     │  │ correct_count      │
│ grade_levels │  │ source           │  │ avg_quality_score  │
│ keywords     │  │ embedding vector │  │ study_minutes      │
│ related_ids  │  │ metadata (JSONB) │  │ mastered_count     │
│ embedding    │←v│ created_at       │  │ created_at         │
│ created_at   │  └──────────────────┘  └────────────────────┘
└──────────────┘
```

### 6.3 Table DDL

#### users (enhanced)

```sql
CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    phone         VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    nickname      VARCHAR(100),
    avatar_url    TEXT,
    grade_level   VARCHAR(20),
    preferences   JSONB DEFAULT '{}',    -- NEW: {default_provider, language, ...}
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
```

#### scan_records (enhanced)

```sql
CREATE TABLE scan_records (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE CASCADE,
    image_url       TEXT NOT NULL,
    ocr_text        TEXT,
    ocr_confidence  FLOAT,                        -- NEW
    subject         VARCHAR(50),
    problem_type    VARCHAR(50),                   -- NEW: equation, geometry, word_problem
    difficulty      VARCHAR(20),
    knowledge_points JSONB DEFAULT '[]',           -- NEW: ["algebra", "linear_equations"]
    embedding       vector(1536),                  -- NEW: pgvector for similar problem search
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scan_records_user_id ON scan_records(user_id);
CREATE INDEX idx_scan_records_created_at ON scan_records(created_at DESC);
CREATE INDEX idx_scan_records_subject ON scan_records(subject);
CREATE INDEX idx_scan_records_embedding ON scan_records
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

#### solutions (enhanced)

```sql
CREATE TABLE solutions (
    id                BIGSERIAL PRIMARY KEY,
    scan_id           BIGINT REFERENCES scan_records(id) ON DELETE CASCADE,
    provider          VARCHAR(50) NOT NULL,         -- "claude", "openai", "gemini"
    model             VARCHAR(100) NOT NULL,        -- "claude-sonnet-4-20250514"
    content           TEXT NOT NULL,                 -- raw LLM response
    steps             JSONB,                         -- [{step, description, formula, calculation}]
    final_answer      TEXT,                          -- NEW: extracted final answer
    knowledge_points  JSONB DEFAULT '[]',            -- NEW
    quality_score     FLOAT,                         -- NEW: from evaluator (0.0 - 1.0)
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    attempt_number    INTEGER DEFAULT 1,             -- NEW: which attempt produced this
    related_formula_ids JSONB DEFAULT '[]',
    rating            SMALLINT,                      -- user rating (1-5)
    created_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_solutions_scan_id ON solutions(scan_id);
```

#### formulas (enhanced with pgvector)

```sql
CREATE TABLE formulas (
    id            BIGSERIAL PRIMARY KEY,
    subject       VARCHAR(50) NOT NULL,
    category      VARCHAR(100),
    name          VARCHAR(255) NOT NULL,
    latex         TEXT NOT NULL,
    description   TEXT,
    grade_levels  TEXT[] DEFAULT '{}',
    keywords      TEXT[] DEFAULT '{}',
    related_ids   TEXT[] DEFAULT '{}',
    embedding     vector(1536),                     -- NEW: semantic search
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_formulas_subject ON formulas(subject);
CREATE INDEX idx_formulas_embedding ON formulas
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
```

#### mistake_books (enhanced)

```sql
CREATE TABLE mistake_books (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT REFERENCES users(id) ON DELETE CASCADE,
    scan_id       BIGINT REFERENCES scan_records(id) ON DELETE CASCADE,
    subject       VARCHAR(50),                      -- NEW: denormalized for filtering
    tags          JSONB DEFAULT '[]',               -- NEW: user-defined tags
    notes         TEXT,
    mastered      BOOLEAN DEFAULT FALSE,
    mastery_level SMALLINT DEFAULT 0,               -- NEW: 0-5 spaced repetition level
    review_count  INTEGER DEFAULT 0,
    last_reviewed_at TIMESTAMPTZ,                   -- NEW
    next_review_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mistake_books_user_id ON mistake_books(user_id);
CREATE INDEX idx_mistake_books_next_review ON mistake_books(next_review_at)
    WHERE mastered = FALSE;
CREATE UNIQUE INDEX idx_mistake_books_user_scan ON mistake_books(user_id, scan_id);
```

#### conversation_messages (NEW)

```sql
CREATE TABLE conversation_messages (
    id          BIGSERIAL PRIMARY KEY,
    scan_id     BIGINT REFERENCES scan_records(id) ON DELETE CASCADE,
    role        VARCHAR(20) NOT NULL,              -- "system", "user", "assistant"
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',                -- {tokens, model, latency_ms, ...}
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversation_messages_scan_id ON conversation_messages(scan_id);
```

#### evaluation_logs (NEW)

```sql
CREATE TABLE evaluation_logs (
    id                  BIGSERIAL PRIMARY KEY,
    solution_id         BIGINT REFERENCES solutions(id) ON DELETE CASCADE,
    evaluator_provider  VARCHAR(50) NOT NULL,
    evaluator_model     VARCHAR(100) NOT NULL,
    scores              JSONB NOT NULL,            -- {correctness: 0.9, completeness: 0.8, ...}
    overall_score       FLOAT NOT NULL,
    issues              JSONB DEFAULT '[]',        -- ["missing step 3", "wrong sign"]
    passed              BOOLEAN NOT NULL,
    attempt_number      INTEGER NOT NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_evaluation_logs_solution_id ON evaluation_logs(solution_id);
```

#### knowledge_base (NEW — for future RAG expansion)

```sql
CREATE TABLE knowledge_base (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(500) NOT NULL,
    content     TEXT NOT NULL,
    subject     VARCHAR(50) NOT NULL,
    category    VARCHAR(100),
    grade_levels TEXT[] DEFAULT '{}',
    source      VARCHAR(255),                      -- "textbook:math_7th", "curriculum:2024"
    metadata    JSONB DEFAULT '{}',
    embedding   vector(1536) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_knowledge_base_subject ON knowledge_base(subject);
CREATE INDEX idx_knowledge_base_embedding ON knowledge_base
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

#### learning_stats (enhanced)

```sql
CREATE TABLE learning_stats (
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT REFERENCES users(id) ON DELETE CASCADE,
    stat_date         DATE NOT NULL,
    subject           VARCHAR(50) NOT NULL,
    scan_count        INTEGER DEFAULT 0,
    correct_count     INTEGER DEFAULT 0,
    avg_quality_score FLOAT DEFAULT 0,              -- NEW: average solution quality
    study_minutes     INTEGER DEFAULT 0,
    mastered_count    INTEGER DEFAULT 0,             -- NEW: mistakes mastered today
    created_at        TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, stat_date, subject)
);

CREATE INDEX idx_learning_stats_user_date ON learning_stats(user_id, stat_date DESC);
```

### 6.4 pgvector Setup

```sql
-- Enable the extension (run once)
CREATE EXTENSION IF NOT EXISTS vector;

-- Embedding dimension: 1536 (OpenAI text-embedding-3-small)
-- Alternative: 1024 (Cohere), 768 (sentence-transformers)
-- Configure in settings: EMBEDDING_DIMENSION=1536
```

**Docker Compose** — use pgvector-enabled image:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: eduscan
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

---

## 7. RAG Pipeline

### 7.1 Embedding Generation

Embeddings are generated asynchronously when records are created or updated.

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

async def embed_text(text: str) -> list[float]:
    """Generate embedding vector for text."""
    return await embeddings.aembed_query(text)
```

**When embeddings are generated:**

| Event | Table | What gets embedded |
|-------|-------|-------------------|
| Formula created/updated | `formulas` | `name + description + keywords` |
| Scan completed | `scan_records` | `ocr_text` |
| Knowledge base entry added | `knowledge_base` | `title + content` |

### 7.2 Retrieval in Solve Graph

The `retrieve` node performs two vector searches:

1. **Formula retrieval**: Find formulas semantically related to the problem
2. **Similar problem retrieval**: Find past problems with similar embeddings (for context)

```python
async def retrieve_node(state: SolveState) -> dict:
    query_embedding = await embed_text(state["ocr_text"])

    # 1. Related formulas (top 5)
    formulas = await formula_repo.vector_search(
        embedding=query_embedding,
        subject=state.get("detected_subject"),
        limit=5,
    )

    # 2. Similar past problems (top 3, same grade level)
    similar = await scan_repo.vector_search(
        embedding=query_embedding,
        grade_level=state.get("grade_level"),
        limit=3,
    )

    return {
        "related_formulas": formulas,
        "similar_problems": similar,
    }
```

### 7.3 Context Injection

Retrieved context is injected into the solve prompt:

```
## Related Formulas
{for each formula: name, latex, description}

## Similar Problems (for reference)
{for each: problem text, solution approach — NOT the full solution}

## Problem to Solve
{ocr_text}
```

---

## 8. Service Layer Changes

### 8.1 New Directory Structure

```
backend/app/
├── api/
│   ├── deps.py
│   └── v1/
│       ├── router.py
│       ├── auth.py
│       ├── scan.py               # updated: uses graph, adds followup endpoint
│       ├── history.py
│       ├── mistakes.py
│       ├── formulas.py
│       └── stats.py              # NEW: learning stats endpoints
├── graph/                        # NEW: LangGraph pipeline
│   ├── __init__.py
│   ├── state.py                  # SolveState, FollowUpState definitions
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── ocr.py                # ocr_node
│   │   ├── analyze.py            # analyze_node
│   │   ├── retrieve.py           # retrieve_node (RAG)
│   │   ├── solve.py              # solve_node
│   │   ├── evaluate.py           # evaluate_node
│   │   └── enrich.py             # enrich_node
│   ├── edges.py                  # should_retry, routing functions
│   ├── solve_graph.py            # build_solve_graph()
│   └── followup_graph.py         # build_followup_graph()
├── llm/                          # NEW: LLM provider abstraction
│   ├── __init__.py
│   ├── registry.py               # LLM_REGISTRY, get_llm(), select_llm()
│   ├── embeddings.py             # embed_text(), embedding model config
│   └── prompts/
│       ├── __init__.py
│       ├── analysis.py           # problem analysis prompt
│       ├── solve.py              # solution generation prompt
│       ├── evaluate.py           # evaluation prompt
│       └── followup.py           # follow-up conversation prompt
├── services/
│   ├── auth_service.py           # unchanged
│   ├── scan_service.py           # refactored: delegates to graph
│   ├── ocr_service.py            # unchanged (provider pattern)
│   ├── formula_service.py        # enhanced: vector search
│   ├── storage_service.py        # unchanged
│   ├── conversation_service.py   # NEW: manage conversation history
│   ├── embedding_service.py      # NEW: generate/update embeddings
│   └── stats_service.py          # NEW: learning statistics
├── repositories/                 # NEW: data access layer
│   ├── __init__.py
│   ├── scan_repo.py              # vector search + CRUD
│   ├── formula_repo.py           # vector search + CRUD
│   ├── mistake_repo.py
│   ├── conversation_repo.py
│   └── knowledge_repo.py
├── models/                       # enhanced ORM models
│   ├── user.py
│   ├── scan_record.py            # + embedding column
│   ├── solution.py               # + quality_score, attempt_number
│   ├── mistake_book.py           # + tags, mastery_level
│   ├── formula.py                # + embedding column
│   ├── learning_stats.py         # + avg_quality_score, mastered_count
│   ├── conversation_message.py   # NEW
│   ├── evaluation_log.py         # NEW
│   └── knowledge_base.py         # NEW
├── schemas/                      # enhanced Pydantic schemas
│   ├── auth.py
│   ├── scan.py                   # + FollowUpRequest, ConversationResponse
│   ├── mistake.py                # + tags, mastery_level
│   ├── formula.py
│   ├── stats.py                  # NEW
│   ├── evaluation.py             # NEW
│   └── common.py
├── core/
│   ├── security.py
│   ├── exceptions.py
│   └── middleware.py
├── config.py                     # enhanced with LLM + embedding settings
├── database.py
└── main.py
```

### 8.2 scan_service.py (Refactored)

```python
class ScanService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph = solve_graph        # compiled LangGraph
        self.followup_graph = followup_graph

    async def scan_and_solve(
        self, user_id: int, image: UploadFile, **kwargs
    ) -> ScanResponse:
        # 1. Upload image
        image_url = await storage_service.upload_image(image)
        image_bytes = await image.read()

        # 2. Run the LangGraph pipeline
        result = await self.graph.ainvoke({
            "image_bytes": image_bytes,
            "image_url": image_url,
            "user_id": user_id,
            "subject": kwargs.get("subject"),
            "grade_level": kwargs.get("grade_level"),
            "preferred_provider": kwargs.get("ai_provider"),
            "attempt_count": 0,
        })

        # 3. Persist to database
        scan_record = await self._save_scan(user_id, result)
        await self._save_solution(scan_record.id, result)
        await self._save_initial_conversation(scan_record.id, result)

        # 4. Generate embedding async (background task)
        await embedding_service.embed_scan_record(scan_record.id, result["ocr_text"])

        return self._build_response(scan_record, result)

    async def followup(
        self, scan_id: int, user_id: int, message: str
    ) -> FollowUpResponse:
        # 1. Load conversation history
        history = await conversation_service.get_history(scan_id)

        # 2. Run follow-up graph
        result = await self.followup_graph.ainvoke({
            "scan_id": scan_id,
            "user_message": message,
            "conversation_history": history,
            "solution_context": await self._get_solution_context(scan_id),
        })

        # 3. Save messages
        await conversation_service.add_message(scan_id, "user", message)
        await conversation_service.add_message(scan_id, "assistant", result["reply"])

        return FollowUpResponse(reply=result["reply"])
```

---

## 9. API Changes

### 9.1 New Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/scan/{scan_id}/followup` | Send follow-up question |
| GET | `/api/v1/scan/{scan_id}/conversation` | Get conversation history |
| GET | `/api/v1/stats/summary` | Learning stats summary |
| GET | `/api/v1/stats/daily` | Daily learning stats |
| GET | `/api/v1/formulas/search` | Semantic formula search (vector) |

### 9.2 Enhanced Endpoints

| Endpoint | Changes |
|----------|---------|
| `POST /api/v1/scan/solve` | Response now includes `quality_score`, `attempt_count` |
| `GET /api/v1/mistakes` | New query params: `tags`, `mastery_level` |
| `PATCH /api/v1/mistakes/{id}` | Can now update `tags`, `mastery_level` |
| `GET /api/v1/formulas` | New `semantic_query` param for vector search |

### 9.3 Follow-up API Detail

```yaml
POST /api/v1/scan/{scan_id}/followup
  Headers: Authorization: Bearer {token}
  Request:
    message: string (required)
  Response:
    reply: string
    message_id: string
    tokens_used: integer

GET /api/v1/scan/{scan_id}/conversation
  Headers: Authorization: Bearer {token}
  Response:
    messages:
      - id: string
        role: "user" | "assistant" | "system"
        content: string
        created_at: datetime
    total_messages: integer
```

---

## 10. Configuration

### 10.1 New Settings (config.py)

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # LLM Providers (LangChain)
    default_ai_provider: str = "claude"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""

    # Model Configuration
    strong_model_claude: str = "claude-sonnet-4-20250514"
    fast_model_claude: str = "claude-haiku-4-5-20251001"
    strong_model_openai: str = "gpt-4o"
    fast_model_openai: str = "gpt-4o-mini"
    strong_model_gemini: str = "gemini-2.0-flash"
    fast_model_gemini: str = "gemini-2.0-flash-lite"

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # LangGraph
    max_solve_attempts: int = 3
    min_quality_score: float = 0.7

    # Conversation
    max_followup_messages: int = 20
    conversation_ttl_hours: int = 24

    # Observability (optional)
    langsmith_api_key: str = ""
    langsmith_project: str = "eduscan"
```

### 10.2 .env.example additions

```env
# LLM Providers
DEFAULT_AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AI...

# Embeddings
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536

# LangGraph
MAX_SOLVE_ATTEMPTS=3
MIN_QUALITY_SCORE=0.7

# LangSmith (optional, for tracing)
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=eduscan
```

---

## 11. Dependencies

### 11.1 New requirements.txt

```text
# --- Core Framework ---
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6

# --- Database ---
sqlalchemy>=2.0.25
asyncpg>=0.29.0
alembic>=1.13.1
pgvector>=0.3.0                    # NEW: pgvector Python bindings

# --- Authentication ---
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# --- LangGraph + LangChain ---          # NEW: replaces litellm
langgraph>=1.0.0
langchain-core>=0.3.0
langchain-anthropic>=0.3.0
langchain-openai>=0.3.0
langchain-google-genai>=2.0.0

# --- Storage ---
boto3==1.34.14
Pillow>=11.0.0

# --- Cache ---
redis>=5.0.1

# --- Utilities ---
httpx>=0.26.0
python-dotenv>=1.0.0
pydantic>=2.5.3
pydantic-settings>=2.1.0
email-validator>=2.1.0

# --- Observability (optional) ---
langsmith>=0.2.0                   # NEW: LangGraph tracing
```

### 11.2 Removed

```text
litellm    # replaced by langchain-* + langgraph
```

---

## 12. Docker Compose (Updated)

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: eduscan
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

---

## 13. Migration Plan

### Phase 1: Infrastructure (Week 1)
1. Update docker-compose to use `pgvector/pgvector:pg16`
2. Create Alembic migration: enable pgvector extension, add new tables and columns
3. Update `requirements.txt` (add langchain/langgraph, remove litellm)
4. Update `config.py` with new settings

### Phase 2: LLM Layer (Week 1-2)
1. Create `app/llm/` module with registry, embeddings, prompts
2. Verify all three providers (Claude, OpenAI, Gemini) work through LangChain
3. Write unit tests for LLM selection and fallback

### Phase 3: LangGraph Pipeline (Week 2-3)
1. Create `app/graph/` module with state, nodes, edges
2. Implement each node: ocr → analyze → retrieve → solve → evaluate → enrich
3. Wire up conditional edges (retry, fallback)
4. Integration tests for full pipeline

### Phase 4: Conversation + Evaluation (Week 3-4)
1. Implement `conversation_service` and `conversation_messages` table
2. Build follow-up graph
3. Implement evaluation node and `evaluation_logs` table
4. Add `/followup` and `/conversation` API endpoints

### Phase 5: RAG + Embeddings (Week 4-5)
1. Implement `embedding_service` with background embedding generation
2. Add vector columns to formulas and scan_records
3. Backfill embeddings for existing data
4. Implement vector search in `retrieve` node
5. Create `knowledge_base` table (empty, ready for content)

### Phase 6: Testing + Cleanup (Week 5-6)
1. End-to-end tests for full solve pipeline
2. Load testing for vector search performance
3. Remove old `ai_service.py` (replaced by graph)
4. Update API documentation
5. Update CLAUDE.md

---

## 14. Observability

### 14.1 LangSmith Integration (Optional)

LangGraph natively supports [LangSmith](https://smith.langchain.com) tracing. When `LANGSMITH_API_KEY` is set, every graph invocation is automatically traced with:

- Full node execution timeline
- LLM inputs/outputs per node
- Token usage per node
- Latency breakdown
- Error traces

### 14.2 Custom Metrics

Log to `evaluation_logs` table for internal analytics:

```python
# Example queries
# 1. Model quality comparison
SELECT provider, AVG(overall_score) FROM evaluation_logs
GROUP BY provider;

# 2. Subject accuracy
SELECT s.subject, AVG(e.overall_score)
FROM evaluation_logs e
JOIN solutions sol ON sol.id = e.solution_id
JOIN scan_records s ON s.id = sol.scan_id
GROUP BY s.subject;

# 3. Retry rate
SELECT provider, AVG(attempt_number) FROM solutions GROUP BY provider;
```

---

## 15. Spaced Repetition for Mistake Book

The mistake book uses **SM-2 algorithm** (SuperMemo) for review scheduling:

```python
def calculate_next_review(
    mastery_level: int,
    quality: int,     # 0-5, from user self-assessment
) -> tuple[int, datetime]:
    """Returns (new_mastery_level, next_review_date)."""
    if quality < 3:
        # Reset to level 0, review tomorrow
        return 0, now() + timedelta(days=1)

    intervals = [1, 3, 7, 14, 30, 90]  # days
    new_level = min(mastery_level + 1, 5)
    next_date = now() + timedelta(days=intervals[new_level])
    return new_level, next_date
```

| Mastery Level | Interval | Meaning |
|---------------|----------|---------|
| 0 | 1 day | Just added / reset |
| 1 | 3 days | Reviewed once |
| 2 | 7 days | Getting familiar |
| 3 | 14 days | Comfortable |
| 4 | 30 days | Well understood |
| 5 | 90 days | Mastered (final review) |

---

## Appendix A: Adding a New LLM Provider

Example: adding DeepSeek

```python
# 1. Install
# pip install langchain-deepseek

# 2. Register in llm/registry.py
from langchain_deepseek import ChatDeepSeek

LLM_REGISTRY["deepseek"] = ChatDeepSeek
MODEL_CONFIG["deepseek"] = {
    "strong": "deepseek-chat",
    "fast": "deepseek-chat",
}

# 3. Add API key to config.py
deepseek_api_key: str = ""

# 4. (Optional) Map subjects
SUBJECT_PROVIDER_MAP["math"] = "deepseek"  # if preferred for math

# Done. No graph changes needed.
```

## Appendix B: Adding a New Graph Node

Example: adding a "hints" node that generates study hints.

```python
# 1. Create app/graph/nodes/hints.py
async def hints_node(state: SolveState) -> dict:
    llm = get_llm("fast")
    result = await llm.ainvoke(hints_prompt.format(...))
    return {"study_hints": parse_hints(result.content)}

# 2. Add to SolveState
class SolveState(TypedDict):
    ...
    study_hints: list[str]

# 3. Wire into graph (solve_graph.py)
graph.add_node("hints", hints_node)
graph.add_edge("enrich", "hints")  # after enrich
graph.add_edge("hints", END)       # replace enrich → END
```

---

*Document Version: 3.0*
*Last Updated: February 2026*
