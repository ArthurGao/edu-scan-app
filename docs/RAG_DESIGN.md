# EduScan RAG System Design

## 1. Overview

### Current Problem

Every problem-solving request triggers a full LLM pipeline (`OCR → ANALYZE → RETRIEVE → SOLVE → VERIFY → ENRICH`), with `retrieve_node` returning empty results. This means:

- **No reuse** of previously solved identical/similar problems
- **No formula context** injected into solve prompts (keyword matching exists but is disconnected from the graph)
- **No personalization** — user's mistake history is never consulted during solving
- **Every request = fresh API call** — high latency, high cost

### Goal

Implement a three-tier RAG system that:

1. **Cache-hits identical problems** — skip LLM entirely (~30-50% of K12 traffic)
2. **Inject similar problems + formulas** as context — improve quality, reduce retries
3. **Personalize via mistake history** — differentiated user experience

### Expected Impact

| Metric | Before | After |
|--------|--------|-------|
| API calls per solve | 3-5 (analyze + solve + verify + retries) | 0 (cache hit) or 2-4 |
| Average latency | ~8-12s | ~0.5s (cache hit) or ~7-10s (with better first-attempt quality) |
| Retry rate | ~20% (verify fails) | ~8% (better context = better first attempt) |
| Monthly LLM cost | 100% baseline | ~55-65% of baseline |

---

## 2. Architecture

### 2.1 High-Level Flow

```
                         ┌─────────────────────┐
                         │   Incoming Problem   │
                         │  (ocr_text, subject) │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  1. Exact Match Cache │ ◄── Redis / pgvector cosine ≥ 0.98
                         │   (hash or vector)   │
                         └──────────┬──────────┘
                               ┌────┴────┐
                            HIT│         │MISS
                               ▼         ▼
                    ┌──────────────┐  ┌─────────────────────┐
                    │ Return cached │  │ 2. Semantic Retrieval │
                    │ solution     │  │  (pgvector search)   │
                    │ immediately  │  └──────────┬──────────┘
                    └──────────────┘             │
                                                 ▼
                                      ┌─────────────────────┐
                                      │ 3. Build RAG Context │
                                      │  • similar problems  │
                                      │  • related formulas  │
                                      │  • user mistakes     │
                                      └──────────┬──────────┘
                                                 │
                                                 ▼
                                      ┌─────────────────────┐
                                      │ 4. SOLVE with context│
                                      │  (existing pipeline) │
                                      └──────────┬──────────┘
                                                 │
                                                 ▼
                                      ┌─────────────────────┐
                                      │ 5. Store embedding   │
                                      │  (async, post-solve) │
                                      └─────────────────────┘
```

### 2.2 Modified LangGraph Pipeline

```
Current:  OCR → ANALYZE → RETRIEVE(empty) → SOLVE → VERIFY → ENRICH
                              │
New:      OCR → ANALYZE → CACHE_CHECK ──HIT──→ ENRICH → END
                              │
                             MISS
                              │
                          RETRIEVE(real) → SOLVE → VERIFY → ENRICH → STORE_EMBEDDING
```

The graph gains two new nodes: `cache_check` (before retrieve) and `store_embedding` (after enrich, async).

---

## 3. Vector Database Design

### 3.1 pgvector Setup

We use PostgreSQL + pgvector (already a dependency). No separate vector DB needed.

```sql
-- Migration: enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Index for scan_records (HNSW for fast approximate search)
CREATE INDEX idx_scan_records_embedding
  ON scan_records
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Index for formulas (add embedding column first)
ALTER TABLE formulas ADD COLUMN embedding vector(1536);

CREATE INDEX idx_formulas_embedding
  ON formulas
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Index for knowledge_base (already has embedding column)
CREATE INDEX idx_knowledge_base_embedding
  ON knowledge_base
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);
```

**Why HNSW over IVFFlat:**
- HNSW: better recall at low latency, no training step, good for incremental inserts
- Our dataset size (< 1M rows) fits HNSW well

### 3.2 Embedding Model

| Setting | Value |
|---------|-------|
| Model | `text-embedding-3-small` (already configured) |
| Dimension | 1536 |
| Provider | OpenAI |
| Cost | ~$0.02 / 1M tokens |

**Embedding text construction** — what we embed per record type:

```python
# scan_record: combine OCR text + metadata for richer matching
def build_scan_embedding_text(ocr_text: str, subject: str, knowledge_points: list[str]) -> str:
    parts = [ocr_text]
    if subject:
        parts.append(f"Subject: {subject}")
    if knowledge_points:
        parts.append(f"Concepts: {', '.join(knowledge_points)}")
    return "\n".join(parts)

# formula: combine name + description + keywords
def build_formula_embedding_text(name: str, description: str, keywords: list[str]) -> str:
    parts = [name]
    if description:
        parts.append(description)
    if keywords:
        parts.append(f"Keywords: {', '.join(keywords)}")
    return "\n".join(parts)
```

### 3.3 Similarity Thresholds

| Threshold | Cosine Distance | Action |
|-----------|----------------|--------|
| **Exact match** | ≥ 0.98 | Return cached solution directly |
| **High similarity** | 0.90 - 0.97 | Use as few-shot example in prompt |
| **Related** | 0.80 - 0.89 | Include as "similar problem" reference |
| **Irrelevant** | < 0.80 | Discard |

---

## 4. Three RAG Cases — Detailed Design

### Case 1: Similar Problem Retrieval (Highest Impact)

**Goal:** Find previously solved problems similar to the current one, to either skip LLM or provide few-shot examples.

#### Data Source

Table: `scan_records` + `solutions` (JOIN)

```
scan_records.embedding (vector) ← search target
scan_records.ocr_text           ← original problem text
scan_records.subject            ← filter
scan_records.knowledge_points   ← metadata
solutions.steps (JSONB)         ← cached answer
solutions.final_answer          ← cached answer
solutions.quality_score         ← only use high-quality solutions
solutions.verification_status   ← only use verified solutions
```

#### Query Logic

```python
# In retrieve_node or cache_check_node
async def find_similar_problems(
    db: AsyncSession,
    query_embedding: list[float],
    subject: str | None = None,
    limit: int = 5,
    min_quality: float = 0.7,
) -> list[dict]:
    """
    Vector search for similar previously-solved problems.
    Only returns problems with verified, high-quality solutions.
    """
    filters = [
        ScanRecord.embedding.isnot(None),
        Solution.quality_score >= min_quality,
        Solution.verification_status.in_(["verified", "caution"]),
    ]
    if subject:
        filters.append(ScanRecord.subject == subject)

    query = (
        select(
            ScanRecord.id,
            ScanRecord.ocr_text,
            ScanRecord.subject,
            ScanRecord.knowledge_points,
            Solution.steps,
            Solution.final_answer,
            ScanRecord.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .join(Solution, Solution.scan_id == ScanRecord.id)
        .where(and_(*filters))
        .order_by("distance")
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "scan_id": r.id,
            "ocr_text": r.ocr_text,
            "subject": r.subject,
            "knowledge_points": r.knowledge_points,
            "steps": r.steps,
            "final_answer": r.final_answer,
            "similarity": 1 - r.distance,  # cosine similarity
        }
        for r in rows
    ]
```

#### Cache Hit Logic

```python
async def cache_check_node(state: SolveState) -> dict:
    """Check if an identical or near-identical problem was already solved."""
    ocr_text = state.get("ocr_text", "")
    subject = state.get("detected_subject")

    embedding = await embed_text(ocr_text)
    similar = await find_similar_problems(db, embedding, subject, limit=1)

    if similar and similar[0]["similarity"] >= 0.98:
        # Exact match — reuse cached solution
        cached = similar[0]
        return {
            "cache_hit": True,
            "solution_parsed": {
                "steps": cached["steps"],
                "final_answer": cached["final_answer"],
                "knowledge_points": cached["knowledge_points"],
                "question_type": "cached",
            },
            "similar_problems": [],
            "query_embedding": embedding,
        }

    # No cache hit — pass embedding + similar problems downstream
    return {
        "cache_hit": False,
        "similar_problems": [s for s in similar if s["similarity"] >= 0.80],
        "query_embedding": embedding,
    }
```

#### Embedding Storage (Post-Solve)

```python
async def store_embedding_node(state: SolveState) -> dict:
    """Store embedding for the newly solved problem (async, non-blocking)."""
    # Only store if we didn't hit cache (new problem)
    if state.get("cache_hit"):
        return {}

    embedding = state.get("query_embedding")
    scan_id = state.get("scan_id")

    if embedding and scan_id:
        await embedding_service.store_scan_embedding(scan_id, embedding)

    return {}
```

#### Context Injection Format

When similar problems are found but not exact matches, inject into the solve prompt:

```markdown
## Similar Problems (for reference)

### Similar Problem 1 (92% match)
**Problem:** Find the area of a triangle with base 6cm and height 4cm
**Answer:** 12 cm²
**Key Steps:** Used formula A = ½ × b × h

### Similar Problem 2 (85% match)
**Problem:** Calculate the area of a triangle with sides 3, 4, 5
**Answer:** 6 cm²
**Key Steps:** Used Heron's formula
```

---

### Case 2: Formula Semantic Retrieval

**Goal:** Replace keyword-based formula matching with vector search for more accurate formula context.

#### Data Source

Table: `formulas`

```
formulas.embedding    ← search target (new column)
formulas.name         ← formula name
formulas.latex        ← LaTeX representation
formulas.description  ← what it does
formulas.subject      ← filter
formulas.grade_levels ← filter
formulas.keywords     ← fallback for keyword search
```

#### Query Logic

```python
async def find_related_formulas_vector(
    db: AsyncSession,
    query_embedding: list[float],
    subject: str | None = None,
    grade_level: str | None = None,
    limit: int = 5,
) -> list[dict]:
    """Semantic search for related formulas."""
    filters = [Formula.embedding.isnot(None)]
    if subject:
        filters.append(Formula.subject == subject)
    if grade_level:
        filters.append(Formula.grade_levels.any(grade_level))

    query = (
        select(
            Formula.id,
            Formula.name,
            Formula.latex,
            Formula.description,
            Formula.category,
            Formula.embedding.cosine_distance(query_embedding).label("distance"),
        )
        .where(and_(*filters))
        .order_by("distance")
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "latex": r.latex,
            "description": r.description,
            "category": r.category,
            "similarity": 1 - r.distance,
        }
        for r in rows
        if (1 - r.distance) >= 0.75  # minimum relevance threshold
    ]
```

#### Hybrid Search Strategy

Combine vector search with existing keyword search for best results:

```python
async def find_formulas_hybrid(
    db: AsyncSession,
    query_embedding: list[float],
    problem_text: str,
    subject: str | None = None,
) -> list[dict]:
    """Hybrid: vector search + keyword fallback, deduplicated."""
    # 1. Vector search (primary)
    vector_results = await find_related_formulas_vector(db, query_embedding, subject, limit=5)

    # 2. Keyword search (fallback, existing logic)
    keyword_results = await formula_service.find_related_formulas(problem_text, subject)

    # 3. Merge and deduplicate, prefer vector results
    seen_ids = {r["id"] for r in vector_results}
    merged = list(vector_results)
    for kr in keyword_results:
        if int(kr.id) not in seen_ids:
            merged.append({
                "id": int(kr.id),
                "name": kr.name,
                "latex": kr.latex,
                "description": kr.description,
                "similarity": 0.70,  # keyword match gets a default score
            })

    return merged[:8]  # cap at 8 formulas
```

#### Context Injection Format

```markdown
## Related Formulas

- **Pythagorean Theorem**: `a^2 + b^2 = c^2` — Relates sides of a right triangle (95% relevant)
- **Triangle Area**: `A = \frac{1}{2}bh` — Area using base and height (88% relevant)
- **Heron's Formula**: `A = \sqrt{s(s-a)(s-b)(s-c)}` — Area from three sides (82% relevant)
```

---

### Case 3: Mistake Book Personalization

**Goal:** Query user's past mistakes to inject personalized coaching context into the solve prompt.

#### Data Source

Tables: `mistake_books` JOIN `scan_records` JOIN `solutions`

```
mistake_books.user_id          ← filter by current user
mistake_books.scan_id          → scan_records.id
mistake_books.subject          ← filter
mistake_books.tags             ← knowledge point tags
mistake_books.mastered         ← skip mastered items
mistake_books.mastery_level    ← prioritize low mastery
scan_records.ocr_text          ← original problem
scan_records.knowledge_points  ← concept overlap check
solutions.final_answer         ← what the answer was
```

#### Query Logic

```python
async def find_relevant_mistakes(
    db: AsyncSession,
    user_id: int,
    current_knowledge_points: list[str],
    subject: str | None = None,
    limit: int = 3,
) -> list[dict]:
    """
    Find user's past mistakes related to current problem's knowledge points.
    Prioritizes unmastered items with low mastery levels.
    """
    filters = [
        MistakeBook.user_id == user_id,
        MistakeBook.mastered == False,  # only unmastered
    ]
    if subject:
        filters.append(MistakeBook.subject == subject)

    query = (
        select(
            MistakeBook.id,
            MistakeBook.tags,
            MistakeBook.mastery_level,
            MistakeBook.notes,
            ScanRecord.ocr_text,
            ScanRecord.knowledge_points,
        )
        .join(ScanRecord, ScanRecord.id == MistakeBook.scan_id)
        .where(and_(*filters))
        .order_by(MistakeBook.mastery_level.asc())  # lowest mastery first
        .limit(20)  # fetch more, then filter by relevance
    )

    result = await db.execute(query)
    rows = result.all()

    # Filter by knowledge point overlap
    current_kp_set = set(kp.lower() for kp in current_knowledge_points)
    relevant = []
    for r in rows:
        row_kps = set(kp.lower() for kp in (r.knowledge_points or []))
        overlap = current_kp_set & row_kps
        if overlap:
            relevant.append({
                "mistake_id": r.id,
                "ocr_text": r.ocr_text[:200],
                "knowledge_points": list(overlap),
                "mastery_level": r.mastery_level,
                "notes": r.notes,
            })

    return relevant[:limit]
```

#### Context Injection Format

```markdown
## Personalized Notes

Based on your study history, pay attention to these areas:

- **Quadratic formula**: You've made mistakes on this concept before (mastery: 2/5).
  Previous error: Forgot to consider the ± sign when taking square root.
- **Factoring**: Similar problem in your mistake book (mastery: 1/5).
  Your note: "Always check if common factor exists first"
```

#### Guest Mode Handling

Guest users (`solve-guest` endpoint) have no `user_id`, so mistake personalization is skipped. The retrieve node checks:

```python
if user_id and user_id > 0:  # authenticated user
    mistakes = await find_relevant_mistakes(db, user_id, knowledge_points, subject)
else:
    mistakes = []  # guest mode — no personalization
```

---

## 5. Redis Cache Layer

### 5.1 Purpose

Fast exact-match cache before hitting pgvector. For identical OCR text, return instantly.

### 5.2 Cache Key Design

```python
import hashlib

def make_cache_key(ocr_text: str, subject: str | None = None) -> str:
    """Deterministic cache key from normalized problem text."""
    normalized = ocr_text.strip().lower()
    if subject:
        normalized = f"{subject}:{normalized}"
    hash_val = hashlib.sha256(normalized.encode()).hexdigest()[:16]
    return f"eduscan:solution:{hash_val}"
```

### 5.3 Cache Schema

```python
# Stored as JSON in Redis
{
    "scan_id": 1234,
    "solution": {
        "steps": [...],
        "final_answer": "...",
        "knowledge_points": [...],
        "question_type": "..."
    },
    "quality_score": 0.92,
    "created_at": "2026-03-01T10:00:00Z",
    "hit_count": 5
}
```

### 5.4 TTL and Invalidation

| Policy | Value | Reason |
|--------|-------|--------|
| Default TTL | 7 days | K12 problems are stable, solutions don't change |
| Min quality to cache | 0.8 | Only cache high-quality verified solutions |
| Max cache size | 10,000 entries | ~20MB, fits comfortably in Redis |
| Invalidation | On solution re-rating (user thumbs-down) | Remove bad solutions from cache |

### 5.5 Cache Flow

```python
async def check_redis_cache(ocr_text: str, subject: str | None) -> dict | None:
    key = make_cache_key(ocr_text, subject)
    cached = await redis.get(key)
    if cached:
        data = json.loads(cached)
        # Increment hit count
        data["hit_count"] = data.get("hit_count", 0) + 1
        await redis.set(key, json.dumps(data), ex=7 * 86400)
        return data
    return None


async def store_redis_cache(
    ocr_text: str,
    subject: str | None,
    scan_id: int,
    solution: dict,
    quality_score: float,
) -> None:
    if quality_score < 0.8:
        return  # don't cache low-quality solutions
    key = make_cache_key(ocr_text, subject)
    data = {
        "scan_id": scan_id,
        "solution": solution,
        "quality_score": quality_score,
        "created_at": datetime.utcnow().isoformat(),
        "hit_count": 0,
    }
    await redis.set(key, json.dumps(data), ex=7 * 86400)
```

---

## 6. Updated LangGraph Pipeline

### 6.1 New State Fields

Add to `SolveState` in `app/graph/state.py`:

```python
class SolveState(TypedDict, total=False):
    # ... existing fields ...

    # RAG additions
    cache_hit: bool                    # whether exact cache hit occurred
    query_embedding: list[float]       # embedding of current problem
    user_mistakes: list[dict]          # relevant mistakes from user's history
    scan_id: int                       # needed for embedding storage
```

### 6.2 New Graph Topology

```python
# app/graph/solve_graph.py

def build_solve_graph():
    graph = StateGraph(SolveState)

    # Nodes
    graph.add_node("ocr", ocr_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("cache_check", cache_check_node)      # NEW
    graph.add_node("retrieve", retrieve_node)             # UPDATED (real logic)
    graph.add_node("solve", solve_node)
    graph.add_node("quick_verify", quick_verify_node)
    graph.add_node("enrich", enrich_node)
    graph.add_node("store_embedding", store_embedding_node)  # NEW

    # Edges
    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "analyze")
    graph.add_edge("analyze", "cache_check")              # CHANGED

    # Conditional: cache hit → skip to enrich; miss → retrieve
    graph.add_conditional_edges(
        "cache_check",
        route_after_cache_check,
        {
            "enrich": "enrich",      # cache hit
            "retrieve": "retrieve",  # cache miss
        },
    )

    graph.add_edge("retrieve", "solve")
    graph.add_edge("solve", "quick_verify")
    graph.add_conditional_edges(
        "quick_verify",
        should_retry_after_verify,
        {"enrich": "enrich", "solve": "solve", "caution": "enrich"},
    )
    graph.add_edge("enrich", "store_embedding")           # CHANGED
    graph.add_edge("store_embedding", END)

    return graph.compile()
```

### 6.3 Edge Function

```python
def route_after_cache_check(state: SolveState) -> str:
    if state.get("cache_hit"):
        return "enrich"
    return "retrieve"
```

---

## 7. Updated `retrieve_node`

Replace the current placeholder with real retrieval logic.

```python
# app/graph/nodes/retrieve.py

from sqlalchemy.ext.asyncio import AsyncSession
from app.graph.state import SolveState
from app.services.rag_service import RAGService
from app.database import get_db_session


async def retrieve_node(state: SolveState) -> dict:
    """Vector search for related formulas, similar problems, and user mistakes."""
    query_embedding = state.get("query_embedding")
    if not query_embedding:
        return {"related_formulas": [], "similar_problems": [], "user_mistakes": []}

    async with get_db_session() as db:
        rag = RAGService(db)

        # Run all three retrievals concurrently
        import asyncio
        formulas_task = rag.find_related_formulas(
            query_embedding=query_embedding,
            subject=state.get("detected_subject"),
            grade_level=state.get("grade_level"),
        )
        problems_task = rag.find_similar_problems(
            query_embedding=query_embedding,
            subject=state.get("detected_subject"),
        )
        mistakes_task = rag.find_user_mistakes(
            user_id=state.get("user_id", 0),
            knowledge_points=state.get("knowledge_points", []),
            subject=state.get("detected_subject"),
        )

        formulas, problems, mistakes = await asyncio.gather(
            formulas_task, problems_task, mistakes_task
        )

    return {
        "related_formulas": formulas,
        "similar_problems": problems,
        "user_mistakes": mistakes,
    }
```

---

## 8. New Service: `RAGService`

Create `app/services/rag_service.py` as the central retrieval coordinator.

```python
# app/services/rag_service.py

class RAGService:
    """Coordinates all RAG retrieval: problems, formulas, mistakes."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_similar_problems(
        self, query_embedding, subject=None, limit=5, min_quality=0.7
    ) -> list[dict]:
        """Vector search on scan_records + solutions."""
        ...

    async def find_related_formulas(
        self, query_embedding, subject=None, grade_level=None, limit=5
    ) -> list[dict]:
        """Hybrid vector + keyword search on formulas."""
        ...

    async def find_user_mistakes(
        self, user_id, knowledge_points, subject=None, limit=3
    ) -> list[dict]:
        """Knowledge-point overlap search on mistake_books."""
        ...
```

---

## 9. Updated `solve_node` Context Building

Extend `_build_context` in `app/graph/nodes/solve.py`:

```python
def _build_context(
    formulas: list[dict],
    similar_problems: list[dict],
    user_mistakes: list[dict],    # NEW
) -> str:
    parts = []

    if formulas:
        parts.append("## Related Formulas")
        for f in formulas:
            sim = f.get("similarity", 0)
            parts.append(
                f"- **{f.get('name', '')}**: `{f.get('latex', '')}` "
                f"— {f.get('description', '')} ({sim:.0%} relevant)"
            )

    if similar_problems:
        parts.append("\n## Similar Previously-Solved Problems")
        for i, p in enumerate(similar_problems[:3], 1):
            sim = p.get("similarity", 0)
            parts.append(f"\n### Example {i} ({sim:.0%} match)")
            parts.append(f"**Problem:** {p.get('ocr_text', '')[:300]}")
            parts.append(f"**Answer:** {p.get('final_answer', '')}")

    if user_mistakes:
        parts.append("\n## Student's Weak Areas (personalized)")
        parts.append("This student has struggled with these concepts before:")
        for m in user_mistakes:
            kps = ", ".join(m.get("knowledge_points", []))
            level = m.get("mastery_level", 0)
            parts.append(f"- **{kps}** (mastery: {level}/5)")
            if m.get("notes"):
                parts.append(f"  Student note: \"{m['notes']}\"")
        parts.append("Please explain these concepts extra clearly in your solution.")

    return "\n".join(parts)
```

---

## 10. Database Migrations

### Migration 1: pgvector extension + formula embedding column

```python
# alembic/versions/xxx_add_pgvector_and_formula_embedding.py

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column to formulas
    op.add_column("formulas", sa.Column("embedding", Vector(1536), nullable=True))

    # Create HNSW indexes
    op.execute("""
        CREATE INDEX idx_scan_records_embedding
        ON scan_records USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX idx_formulas_embedding
        ON formulas USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.execute("""
        CREATE INDEX idx_knowledge_base_embedding
        ON knowledge_base USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_knowledge_base_embedding")
    op.execute("DROP INDEX IF EXISTS idx_formulas_embedding")
    op.execute("DROP INDEX IF EXISTS idx_scan_records_embedding")
    op.drop_column("formulas", "embedding")
```

---

## 11. Backfill Script

For existing data that has no embeddings.

```python
# scripts/backfill_embeddings.py

"""
Backfill embeddings for existing scan_records and formulas.

Usage:
    python -m scripts.backfill_embeddings --table scan_records --batch-size 50
    python -m scripts.backfill_embeddings --table formulas --batch-size 50
"""

import asyncio
import argparse
from app.database import async_session_maker
from app.llm.embeddings import embed_texts
from app.models.scan_record import ScanRecord
from app.models.formula import Formula


async def backfill_scan_records(batch_size: int = 50):
    async with async_session_maker() as db:
        # Select records without embeddings
        result = await db.execute(
            select(ScanRecord.id, ScanRecord.ocr_text, ScanRecord.subject, ScanRecord.knowledge_points)
            .where(ScanRecord.embedding.is_(None))
            .where(ScanRecord.ocr_text.isnot(None))
            .limit(batch_size)
        )
        rows = result.all()

        if not rows:
            print("No records to backfill")
            return

        texts = [build_scan_embedding_text(r.ocr_text, r.subject, r.knowledge_points or []) for r in rows]
        embeddings = await embed_texts(texts)

        for row, emb in zip(rows, embeddings):
            await db.execute(
                update(ScanRecord).where(ScanRecord.id == row.id).values(embedding=emb)
            )

        await db.commit()
        print(f"Backfilled {len(rows)} scan records")


async def backfill_formulas(batch_size: int = 50):
    async with async_session_maker() as db:
        result = await db.execute(
            select(Formula.id, Formula.name, Formula.description, Formula.keywords)
            .where(Formula.embedding.is_(None))
            .limit(batch_size)
        )
        rows = result.all()

        if not rows:
            print("No formulas to backfill")
            return

        texts = [build_formula_embedding_text(r.name, r.description or "", r.keywords or []) for r in rows]
        embeddings = await embed_texts(texts)

        for row, emb in zip(rows, embeddings):
            await db.execute(
                update(Formula).where(Formula.id == row.id).values(embedding=emb)
            )

        await db.commit()
        print(f"Backfilled {len(rows)} formulas")
```

---

## 12. Implementation Order

### Phase 1 — Foundation (Week 1)

| Step | File(s) | Description |
|------|---------|-------------|
| 1.1 | Alembic migration | pgvector extension + formula embedding column + HNSW indexes |
| 1.2 | `app/services/rag_service.py` | New service with `find_similar_problems`, `find_related_formulas` |
| 1.3 | `app/services/embedding_service.py` | Add `search_similar()` and `build_*_embedding_text()` methods |
| 1.4 | `app/graph/nodes/retrieve.py` | Replace placeholder with real RAGService calls |
| 1.5 | `app/graph/nodes/solve.py` | Extend `_build_context` to include user_mistakes |
| 1.6 | `scripts/backfill_embeddings.py` | Backfill script for existing records |

### Phase 2 — Cache Layer (Week 2)

| Step | File(s) | Description |
|------|---------|-------------|
| 2.1 | `app/services/cache_service.py` | Redis cache check/store for exact matches |
| 2.2 | `app/graph/nodes/cache_check.py` | New graph node: Redis check → vector check → route |
| 2.3 | `app/graph/nodes/store_embedding.py` | New graph node: async embedding storage |
| 2.4 | `app/graph/solve_graph.py` | Rewire graph with new nodes + conditional edge |
| 2.5 | `app/graph/state.py` | Add `cache_hit`, `query_embedding`, `user_mistakes`, `scan_id` |

### Phase 3 — Personalization (Week 3)

| Step | File(s) | Description |
|------|---------|-------------|
| 3.1 | `app/services/rag_service.py` | Add `find_user_mistakes()` method |
| 3.2 | `app/graph/nodes/retrieve.py` | Wire mistake retrieval into retrieve_node |
| 3.3 | `app/graph/nodes/solve.py` | Update `_build_context` with personalization block |

### Phase 4 — Observability & Tuning (Week 4)

| Step | File(s) | Description |
|------|---------|-------------|
| 4.1 | Logging | Log cache hit rate, retrieval latency, similarity scores |
| 4.2 | Metrics endpoint | `GET /api/v1/admin/rag-stats` — cache hit rate, avg similarity |
| 4.3 | Threshold tuning | A/B test similarity thresholds based on user ratings |
| 4.4 | Formula seed data | Bulk import K12 formulas with embeddings |

---

## 13. File Change Summary

| File | Action | Change |
|------|--------|--------|
| `app/graph/state.py` | EDIT | Add `cache_hit`, `query_embedding`, `user_mistakes`, `scan_id` |
| `app/graph/solve_graph.py` | EDIT | Add `cache_check` + `store_embedding` nodes, rewire edges |
| `app/graph/nodes/retrieve.py` | REWRITE | Replace empty placeholder with RAGService calls |
| `app/graph/nodes/solve.py` | EDIT | Extend `_build_context` for mistakes + richer formatting |
| `app/graph/nodes/cache_check.py` | CREATE | Redis exact-match + vector near-match cache check |
| `app/graph/nodes/store_embedding.py` | CREATE | Async embedding storage after successful solve |
| `app/graph/edges.py` | EDIT | Add `route_after_cache_check` edge function |
| `app/services/rag_service.py` | CREATE | Central RAG coordinator with all three retrieval methods |
| `app/services/cache_service.py` | CREATE | Redis cache get/set/invalidate |
| `app/services/embedding_service.py` | EDIT | Add search methods + text builders |
| `app/models/formula.py` | EDIT | Add `embedding` column (pgvector Vector) |
| `scripts/backfill_embeddings.py` | CREATE | One-time backfill for existing data |
| Alembic migration | CREATE | pgvector extension + embedding column + HNSW indexes |

---

## 14. Testing Strategy

### Unit Tests

```python
# tests/test_rag_service.py

async def test_find_similar_problems_returns_high_quality_only():
    """Only solutions with quality_score >= threshold should be returned."""
    ...

async def test_find_similar_problems_respects_subject_filter():
    """Subject filter should narrow results correctly."""
    ...

async def test_cache_hit_skips_solve():
    """When similarity >= 0.98, graph should route to enrich directly."""
    ...

async def test_cache_miss_proceeds_to_retrieve():
    """When no cache hit, graph should proceed to retrieve → solve."""
    ...

async def test_mistake_retrieval_skipped_for_guest():
    """Guest users (user_id=0) should get empty mistakes list."""
    ...

async def test_formula_hybrid_search_deduplicates():
    """Vector + keyword results should be merged without duplicates."""
    ...
```

### Integration Tests

```python
# tests/test_rag_integration.py

async def test_full_pipeline_with_cache_hit():
    """Submit same problem twice; second should be a cache hit."""
    ...

async def test_full_pipeline_injects_context():
    """Verify that similar problems appear in the solve prompt context."""
    ...
```

---

## 15. Monitoring & Metrics

Track these metrics to validate RAG effectiveness:

| Metric | How to Measure | Target |
|--------|---------------|--------|
| Cache hit rate | `cache_hit=True` / total solves | > 30% after 1 month |
| Avg retrieval latency | Time in `retrieve_node` | < 200ms |
| First-attempt verify pass rate | `verify_passed=True` on attempt 1 | > 85% (up from ~80%) |
| User rating improvement | Avg `solution.rating` with/without RAG context | +0.3 stars |
| Embedding coverage | Records with non-null embedding / total | > 95% |
| API cost per solve | Sum of token costs per solve request | -35% vs baseline |

---

## Appendix A: pgvector Cheat Sheet

```sql
-- Cosine distance (lower = more similar)
SELECT embedding <=> '[0.1, 0.2, ...]'::vector AS distance FROM scan_records;

-- Cosine similarity (higher = more similar) = 1 - distance
SELECT 1 - (embedding <=> '[0.1, 0.2, ...]'::vector) AS similarity FROM scan_records;

-- L2 (Euclidean) distance
SELECT embedding <-> '[0.1, 0.2, ...]'::vector FROM scan_records;

-- Inner product (negate for index ordering)
SELECT embedding <#> '[0.1, 0.2, ...]'::vector FROM scan_records;

-- Set probes for IVFFlat (not needed for HNSW)
SET ivfflat.probes = 10;

-- Check index usage
EXPLAIN ANALYZE SELECT * FROM scan_records ORDER BY embedding <=> $1 LIMIT 5;
```

## Appendix B: Cost Estimation

| Component | Per-Request Cost | Monthly (10K solves) |
|-----------|-----------------|---------------------|
| Embedding generation | $0.00002 (150 tokens avg) | $0.20 |
| pgvector search | ~0 (DB CPU only) | ~0 |
| Redis cache | ~0 | ~0 |
| **Saved LLM calls** (30% cache hit) | -$0.03 per cached call | **-$90.00** |
| **Net savings** | | **~$89.80/month** |
