# LangGraph Backend Refactor — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace LiteLLM with LangGraph multi-step pipeline, add pgvector for RAG, conversation memory, and auto-evaluation.

**Architecture:** LangGraph StateGraph orchestrates 6 nodes (OCR → Analyze → Retrieve → Solve → Evaluate → Enrich) with conditional retry edges. LangChain ChatModel abstracts LLM providers. pgvector enables semantic search on formulas and scan records.

**Tech Stack:** FastAPI, LangGraph 1.0+, LangChain (anthropic/openai/google-genai), PostgreSQL 16 + pgvector, SQLAlchemy 2.0, Redis, Pydantic v2

**Design Doc:** `docs/BACKEND_DESIGN_V3.md`

---

## Phase 1: Infrastructure

### Task 1: Update Docker Compose for pgvector

**Files:**
- Modify: `backend/docker-compose.yml` (line 23 — postgres image)

**Step 1: Change postgres image to pgvector-enabled**

Replace the postgres service image and add healthcheck:

```yaml
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
```

**Step 2: Verify docker image pulls**

Run: `cd backend && docker-compose pull postgres`
Expected: Successfully pulls `pgvector/pgvector:pg16`

**Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "infra: switch postgres to pgvector/pgvector:pg16"
```

---

### Task 2: Update Dependencies

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/requirements-dev.txt`

**Step 1: Replace litellm with langchain/langgraph in requirements.txt**

Full new `requirements.txt`:

```text
# Core Framework
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6

# Database
sqlalchemy>=2.0.25
asyncpg>=0.29.0
alembic>=1.13.1
pgvector>=0.3.0

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# LangGraph + LangChain
langgraph>=1.0.0
langchain-core>=0.3.0
langchain-anthropic>=0.3.0
langchain-openai>=0.3.0
langchain-google-genai>=2.0.0

# Storage
boto3==1.34.14
Pillow>=11.0.0

# Cache
redis>=5.0.1

# Utilities
httpx>=0.26.0
python-dotenv>=1.0.0
pydantic>=2.5.3
pydantic-settings>=2.1.0
email-validator>=2.1.0

# Observability (optional)
langsmith>=0.2.0
```

**Step 2: Add aiosqlite to requirements-dev.txt** (needed for tests with pgvector mock)

Append to `requirements-dev.txt`:

```text
aiosqlite>=0.19.0
```

**Step 3: Install dependencies**

Run: `cd backend && pip install -r requirements.txt -r requirements-dev.txt`
Expected: All packages install successfully, no conflicts

**Step 4: Commit**

```bash
git add requirements.txt requirements-dev.txt
git commit -m "deps: replace litellm with langgraph + langchain, add pgvector"
```

---

### Task 3: Update Configuration

**Files:**
- Modify: `backend/app/config.py` (class Settings, lines 7-52)

**Step 1: Add new settings to Settings class**

Add after existing AI provider settings (after line 36):

```python
    # AI Provider - Default
    default_ai_provider: str = "claude"

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

**Step 2: Verify config loads**

Run: `cd backend && python -c "from app.config import get_settings; s = get_settings(); print(s.embedding_dimension)"`
Expected: `1536`

**Step 3: Commit**

```bash
git add app/config.py
git commit -m "config: add langgraph, embedding, and conversation settings"
```

---

## Phase 2: LLM Abstraction Layer

### Task 4: Create LLM Registry

**Files:**
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/registry.py`
- Test: `backend/tests/test_llm_registry.py`

**Step 1: Write the test**

```python
# tests/test_llm_registry.py
import pytest
from app.llm.registry import get_llm, select_llm, LLM_REGISTRY, MODEL_CONFIG


def test_registry_has_all_providers():
    assert "claude" in LLM_REGISTRY
    assert "openai" in LLM_REGISTRY
    assert "gemini" in LLM_REGISTRY


def test_model_config_has_tiers():
    for provider in LLM_REGISTRY:
        assert "strong" in MODEL_CONFIG[provider]
        assert "fast" in MODEL_CONFIG[provider]


def test_get_llm_returns_chat_model():
    llm = get_llm("fast", "openai")
    assert llm is not None
    assert hasattr(llm, "ainvoke")


def test_select_llm_uses_subject_mapping():
    # Math should default to claude
    llm = select_llm(preferred=None, subject="math", attempt=0)
    assert "claude" in str(type(llm)).lower() or "anthropic" in str(type(llm)).lower()


def test_select_llm_rotates_on_retry():
    llm_0 = select_llm(preferred="claude", subject="math", attempt=0)
    llm_1 = select_llm(preferred="claude", subject="math", attempt=1)
    # Different providers on retry
    assert type(llm_0) != type(llm_1)


def test_select_llm_respects_preferred():
    llm = select_llm(preferred="openai", subject="math", attempt=0)
    assert "openai" in str(type(llm)).lower()
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_llm_registry.py -v`
Expected: FAIL — ModuleNotFoundError: No module named 'app.llm'

**Step 3: Implement app/llm/__init__.py**

```python
from app.llm.registry import get_llm, select_llm, LLM_REGISTRY, MODEL_CONFIG

__all__ = ["get_llm", "select_llm", "LLM_REGISTRY", "MODEL_CONFIG"]
```

**Step 4: Implement app/llm/registry.py**

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel

from app.config import get_settings

LLM_REGISTRY: dict[str, type[BaseChatModel]] = {
    "claude": ChatAnthropic,
    "openai": ChatOpenAI,
    "gemini": ChatGoogleGenerativeAI,
}

MODEL_CONFIG: dict[str, dict[str, str]] = {
    "claude": {
        "strong": "claude-sonnet-4-20250514",
        "fast": "claude-haiku-4-5-20251001",
    },
    "openai": {
        "strong": "gpt-4o",
        "fast": "gpt-4o-mini",
    },
    "gemini": {
        "strong": "gemini-2.0-flash",
        "fast": "gemini-2.0-flash-lite",
    },
}

SUBJECT_PROVIDER_MAP: dict[str, str] = {
    "math": "claude",
    "physics": "claude",
    "chemistry": "openai",
    "biology": "openai",
    "english": "openai",
    "chinese": "claude",
}


def _get_api_key_kwargs(provider: str) -> dict:
    """Return the API key kwargs for the given provider."""
    settings = get_settings()
    if provider == "claude":
        key = settings.anthropic_api_key
        return {"api_key": key} if key else {}
    elif provider == "openai":
        key = settings.openai_api_key
        return {"api_key": key} if key else {}
    elif provider == "gemini":
        key = settings.google_api_key
        return {"google_api_key": key} if key else {}
    return {}


def get_llm(tier: str = "strong", provider: str | None = None) -> BaseChatModel:
    """Get a ChatModel instance by tier and provider."""
    settings = get_settings()
    provider = provider or settings.default_ai_provider
    if provider not in LLM_REGISTRY:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(LLM_REGISTRY.keys())}")
    if tier not in MODEL_CONFIG.get(provider, {}):
        raise ValueError(f"Unknown tier: {tier}. Available: strong, fast")

    cls = LLM_REGISTRY[provider]
    model = MODEL_CONFIG[provider][tier]
    kwargs = _get_api_key_kwargs(provider)
    return cls(model=model, temperature=0.1, **kwargs)


def select_llm(
    preferred: str | None,
    subject: str,
    attempt: int = 0,
) -> BaseChatModel:
    """Select LLM based on preference, subject, and retry rotation."""
    providers = list(LLM_REGISTRY.keys())

    if attempt == 0:
        provider = preferred or SUBJECT_PROVIDER_MAP.get(subject, "claude")
    else:
        base = preferred or SUBJECT_PROVIDER_MAP.get(subject, "claude")
        idx = providers.index(base) if base in providers else 0
        provider = providers[(idx + attempt) % len(providers)]

    return get_llm("strong", provider)
```

**Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_llm_registry.py -v`
Expected: All 6 tests PASS

**Step 6: Commit**

```bash
git add app/llm/ tests/test_llm_registry.py
git commit -m "feat: add LLM registry with langchain provider abstraction"
```

---

### Task 5: Create Embedding Service

**Files:**
- Create: `backend/app/llm/embeddings.py`
- Test: `backend/tests/test_embeddings.py`

**Step 1: Write the test**

```python
# tests/test_embeddings.py
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_embed_text_returns_vector():
    mock_vector = [0.1] * 1536
    with patch("app.llm.embeddings._embeddings") as mock_embeddings:
        mock_embeddings.aembed_query = AsyncMock(return_value=mock_vector)
        from app.llm.embeddings import embed_text
        result = await embed_text("solve 2x + 5 = 15")
        assert len(result) == 1536
        assert result == mock_vector
        mock_embeddings.aembed_query.assert_called_once_with("solve 2x + 5 = 15")


@pytest.mark.asyncio
async def test_embed_texts_batch():
    mock_vectors = [[0.1] * 1536, [0.2] * 1536]
    with patch("app.llm.embeddings._embeddings") as mock_embeddings:
        mock_embeddings.aembed_documents = AsyncMock(return_value=mock_vectors)
        from app.llm.embeddings import embed_texts
        result = await embed_texts(["text1", "text2"])
        assert len(result) == 2
        assert len(result[0]) == 1536
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_embeddings.py -v`
Expected: FAIL

**Step 3: Implement app/llm/embeddings.py**

```python
from langchain_openai import OpenAIEmbeddings
from app.config import get_settings

settings = get_settings()

_embeddings = OpenAIEmbeddings(
    model=settings.embedding_model,
    api_key=settings.openai_api_key or "dummy",
)


async def embed_text(text: str) -> list[float]:
    """Generate embedding vector for a single text."""
    return await _embeddings.aembed_query(text)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for multiple texts."""
    return await _embeddings.aembed_documents(texts)
```

**Step 4: Run tests**

Run: `cd backend && python -m pytest tests/test_embeddings.py -v`
Expected: PASS

**Step 5: Update app/llm/__init__.py**

Add:
```python
from app.llm.embeddings import embed_text, embed_texts
```

**Step 6: Commit**

```bash
git add app/llm/ tests/test_embeddings.py
git commit -m "feat: add embedding service using langchain OpenAIEmbeddings"
```

---

### Task 6: Create Prompt Templates

**Files:**
- Create: `backend/app/llm/prompts/__init__.py`
- Create: `backend/app/llm/prompts/analysis.py`
- Create: `backend/app/llm/prompts/solve.py`
- Create: `backend/app/llm/prompts/evaluate.py`
- Create: `backend/app/llm/prompts/followup.py`

**Step 1: Create app/llm/prompts/__init__.py**

```python
from app.llm.prompts.analysis import ANALYSIS_SYSTEM_PROMPT, build_analysis_messages
from app.llm.prompts.solve import SOLVE_SYSTEM_PROMPT, build_solve_messages
from app.llm.prompts.evaluate import EVALUATE_SYSTEM_PROMPT, build_evaluate_messages
from app.llm.prompts.followup import FOLLOWUP_SYSTEM_PROMPT, build_followup_messages

__all__ = [
    "ANALYSIS_SYSTEM_PROMPT", "build_analysis_messages",
    "SOLVE_SYSTEM_PROMPT", "build_solve_messages",
    "EVALUATE_SYSTEM_PROMPT", "build_evaluate_messages",
    "FOLLOWUP_SYSTEM_PROMPT", "build_followup_messages",
]
```

**Step 2: Create app/llm/prompts/analysis.py**

```python
from langchain_core.messages import SystemMessage, HumanMessage

ANALYSIS_SYSTEM_PROMPT = """You are an expert education AI that classifies student homework problems.
Analyze the given problem text and identify:
1. Subject (math, physics, chemistry, biology, english, chinese)
2. Problem type (equation, geometry, word_problem, proof, multiple_choice, fill_in_blank)
3. Difficulty (easy, medium, hard)
4. Key knowledge points

Respond ONLY in JSON:
{
  "subject": "math",
  "problem_type": "equation",
  "difficulty": "medium",
  "knowledge_points": ["algebra", "linear_equations"]
}"""


def build_analysis_messages(
    ocr_text: str,
    grade_level: str = "unknown",
) -> list:
    return [
        SystemMessage(content=ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(content=f"Grade Level: {grade_level}\n\nProblem:\n{ocr_text}"),
    ]
```

**Step 3: Create app/llm/prompts/solve.py**

```python
from langchain_core.messages import SystemMessage, HumanMessage

SOLVE_SYSTEM_PROMPT = """You are an experienced {subject} teacher helping a {grade_level} student.
Your goal is to provide clear, educational explanations that help the student understand the solution process.

IMPORTANT: Respond ONLY in valid JSON format."""


def build_solve_messages(
    ocr_text: str,
    subject: str = "math",
    grade_level: str = "middle school",
    context: str = "",
) -> list:
    system = SOLVE_SYSTEM_PROMPT.format(subject=subject, grade_level=grade_level)
    user_content = f"""Please solve the following problem step by step.

Requirements:
1. Identify the problem type and key concepts
2. List all formulas needed (in LaTeX format)
3. Show detailed solution steps with explanations
4. Provide the final answer
5. Give tips for solving similar problems
"""
    if context:
        user_content += f"""
## Reference Context
{context}
"""
    user_content += f"""
## Problem
{ocr_text}

Respond in JSON format:
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

    return [
        SystemMessage(content=system),
        HumanMessage(content=user_content),
    ]
```

**Step 4: Create app/llm/prompts/evaluate.py**

```python
from langchain_core.messages import SystemMessage, HumanMessage

EVALUATE_SYSTEM_PROMPT = """You are a senior teacher reviewing a student solution for correctness and quality.
Score each criterion from 0.0 to 1.0. Be strict on correctness.

Respond ONLY in JSON:
{
  "scores": {
    "correctness": 0.9,
    "completeness": 0.8,
    "clarity": 0.85,
    "format": 0.9,
    "relevance": 0.8
  },
  "overall": 0.85,
  "issues": ["list of specific issues found"],
  "pass": true
}"""


def build_evaluate_messages(
    problem_text: str,
    solution: str,
    subject: str = "math",
    grade_level: str = "middle school",
) -> list:
    return [
        SystemMessage(content=EVALUATE_SYSTEM_PROMPT),
        HumanMessage(content=f"""Subject: {subject}
Grade Level: {grade_level}

Problem:
{problem_text}

Solution to Review:
{solution}"""),
    ]
```

**Step 5: Create app/llm/prompts/followup.py**

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

FOLLOWUP_SYSTEM_PROMPT = """You are a patient {subject} teacher having a conversation with a {grade_level} student.
You previously helped them solve a problem. Now they have a follow-up question.
Be encouraging, clear, and educational. Use LaTeX for any formulas.
Keep responses focused and concise."""


def build_followup_messages(
    conversation_history: list[dict],
    user_message: str,
    subject: str = "math",
    grade_level: str = "middle school",
) -> list:
    messages = [
        SystemMessage(content=FOLLOWUP_SYSTEM_PROMPT.format(
            subject=subject, grade_level=grade_level
        )),
    ]
    for msg in conversation_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))
    return messages
```

**Step 6: Commit**

```bash
git add app/llm/prompts/
git commit -m "feat: add prompt templates for analysis, solve, evaluate, followup"
```

---

## Phase 3: Database Changes

### Task 7: Create New ORM Models

**Files:**
- Create: `backend/app/models/conversation_message.py`
- Create: `backend/app/models/evaluation_log.py`
- Create: `backend/app/models/knowledge_base.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Create conversation_message.py**

```python
from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("scan_records.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # system, user, assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    scan_record = relationship("ScanRecord", backref="conversation_messages")
```

**Step 2: Create evaluation_log.py**

```python
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class EvaluationLog(Base):
    __tablename__ = "evaluation_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    solution_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("solutions.id", ondelete="CASCADE"), index=True)
    evaluator_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluator_model: Mapped[str] = mapped_column(String(100), nullable=False)
    scores: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    issues: Mapped[list] = mapped_column(JSONB, default=list)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    solution = relationship("Solution", backref="evaluation_logs")
```

**Step 3: Create knowledge_base.py**

```python
from datetime import datetime
from sqlalchemy import BigInteger, String, Text, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.database import Base
from app.config import get_settings


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    subject: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100))
    grade_levels: Mapped[list | None] = mapped_column(ARRAY(String))
    source: Mapped[str | None] = mapped_column(String(255))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default=dict)
    embedding = mapped_column(Vector(1536))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

**Step 4: Enhance existing models — add vector columns**

Modify `app/models/scan_record.py` — add after existing columns:

```python
# Add imports at top
from pgvector.sqlalchemy import Vector
from sqlalchemy import Float
from sqlalchemy.dialects.postgresql import JSONB

# Add columns to ScanRecord class (after difficulty):
    ocr_confidence: Mapped[float | None] = mapped_column(Float)
    problem_type: Mapped[str | None] = mapped_column(String(50))
    knowledge_points: Mapped[list | None] = mapped_column(JSONB, default=list)
    embedding = mapped_column(Vector(1536), nullable=True)
```

Modify `app/models/solution.py` — add columns:

```python
# Add import
from sqlalchemy import Float, Text as SAText

# Add columns (after related_formula_ids):
    final_answer: Mapped[str | None] = mapped_column(Text)
    knowledge_points: Mapped[list | None] = mapped_column(JSONB, default=list)
    quality_score: Mapped[float | None] = mapped_column(Float)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
```

Modify `app/models/formula.py` — add embedding column:

```python
# Add import
from pgvector.sqlalchemy import Vector

# Add column (after related_ids):
    embedding = mapped_column(Vector(1536), nullable=True)
```

Modify `app/models/mistake_book.py` — add columns:

```python
# Add imports
from sqlalchemy import SmallInteger, String
from sqlalchemy.dialects.postgresql import JSONB

# Add columns (after scan_id):
    subject: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[list | None] = mapped_column(JSONB, default=list)

# Add column (after mastered):
    mastery_level: Mapped[int] = mapped_column(SmallInteger, default=0)
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
```

Modify `app/models/learning_stats.py` — add columns:

```python
# Add import
from sqlalchemy import Float

# Add columns (after study_minutes):
    avg_quality_score: Mapped[float] = mapped_column(Float, default=0)
    mastered_count: Mapped[int] = mapped_column(Integer, default=0)
```

**Step 5: Update app/models/__init__.py**

```python
from app.models.user import User
from app.models.scan_record import ScanRecord
from app.models.solution import Solution
from app.models.formula import Formula
from app.models.mistake_book import MistakeBook
from app.models.learning_stats import LearningStats
from app.models.conversation_message import ConversationMessage
from app.models.evaluation_log import EvaluationLog
from app.models.knowledge_base import KnowledgeBase

__all__ = [
    "User", "ScanRecord", "Solution", "Formula",
    "MistakeBook", "LearningStats",
    "ConversationMessage", "EvaluationLog", "KnowledgeBase",
]
```

**Step 6: Commit**

```bash
git add app/models/
git commit -m "feat: add new models (conversation, evaluation, knowledge_base) + enhance existing with pgvector"
```

---

### Task 8: Create Alembic Migration

**Files:**
- Create: `backend/alembic/versions/003_langgraph_refactor.py` (auto-generated)

**Step 1: Generate migration**

Run: `cd backend && alembic revision --autogenerate -m "langgraph refactor: pgvector, new tables, enhanced columns"`

Note: You may need to manually adjust the generated migration to add:

```python
from alembic import op

def upgrade():
    # Enable pgvector extension first
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ... auto-generated table creates and column additions ...
```

**Step 2: Review the generated migration**

Read the generated file and verify it includes:
- `CREATE EXTENSION IF NOT EXISTS vector`
- New tables: `conversation_messages`, `evaluation_logs`, `knowledge_base`
- New columns on: `scan_records`, `solutions`, `formulas`, `mistake_books`, `learning_stats`
- IVFFlat indexes on vector columns

**Step 3: If indexes are missing, add manually**

```python
    # Add vector indexes (IVFFlat requires data, so create with ivfflat after data exists)
    # For now, create HNSW indexes which work on empty tables
    op.create_index(
        "idx_scan_records_embedding",
        "scan_records",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "idx_formulas_embedding",
        "formulas",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    op.create_index(
        "idx_knowledge_base_embedding",
        "knowledge_base",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
```

**Step 4: Test migration (requires running postgres)**

Run: `cd backend && docker-compose up -d postgres && sleep 3 && alembic upgrade head`
Expected: Migration applies successfully

**Step 5: Verify tables exist**

Run: `cd backend && docker-compose exec postgres psql -U postgres -d eduscan -c "\dt"`
Expected: All tables listed including new ones

**Step 6: Commit**

```bash
git add alembic/
git commit -m "migration: add pgvector extension, new tables, enhanced columns"
```

---

## Phase 4: LangGraph Pipeline

### Task 9: Create Graph State Definitions

**Files:**
- Create: `backend/app/graph/__init__.py`
- Create: `backend/app/graph/state.py`

**Step 1: Create app/graph/__init__.py**

```python
from app.graph.solve_graph import solve_graph
from app.graph.followup_graph import followup_graph

__all__ = ["solve_graph", "followup_graph"]
```

Note: This will import from files we create in later tasks. Create it empty for now:

```python
# Imports added after graph implementations are complete
```

**Step 2: Create app/graph/state.py**

```python
from typing import TypedDict, Optional


class SolveState(TypedDict, total=False):
    """State for the main problem-solving graph."""
    # --- Input ---
    image_bytes: Optional[bytes]
    image_url: str
    user_id: int
    subject: Optional[str]
    grade_level: Optional[str]
    preferred_provider: Optional[str]

    # --- OCR ---
    ocr_text: str
    ocr_confidence: float

    # --- Analysis ---
    detected_subject: str
    problem_type: str
    difficulty: str
    knowledge_points: list[str]

    # --- Retrieval (RAG) ---
    related_formulas: list[dict]
    similar_problems: list[dict]

    # --- Solution ---
    solution_raw: str
    solution_parsed: dict
    llm_provider: str
    llm_model: str
    prompt_tokens: int
    completion_tokens: int

    # --- Evaluation ---
    quality_score: float
    quality_issues: list[str]
    attempt_count: int

    # --- Enrichment ---
    final_solution: dict
    related_formula_ids: list[int]

    # --- Errors ---
    error: Optional[str]


class FollowUpState(TypedDict, total=False):
    """State for follow-up conversation graph."""
    scan_id: int
    user_message: str
    conversation_history: list[dict]
    solution_context: dict
    subject: str
    grade_level: str
    reply: str
    provider: str
    model: str
    tokens_used: int
```

**Step 3: Commit**

```bash
git add app/graph/
git commit -m "feat: add LangGraph state definitions (SolveState, FollowUpState)"
```

---

### Task 10: Create Graph Nodes

**Files:**
- Create: `backend/app/graph/nodes/__init__.py`
- Create: `backend/app/graph/nodes/ocr.py`
- Create: `backend/app/graph/nodes/analyze.py`
- Create: `backend/app/graph/nodes/retrieve.py`
- Create: `backend/app/graph/nodes/solve.py`
- Create: `backend/app/graph/nodes/evaluate.py`
- Create: `backend/app/graph/nodes/enrich.py`
- Test: `backend/tests/test_graph_nodes.py`

**Step 1: Write the test**

```python
# tests/test_graph_nodes.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_ocr_node():
    from app.graph.nodes.ocr import ocr_node
    state = {"image_bytes": b"fake_image_data"}
    with patch("app.graph.nodes.ocr.ocr_service") as mock_ocr:
        mock_ocr.extract_text = AsyncMock(return_value="2x + 5 = 15")
        result = await ocr_node(state)
        assert result["ocr_text"] == "2x + 5 = 15"
        assert "ocr_confidence" in result


@pytest.mark.asyncio
async def test_analyze_node():
    from app.graph.nodes.analyze import analyze_node
    state = {
        "ocr_text": "Solve 2x + 5 = 15",
        "grade_level": "middle school",
        "subject": None,
    }
    mock_response = MagicMock()
    mock_response.content = '{"subject": "math", "problem_type": "equation", "difficulty": "easy", "knowledge_points": ["algebra"]}'

    with patch("app.graph.nodes.analyze.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        result = await analyze_node(state)
        assert result["detected_subject"] == "math"
        assert result["problem_type"] == "equation"


@pytest.mark.asyncio
async def test_analyze_node_preserves_user_subject():
    from app.graph.nodes.analyze import analyze_node
    state = {
        "ocr_text": "Solve 2x + 5 = 15",
        "grade_level": "middle school",
        "subject": "physics",  # user explicitly set
    }
    mock_response = MagicMock()
    mock_response.content = '{"subject": "math", "problem_type": "equation", "difficulty": "easy", "knowledge_points": ["algebra"]}'

    with patch("app.graph.nodes.analyze.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        result = await analyze_node(state)
        assert result["detected_subject"] == "physics"  # preserved


@pytest.mark.asyncio
async def test_solve_node():
    from app.graph.nodes.solve import solve_node
    state = {
        "ocr_text": "2x + 5 = 15",
        "detected_subject": "math",
        "grade_level": "middle school",
        "preferred_provider": "claude",
        "attempt_count": 0,
        "related_formulas": [],
        "similar_problems": [],
    }
    mock_response = MagicMock()
    mock_response.content = '{"question_type": "equation", "knowledge_points": ["algebra"], "steps": [{"step": 1, "description": "subtract 5", "formula": "", "calculation": "2x = 10"}], "final_answer": "x = 5", "explanation": "test", "tips": "test"}'
    mock_response.usage_metadata = {"input_tokens": 100, "output_tokens": 50}

    with patch("app.graph.nodes.solve.select_llm") as mock_select:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_select.return_value = mock_llm
        # Add provider/model attributes
        mock_llm._llm_type = "anthropic"
        result = await solve_node(state)
        assert "solution_parsed" in result
        assert result["solution_parsed"]["final_answer"] == "x = 5"


@pytest.mark.asyncio
async def test_evaluate_node():
    from app.graph.nodes.evaluate import evaluate_node
    state = {
        "ocr_text": "2x + 5 = 15",
        "solution_raw": '{"steps": [...], "final_answer": "x = 5"}',
        "detected_subject": "math",
        "grade_level": "middle school",
        "attempt_count": 0,
    }
    mock_response = MagicMock()
    mock_response.content = '{"scores": {"correctness": 0.9}, "overall": 0.9, "issues": [], "pass": true}'

    with patch("app.graph.nodes.evaluate.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm
        result = await evaluate_node(state)
        assert result["quality_score"] == 0.9
        assert result["attempt_count"] == 1


@pytest.mark.asyncio
async def test_enrich_node():
    from app.graph.nodes.enrich import enrich_node
    state = {
        "solution_parsed": {"question_type": "equation", "steps": [], "final_answer": "x = 5"},
        "related_formulas": [{"id": 1, "name": "Linear Equation"}],
        "difficulty": "easy",
        "quality_score": 0.9,
    }
    result = await enrich_node(state)
    assert result["final_solution"]["related_formulas"] == [{"id": 1, "name": "Linear Equation"}]
    assert result["related_formula_ids"] == [1]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_graph_nodes.py -v`
Expected: FAIL

**Step 3: Create app/graph/nodes/__init__.py**

```python
from app.graph.nodes.ocr import ocr_node
from app.graph.nodes.analyze import analyze_node
from app.graph.nodes.retrieve import retrieve_node
from app.graph.nodes.solve import solve_node
from app.graph.nodes.evaluate import evaluate_node
from app.graph.nodes.enrich import enrich_node

__all__ = [
    "ocr_node", "analyze_node", "retrieve_node",
    "solve_node", "evaluate_node", "enrich_node",
]
```

**Step 4: Create app/graph/nodes/ocr.py**

```python
from app.graph.state import SolveState
from app.services.ocr_service import OCRService

ocr_service = OCRService()


async def ocr_node(state: SolveState) -> dict:
    """Extract text from image using OCR provider."""
    image_bytes = state.get("image_bytes")
    if not image_bytes:
        return {"ocr_text": "", "ocr_confidence": 0.0, "error": "No image data provided"}

    try:
        text = await ocr_service.extract_text(image_bytes)
        return {"ocr_text": text, "ocr_confidence": 1.0}
    except Exception as e:
        return {"ocr_text": "", "ocr_confidence": 0.0, "error": str(e)}
```

**Step 5: Create app/graph/nodes/analyze.py**

```python
import json
from app.graph.state import SolveState
from app.llm.registry import get_llm
from app.llm.prompts.analysis import build_analysis_messages

# Fallback keyword-based detection
SUBJECT_KEYWORDS = {
    "math": ["x", "y", "solve", "equation", "angle", "triangle", "calculate", "sum", "product"],
    "physics": ["force", "mass", "acceleration", "velocity", "energy", "momentum", "wave"],
    "chemistry": ["atom", "molecule", "reaction", "acid", "base", "element", "compound"],
}


def _detect_subject_fallback(text: str) -> str:
    text_lower = text.lower()
    scores = {}
    for subject, keywords in SUBJECT_KEYWORDS.items():
        scores[subject] = sum(1 for kw in keywords if kw in text_lower)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "math"


async def analyze_node(state: SolveState) -> dict:
    """Classify the problem: subject, type, difficulty, knowledge points."""
    ocr_text = state.get("ocr_text", "")
    grade_level = state.get("grade_level", "unknown")

    try:
        llm = get_llm("fast")
        messages = build_analysis_messages(ocr_text, grade_level)
        result = await llm.ainvoke(messages)
        parsed = json.loads(result.content)

        detected_subject = state.get("subject") or parsed.get("subject", "math")
        return {
            "detected_subject": detected_subject,
            "problem_type": parsed.get("problem_type", "unknown"),
            "difficulty": parsed.get("difficulty", "medium"),
            "knowledge_points": parsed.get("knowledge_points", []),
        }
    except Exception:
        # Fallback to keyword detection
        detected_subject = state.get("subject") or _detect_subject_fallback(ocr_text)
        return {
            "detected_subject": detected_subject,
            "problem_type": "unknown",
            "difficulty": "medium",
            "knowledge_points": [],
        }
```

**Step 6: Create app/graph/nodes/retrieve.py**

```python
from app.graph.state import SolveState
from app.llm.embeddings import embed_text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def retrieve_node(state: SolveState) -> dict:
    """Vector search for related formulas and similar past problems.

    Note: This node requires a database session injected via the graph config.
    If no DB session is available (e.g., during testing), returns empty results.
    """
    # For now, return empty results. Will be wired up when repositories are created.
    # The full implementation uses pgvector cosine distance search.
    return {
        "related_formulas": [],
        "similar_problems": [],
    }
```

**Step 7: Create app/graph/nodes/solve.py**

```python
import json
from app.graph.state import SolveState
from app.llm.registry import select_llm
from app.llm.prompts.solve import build_solve_messages


def _build_context(formulas: list[dict], similar_problems: list[dict]) -> str:
    """Build context string from retrieved formulas and similar problems."""
    parts = []
    if formulas:
        parts.append("## Related Formulas")
        for f in formulas:
            parts.append(f"- **{f.get('name', '')}**: `{f.get('latex', '')}` — {f.get('description', '')}")

    if similar_problems:
        parts.append("\n## Similar Problems (for reference)")
        for p in similar_problems:
            parts.append(f"- {p.get('ocr_text', '')[:200]}")

    return "\n".join(parts)


async def solve_node(state: SolveState) -> dict:
    """Generate step-by-step solution using the selected LLM."""
    llm = select_llm(
        preferred=state.get("preferred_provider"),
        subject=state.get("detected_subject", "math"),
        attempt=state.get("attempt_count", 0),
    )

    context = _build_context(
        state.get("related_formulas", []),
        state.get("similar_problems", []),
    )

    messages = build_solve_messages(
        ocr_text=state.get("ocr_text", ""),
        subject=state.get("detected_subject", "math"),
        grade_level=state.get("grade_level", "middle school"),
        context=context,
    )

    try:
        result = await llm.ainvoke(messages)
        usage = result.usage_metadata or {}

        # Parse JSON response
        try:
            parsed = json.loads(result.content)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            content = result.content
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(content[start:end])
            else:
                parsed = {
                    "question_type": "unknown",
                    "knowledge_points": [],
                    "steps": [],
                    "final_answer": content,
                    "explanation": "",
                    "tips": "",
                }

        provider = getattr(llm, "_llm_type", "unknown")
        model = getattr(llm, "model_name", getattr(llm, "model", "unknown"))

        return {
            "solution_raw": result.content,
            "solution_parsed": parsed,
            "llm_provider": provider,
            "llm_model": str(model),
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
        }
    except Exception as e:
        return {"error": f"Solve failed: {str(e)}"}
```

**Step 8: Create app/graph/nodes/evaluate.py**

```python
import json
from app.graph.state import SolveState
from app.llm.registry import get_llm
from app.llm.prompts.evaluate import build_evaluate_messages


async def evaluate_node(state: SolveState) -> dict:
    """Auto-grade the solution quality."""
    attempt_count = state.get("attempt_count", 0)

    try:
        # Use a different provider than the solver for cross-check
        llm = get_llm("fast")
        messages = build_evaluate_messages(
            problem_text=state.get("ocr_text", ""),
            solution=state.get("solution_raw", ""),
            subject=state.get("detected_subject", "math"),
            grade_level=state.get("grade_level", "middle school"),
        )
        result = await llm.ainvoke(messages)
        parsed = json.loads(result.content)

        return {
            "quality_score": parsed.get("overall", 0.5),
            "quality_issues": parsed.get("issues", []),
            "attempt_count": attempt_count + 1,
        }
    except Exception:
        # If evaluation fails, assume acceptable quality
        return {
            "quality_score": 0.75,
            "quality_issues": ["evaluation_failed"],
            "attempt_count": attempt_count + 1,
        }
```

**Step 9: Create app/graph/nodes/enrich.py**

```python
from app.graph.state import SolveState


async def enrich_node(state: SolveState) -> dict:
    """Attach formula references, tips, and metadata to the solution."""
    solution = dict(state.get("solution_parsed", {}))
    solution["related_formulas"] = state.get("related_formulas", [])
    solution["difficulty"] = state.get("difficulty", "medium")
    solution["quality_score"] = state.get("quality_score", 0)

    formula_ids = [f["id"] for f in state.get("related_formulas", []) if "id" in f]

    return {
        "final_solution": solution,
        "related_formula_ids": formula_ids,
    }
```

**Step 10: Run tests**

Run: `cd backend && python -m pytest tests/test_graph_nodes.py -v`
Expected: All tests PASS

**Step 11: Commit**

```bash
git add app/graph/nodes/ tests/test_graph_nodes.py
git commit -m "feat: add LangGraph nodes (ocr, analyze, retrieve, solve, evaluate, enrich)"
```

---

### Task 11: Create Graph Edges and Compile Graphs

**Files:**
- Create: `backend/app/graph/edges.py`
- Create: `backend/app/graph/solve_graph.py`
- Create: `backend/app/graph/followup_graph.py`
- Update: `backend/app/graph/__init__.py`
- Test: `backend/tests/test_solve_graph.py`

**Step 1: Write the test**

```python
# tests/test_solve_graph.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.graph.edges import should_retry


def test_should_retry_passes_when_quality_high():
    state = {"quality_score": 0.85, "attempt_count": 1}
    assert should_retry(state) == "enrich"


def test_should_retry_retries_when_quality_low():
    state = {"quality_score": 0.5, "attempt_count": 1}
    assert should_retry(state) == "retry"


def test_should_retry_fallbacks_after_max_attempts():
    state = {"quality_score": 0.3, "attempt_count": 3}
    assert should_retry(state) == "fallback"


def test_solve_graph_compiles():
    from app.graph.solve_graph import build_solve_graph
    graph = build_solve_graph()
    assert graph is not None
    # Graph should have the expected nodes
    assert hasattr(graph, "ainvoke")


def test_followup_graph_compiles():
    from app.graph.followup_graph import build_followup_graph
    graph = build_followup_graph()
    assert graph is not None
    assert hasattr(graph, "ainvoke")
```

**Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_solve_graph.py -v`
Expected: FAIL

**Step 3: Create app/graph/edges.py**

```python
from typing import Literal
from app.graph.state import SolveState
from app.config import get_settings


def should_retry(state: SolveState) -> Literal["retry", "enrich", "fallback"]:
    """Decide whether to retry, fallback, or accept the solution."""
    settings = get_settings()
    score = state.get("quality_score", 0)
    attempts = state.get("attempt_count", 0)
    min_score = settings.min_quality_score
    max_attempts = settings.max_solve_attempts

    if score >= min_score:
        return "enrich"
    elif attempts < max_attempts:
        return "retry"
    else:
        return "fallback"
```

**Step 4: Create app/graph/solve_graph.py**

```python
from langgraph.graph import StateGraph, START, END
from app.graph.state import SolveState
from app.graph.nodes import (
    ocr_node, analyze_node, retrieve_node,
    solve_node, evaluate_node, enrich_node,
)
from app.graph.edges import should_retry


def build_solve_graph():
    """Build and compile the main problem-solving graph."""
    graph = StateGraph(SolveState)

    # Add nodes
    graph.add_node("ocr", ocr_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("solve", solve_node)
    graph.add_node("evaluate", evaluate_node)
    graph.add_node("enrich", enrich_node)

    # Linear flow: START → ocr → analyze → retrieve → solve → evaluate
    graph.add_edge(START, "ocr")
    graph.add_edge("ocr", "analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_edge("retrieve", "solve")
    graph.add_edge("solve", "evaluate")

    # Conditional: evaluate → enrich (pass) or solve (retry) or enrich (fallback)
    graph.add_conditional_edges(
        "evaluate",
        should_retry,
        {
            "enrich": "enrich",
            "retry": "solve",
            "fallback": "enrich",
        },
    )

    graph.add_edge("enrich", END)

    return graph.compile()


# Compiled singleton (import this)
solve_graph = build_solve_graph()
```

**Step 5: Create app/graph/followup_graph.py**

```python
from langgraph.graph import StateGraph, START, END
from app.graph.state import FollowUpState
from app.llm.registry import get_llm
from app.llm.prompts.followup import build_followup_messages


async def build_context_node(state: FollowUpState) -> dict:
    """Build conversation context from history."""
    history = state.get("conversation_history", [])
    return {"conversation_history": history}


async def generate_reply_node(state: FollowUpState) -> dict:
    """Generate reply to follow-up question."""
    llm = get_llm("strong")
    messages = build_followup_messages(
        conversation_history=state.get("conversation_history", []),
        user_message=state.get("user_message", ""),
        subject=state.get("subject", "math"),
        grade_level=state.get("grade_level", "middle school"),
    )
    result = await llm.ainvoke(messages)
    usage = result.usage_metadata or {}
    return {
        "reply": result.content,
        "tokens_used": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
    }


def build_followup_graph():
    """Build and compile the follow-up conversation graph."""
    graph = StateGraph(FollowUpState)

    graph.add_node("build_context", build_context_node)
    graph.add_node("generate_reply", generate_reply_node)

    graph.add_edge(START, "build_context")
    graph.add_edge("build_context", "generate_reply")
    graph.add_edge("generate_reply", END)

    return graph.compile()


# Compiled singleton
followup_graph = build_followup_graph()
```

**Step 6: Update app/graph/__init__.py**

```python
from app.graph.solve_graph import solve_graph, build_solve_graph
from app.graph.followup_graph import followup_graph, build_followup_graph

__all__ = ["solve_graph", "followup_graph", "build_solve_graph", "build_followup_graph"]
```

**Step 7: Run tests**

Run: `cd backend && python -m pytest tests/test_solve_graph.py -v`
Expected: All tests PASS

**Step 8: Commit**

```bash
git add app/graph/ tests/test_solve_graph.py
git commit -m "feat: compile LangGraph solve + followup graphs with conditional retry edges"
```

---

## Phase 5: Services + API

### Task 12: Create Conversation Service

**Files:**
- Create: `backend/app/services/conversation_service.py`
- Test: `backend/tests/test_conversation_service.py`

**Step 1: Write the test**

```python
# tests/test_conversation_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_add_message():
    mock_db = AsyncMock()
    service = ConversationService(mock_db)
    await service.add_message(scan_id=1, role="user", content="explain step 3")
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_history_returns_list():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    service = ConversationService(mock_db)
    result = await service.get_history(scan_id=1)
    assert isinstance(result, list)
```

**Step 2: Implement app/services/conversation_service.py**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.conversation_message import ConversationMessage


class ConversationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(
        self, scan_id: int, role: str, content: str, metadata: dict | None = None
    ) -> ConversationMessage:
        msg = ConversationMessage(
            scan_id=scan_id,
            role=role,
            content=content,
            metadata_=metadata or {},
        )
        self.db.add(msg)
        await self.db.flush()
        return msg

    async def get_history(self, scan_id: int) -> list[dict]:
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.scan_id == scan_id)
            .order_by(ConversationMessage.created_at.asc())
        )
        messages = result.scalars().all()
        return [
            {"role": msg.role, "content": msg.content, "created_at": str(msg.created_at)}
            for msg in messages
        ]

    async def get_message_count(self, scan_id: int) -> int:
        result = await self.db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.scan_id == scan_id)
        )
        return len(result.scalars().all())
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_conversation_service.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add app/services/conversation_service.py tests/test_conversation_service.py
git commit -m "feat: add conversation service for follow-up message management"
```

---

### Task 13: Create Embedding Service

**Files:**
- Create: `backend/app/services/embedding_service.py`

**Step 1: Implement app/services/embedding_service.py**

```python
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.llm.embeddings import embed_text
from app.models.scan_record import ScanRecord
from app.models.formula import Formula


class EmbeddingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def embed_scan_record(self, scan_id: int, text: str) -> None:
        """Generate and store embedding for a scan record."""
        try:
            vector = await embed_text(text)
            await self.db.execute(
                update(ScanRecord)
                .where(ScanRecord.id == scan_id)
                .values(embedding=vector)
            )
            await self.db.flush()
        except Exception:
            pass  # Non-critical: embedding failure shouldn't block solving

    async def embed_formula(self, formula_id: int, text: str) -> None:
        """Generate and store embedding for a formula."""
        try:
            vector = await embed_text(text)
            await self.db.execute(
                update(Formula)
                .where(Formula.id == formula_id)
                .values(embedding=vector)
            )
            await self.db.flush()
        except Exception:
            pass
```

**Step 2: Commit**

```bash
git add app/services/embedding_service.py
git commit -m "feat: add embedding service for scan records and formulas"
```

---

### Task 14: Refactor Scan Service to Use LangGraph

**Files:**
- Modify: `backend/app/services/scan_service.py` (full rewrite)
- Test: `backend/tests/test_scan_service.py`

**Step 1: Write the test**

```python
# tests/test_scan_service.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.scan_service import ScanService


@pytest.mark.asyncio
async def test_scan_and_solve_calls_graph():
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()

    service = ScanService(mock_db)

    mock_graph_result = {
        "ocr_text": "2x + 5 = 15",
        "ocr_confidence": 1.0,
        "detected_subject": "math",
        "problem_type": "equation",
        "difficulty": "easy",
        "knowledge_points": ["algebra"],
        "final_solution": {"question_type": "equation", "steps": [], "final_answer": "x = 5"},
        "llm_provider": "claude",
        "llm_model": "claude-sonnet",
        "prompt_tokens": 100,
        "completion_tokens": 50,
        "quality_score": 0.9,
        "attempt_count": 1,
        "solution_raw": "{}",
        "related_formula_ids": [],
    }

    mock_image = MagicMock()
    mock_image.read = AsyncMock(return_value=b"fake_image")
    mock_image.filename = "test.jpg"

    with patch.object(service, "_graph") as mock_graph, \
         patch("app.services.scan_service.storage_service") as mock_storage:
        mock_graph.ainvoke = AsyncMock(return_value=mock_graph_result)
        mock_storage.upload_image = AsyncMock(return_value="uploads/test.jpg")

        result = await service.scan_and_solve(
            user_id=1, image=mock_image, subject=None, ai_provider=None, grade_level=None
        )
        mock_graph.ainvoke.assert_called_once()
        assert result is not None
```

**Step 2: Rewrite app/services/scan_service.py**

```python
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile

from app.graph.solve_graph import solve_graph
from app.graph.followup_graph import followup_graph
from app.models.scan_record import ScanRecord
from app.models.solution import Solution
from app.models.conversation_message import ConversationMessage
from app.services.storage_service import StorageService
from app.services.conversation_service import ConversationService
from app.services.embedding_service import EmbeddingService
from app.schemas.scan import ScanResponse, SolutionResponse, SolutionStep

storage_service = StorageService()


class ScanService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._graph = solve_graph
        self._followup_graph = followup_graph
        self._conversation_service = ConversationService(db)
        self._embedding_service = EmbeddingService(db)

    async def scan_and_solve(
        self,
        user_id: int,
        image: UploadFile,
        subject: str | None = None,
        ai_provider: str | None = None,
        grade_level: str | None = None,
    ) -> ScanResponse:
        # 1. Upload image
        image_url = await storage_service.upload_image(image)
        image_bytes = await image.read()

        # 2. Run the LangGraph pipeline
        result = await self._graph.ainvoke({
            "image_bytes": image_bytes,
            "image_url": image_url,
            "user_id": user_id,
            "subject": subject,
            "grade_level": grade_level,
            "preferred_provider": ai_provider,
            "attempt_count": 0,
        })

        # 3. Persist scan record
        scan_record = ScanRecord(
            user_id=user_id,
            image_url=image_url,
            ocr_text=result.get("ocr_text", ""),
            ocr_confidence=result.get("ocr_confidence"),
            subject=result.get("detected_subject"),
            problem_type=result.get("problem_type"),
            difficulty=result.get("difficulty"),
            knowledge_points=result.get("knowledge_points", []),
        )
        self.db.add(scan_record)
        await self.db.flush()

        # 4. Persist solution
        solution = Solution(
            scan_id=scan_record.id,
            ai_provider=result.get("llm_provider", "unknown"),
            model=result.get("llm_model", "unknown"),
            content=result.get("solution_raw", ""),
            steps=result.get("final_solution", {}).get("steps"),
            final_answer=result.get("final_solution", {}).get("final_answer"),
            knowledge_points=result.get("knowledge_points", []),
            quality_score=result.get("quality_score"),
            prompt_tokens=result.get("prompt_tokens", 0),
            completion_tokens=result.get("completion_tokens", 0),
            attempt_number=result.get("attempt_count", 1),
            related_formula_ids=result.get("related_formula_ids", []),
        )
        self.db.add(solution)

        # 5. Save initial conversation (system + solution)
        await self._conversation_service.add_message(
            scan_record.id, "system",
            f"Problem: {result.get('ocr_text', '')}",
        )
        await self._conversation_service.add_message(
            scan_record.id, "assistant",
            result.get("solution_raw", ""),
        )

        await self.db.commit()

        # 6. Generate embedding async (best-effort)
        try:
            await self._embedding_service.embed_scan_record(
                scan_record.id, result.get("ocr_text", "")
            )
            await self.db.commit()
        except Exception:
            pass

        # 7. Build response
        final = result.get("final_solution", {})
        return ScanResponse(
            scan_id=str(scan_record.id),
            ocr_text=result.get("ocr_text", ""),
            solution=SolutionResponse(
                question_type=final.get("question_type", ""),
                knowledge_points=final.get("knowledge_points", []),
                steps=[SolutionStep(**s) for s in final.get("steps", [])],
                final_answer=final.get("final_answer", ""),
                explanation=final.get("explanation"),
                tips=final.get("tips"),
            ),
            related_formulas=[],
            created_at=scan_record.created_at or datetime.utcnow(),
        )

    async def followup(
        self, scan_id: int, user_id: int, message: str
    ) -> dict:
        """Handle follow-up question on a scan."""
        history = await self._conversation_service.get_history(scan_id)

        # Get scan record for context
        result_row = await self.db.execute(
            select(ScanRecord).where(ScanRecord.id == scan_id)
        )
        scan_record = result_row.scalars().first()
        subject = scan_record.subject if scan_record else "math"

        # Run follow-up graph
        result = await self._followup_graph.ainvoke({
            "scan_id": scan_id,
            "user_message": message,
            "conversation_history": history,
            "subject": subject,
            "grade_level": scan_record.difficulty if scan_record else "middle school",
        })

        # Save messages
        await self._conversation_service.add_message(scan_id, "user", message)
        await self._conversation_service.add_message(
            scan_id, "assistant", result.get("reply", "")
        )
        await self.db.commit()

        return {
            "reply": result.get("reply", ""),
            "tokens_used": result.get("tokens_used", 0),
        }

    async def get_scan_result(self, scan_id: int) -> ScanResponse | None:
        """Retrieve a previous scan result."""
        result = await self.db.execute(
            select(ScanRecord).where(ScanRecord.id == scan_id)
        )
        scan_record = result.scalars().first()
        if not scan_record:
            return None

        sol_result = await self.db.execute(
            select(Solution)
            .where(Solution.scan_id == scan_id)
            .order_by(Solution.created_at.desc())
        )
        solution = sol_result.scalars().first()

        if not solution:
            return None

        steps = solution.steps or []
        return ScanResponse(
            scan_id=str(scan_record.id),
            ocr_text=scan_record.ocr_text or "",
            solution=SolutionResponse(
                question_type=solution.knowledge_points[0] if solution.knowledge_points else "",
                knowledge_points=solution.knowledge_points or [],
                steps=[SolutionStep(**s) if isinstance(s, dict) else s for s in steps],
                final_answer=solution.final_answer or "",
                explanation=None,
                tips=None,
            ),
            related_formulas=[],
            created_at=scan_record.created_at,
        )
```

**Step 3: Run tests**

Run: `cd backend && python -m pytest tests/test_scan_service.py -v`
Expected: PASS

**Step 4: Commit**

```bash
git add app/services/scan_service.py tests/test_scan_service.py
git commit -m "refactor: rewrite scan_service to use LangGraph pipeline + conversation memory"
```

---

### Task 15: Update Schemas

**Files:**
- Modify: `backend/app/schemas/scan.py`
- Create: `backend/app/schemas/conversation.py`
- Create: `backend/app/schemas/stats.py`

**Step 1: Add FollowUp schemas to scan.py**

Append to `app/schemas/scan.py`:

```python
class FollowUpRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class FollowUpResponse(BaseModel):
    reply: str
    message_id: str | None = None
    tokens_used: int = 0


class ConversationMessageResponse(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    messages: list[ConversationMessageResponse]
    total_messages: int
```

**Step 2: Create app/schemas/stats.py**

```python
from datetime import date, datetime
from pydantic import BaseModel


class DailyStatResponse(BaseModel):
    stat_date: date
    subject: str
    scan_count: int
    correct_count: int
    avg_quality_score: float
    study_minutes: int
    mastered_count: int

    class Config:
        from_attributes = True


class StatsSummaryResponse(BaseModel):
    total_scans: int
    total_mastered: int
    avg_quality: float
    subjects: dict[str, int]  # subject -> count
```

**Step 3: Commit**

```bash
git add app/schemas/
git commit -m "feat: add schemas for followup, conversation, and stats"
```

---

### Task 16: Update API Endpoints

**Files:**
- Modify: `backend/app/api/v1/scan.py`
- Create: `backend/app/api/v1/stats.py`
- Modify: `backend/app/api/v1/router.py`

**Step 1: Update app/api/v1/scan.py — add followup + conversation endpoints**

Add these routes to the existing scan router:

```python
from app.schemas.scan import FollowUpRequest, FollowUpResponse, ConversationResponse, ConversationMessageResponse
from app.services.conversation_service import ConversationService


@router.post("/{scan_id}/followup", response_model=FollowUpResponse)
async def followup(
    scan_id: int,
    request: FollowUpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a follow-up question about a scan."""
    service = ScanService(db)
    result = await service.followup(
        scan_id=scan_id,
        user_id=current_user.id,
        message=request.message,
    )
    return FollowUpResponse(
        reply=result["reply"],
        tokens_used=result.get("tokens_used", 0),
    )


@router.get("/{scan_id}/conversation", response_model=ConversationResponse)
async def get_conversation(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get conversation history for a scan."""
    service = ConversationService(db)
    history = await service.get_history(scan_id)
    return ConversationResponse(
        messages=[
            ConversationMessageResponse(
                id=str(i),
                role=msg["role"],
                content=msg["content"],
                created_at=msg["created_at"],
            )
            for i, msg in enumerate(history)
        ],
        total_messages=len(history),
    )
```

**Step 2: Create app/api/v1/stats.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.learning_stats import LearningStats
from app.models.scan_record import ScanRecord
from app.models.mistake_book import MistakeBook
from app.schemas.stats import StatsSummaryResponse, DailyStatResponse

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=StatsSummaryResponse)
async def get_stats_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get learning stats summary for current user."""
    # Total scans
    scan_result = await db.execute(
        select(func.count(ScanRecord.id))
        .where(ScanRecord.user_id == current_user.id)
    )
    total_scans = scan_result.scalar() or 0

    # Total mastered mistakes
    mastered_result = await db.execute(
        select(func.count(MistakeBook.id))
        .where(MistakeBook.user_id == current_user.id, MistakeBook.mastered == True)
    )
    total_mastered = mastered_result.scalar() or 0

    # Average quality from stats
    avg_result = await db.execute(
        select(func.avg(LearningStats.avg_quality_score))
        .where(LearningStats.user_id == current_user.id)
    )
    avg_quality = avg_result.scalar() or 0.0

    # Subject breakdown
    subject_result = await db.execute(
        select(ScanRecord.subject, func.count(ScanRecord.id))
        .where(ScanRecord.user_id == current_user.id, ScanRecord.subject.isnot(None))
        .group_by(ScanRecord.subject)
    )
    subjects = {row[0]: row[1] for row in subject_result.all()}

    return StatsSummaryResponse(
        total_scans=total_scans,
        total_mastered=total_mastered,
        avg_quality=round(float(avg_quality), 2),
        subjects=subjects,
    )


@router.get("/daily", response_model=list[DailyStatResponse])
async def get_daily_stats(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get daily learning stats."""
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow().date() - timedelta(days=days)

    result = await db.execute(
        select(LearningStats)
        .where(
            LearningStats.user_id == current_user.id,
            LearningStats.stat_date >= cutoff,
        )
        .order_by(LearningStats.stat_date.desc())
    )
    stats = result.scalars().all()
    return [DailyStatResponse.model_validate(s) for s in stats]
```

**Step 3: Update app/api/v1/router.py — add stats route**

```python
from app.api.v1 import auth, scan, history, mistakes, formulas, stats

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(scan.router)
api_router.include_router(history.router)
api_router.include_router(mistakes.router)
api_router.include_router(formulas.router)
api_router.include_router(stats.router)
```

**Step 4: Commit**

```bash
git add app/api/v1/
git commit -m "feat: add followup, conversation, and stats API endpoints"
```

---

### Task 17: Remove Old AI Service

**Files:**
- Delete: `backend/app/services/ai_service.py`
- Keep: `backend/app/utils/prompt_templates.py` (legacy reference, can be removed later)

**Step 1: Verify no remaining imports of ai_service**

Run: `cd backend && grep -r "ai_service" app/ --include="*.py" -l`

If any file still imports `ai_service`, update it to use the graph or `app.llm.registry` instead.

**Step 2: Delete ai_service.py**

```bash
rm app/services/ai_service.py
```

**Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove old ai_service.py (replaced by LangGraph pipeline)"
```

---

## Phase 6: Integration Test

### Task 18: End-to-End Solve Pipeline Test

**Files:**
- Create: `backend/tests/test_integration_solve.py`

**Step 1: Write integration test**

```python
# tests/test_integration_solve.py
"""
Integration test for the full solve pipeline.
Uses mocked LLM responses to test the graph end-to-end.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.graph.solve_graph import build_solve_graph


def _mock_llm_response(content: str):
    """Create a mock LLM response."""
    response = MagicMock()
    response.content = content
    response.usage_metadata = {"input_tokens": 50, "output_tokens": 50}
    return response


@pytest.mark.asyncio
async def test_full_solve_pipeline():
    """Test the full solve pipeline with mocked LLMs."""
    graph = build_solve_graph()

    analysis_response = _mock_llm_response(
        '{"subject": "math", "problem_type": "equation", "difficulty": "easy", "knowledge_points": ["algebra"]}'
    )
    solve_response = _mock_llm_response(
        '{"question_type": "equation", "knowledge_points": ["algebra"], '
        '"steps": [{"step": 1, "description": "Subtract 5", "formula": "", "calculation": "2x = 10"}], '
        '"final_answer": "x = 5", "explanation": "We isolate x", "tips": "Check your answer"}'
    )
    eval_response = _mock_llm_response(
        '{"scores": {"correctness": 0.95}, "overall": 0.95, "issues": [], "pass": true}'
    )

    mock_llm = AsyncMock()
    # Sequence: analyze (fast), solve (strong), evaluate (fast)
    mock_llm.ainvoke = AsyncMock(
        side_effect=[analysis_response, solve_response, eval_response]
    )
    mock_llm._llm_type = "mock"
    mock_llm.model_name = "mock-model"

    with patch("app.graph.nodes.analyze.get_llm", return_value=mock_llm), \
         patch("app.graph.nodes.solve.select_llm", return_value=mock_llm), \
         patch("app.graph.nodes.evaluate.get_llm", return_value=mock_llm), \
         patch("app.graph.nodes.ocr.ocr_service") as mock_ocr:

        mock_ocr.extract_text = AsyncMock(return_value="Solve 2x + 5 = 15")

        result = await graph.ainvoke({
            "image_bytes": b"fake_image_data",
            "image_url": "uploads/test.jpg",
            "user_id": 1,
            "subject": None,
            "grade_level": "middle school",
            "preferred_provider": None,
            "attempt_count": 0,
        })

        # Verify pipeline completed
        assert result["ocr_text"] == "Solve 2x + 5 = 15"
        assert result["detected_subject"] == "math"
        assert result["quality_score"] >= 0.7
        assert result["final_solution"]["final_answer"] == "x = 5"
        assert result["attempt_count"] == 1  # no retries needed


@pytest.mark.asyncio
async def test_solve_pipeline_retries_on_low_quality():
    """Test that pipeline retries when quality is low."""
    graph = build_solve_graph()

    analysis_response = _mock_llm_response(
        '{"subject": "math", "problem_type": "equation", "difficulty": "easy", "knowledge_points": ["algebra"]}'
    )
    bad_solve_response = _mock_llm_response(
        '{"question_type": "equation", "knowledge_points": [], "steps": [], "final_answer": "wrong", "explanation": "", "tips": ""}'
    )
    good_solve_response = _mock_llm_response(
        '{"question_type": "equation", "knowledge_points": ["algebra"], "steps": [{"step": 1, "description": "solve", "formula": "", "calculation": "x=5"}], "final_answer": "x = 5", "explanation": "", "tips": ""}'
    )
    low_eval = _mock_llm_response('{"scores": {}, "overall": 0.3, "issues": ["wrong answer"], "pass": false}')
    high_eval = _mock_llm_response('{"scores": {}, "overall": 0.9, "issues": [], "pass": true}')

    mock_llm = AsyncMock()
    mock_llm._llm_type = "mock"
    mock_llm.model_name = "mock"
    # Sequence: analyze, solve(bad), eval(low), solve(good), eval(high)
    mock_llm.ainvoke = AsyncMock(
        side_effect=[analysis_response, bad_solve_response, low_eval, good_solve_response, high_eval]
    )

    with patch("app.graph.nodes.analyze.get_llm", return_value=mock_llm), \
         patch("app.graph.nodes.solve.select_llm", return_value=mock_llm), \
         patch("app.graph.nodes.evaluate.get_llm", return_value=mock_llm), \
         patch("app.graph.nodes.ocr.ocr_service") as mock_ocr:

        mock_ocr.extract_text = AsyncMock(return_value="Solve 2x + 5 = 15")

        result = await graph.ainvoke({
            "image_bytes": b"fake",
            "image_url": "test.jpg",
            "user_id": 1,
            "attempt_count": 0,
        })

        assert result["attempt_count"] == 2  # retried once
        assert result["quality_score"] >= 0.7
```

**Step 2: Run integration tests**

Run: `cd backend && python -m pytest tests/test_integration_solve.py -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add tests/test_integration_solve.py
git commit -m "test: add integration tests for LangGraph solve pipeline with retry"
```

---

### Task 19: Run Full Test Suite

**Step 1: Run all tests**

Run: `cd backend && python -m pytest -v --tb=short`

Fix any failures before proceeding.

**Step 2: Run linter**

Run: `cd backend && ruff check . && black --check . && isort --check .`

Fix any formatting issues.

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: resolve test and lint issues from langgraph refactor"
```

---

### Task 20: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md` (root level) — update Backend section

**Step 1: Update the architecture section to reflect LangGraph**

Key changes:
- Replace "LiteLLM" references with "LangGraph + LangChain"
- Add `app/graph/` and `app/llm/` to the structure
- Update "Key patterns" section
- Add new endpoints to API table
- Update Configuration section

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for langgraph refactor"
```

---

## Summary

| Phase | Tasks | What changes |
|-------|-------|-------------|
| 1. Infrastructure | 1-3 | docker-compose (pgvector), requirements, config |
| 2. LLM Layer | 4-6 | `app/llm/` — registry, embeddings, prompts |
| 3. Database | 7-8 | New models + enhanced columns + migration |
| 4. LangGraph | 9-11 | `app/graph/` — state, nodes, edges, compiled graphs |
| 5. Services + API | 12-17 | Refactored scan_service, conversation, stats, new endpoints |
| 6. Testing | 18-20 | Integration tests, full suite, docs update |

**Total new files:** ~25
**Modified files:** ~15
**Deleted files:** 1 (ai_service.py)
