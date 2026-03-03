# EduScan LLM Call Architecture

## Table of Contents

- [Overall Architecture](#overall-architecture)
- [LLM Registry — Model Registry](#llm-registry--model-registry)
- [Complete Call Pipeline](#complete-call-pipeline)
  - [Stage 1: OCR — Image Text Extraction](#stage-1-ocr--image-text-extraction)
  - [Stage 2: Analyze — Problem Classification](#stage-2-analyze--problem-classification)
  - [Stage 3: Retrieve — RAG Search](#stage-3-retrieve--rag-search)
  - [Stage 4: Solve — Core Problem Solving](#stage-4-solve--core-problem-solving)
  - [Stage 5: Quick Verify — Fast Answer Verification](#stage-5-quick-verify--fast-answer-verification)
  - [Stage 6: Enrich — Result Enrichment](#stage-6-enrich--result-enrichment)
  - [Stage 7: Deep Evaluate — Deep Quality Assessment (Async)](#stage-7-deep-evaluate--deep-quality-assessment-async)
  - [Stage 8: Embedding — Vector Storage](#stage-8-embedding--vector-storage)
- [Follow-up Conversation](#follow-up-conversation)
- [Retry and Error Handling](#retry-and-error-handling)
- [Model Selection Strategy](#model-selection-strategy)
- [Prompt Design Guidelines](#prompt-design-guidelines)
- [Call Summary Table](#call-summary-table)
- [Key File Index](#key-file-index)

---

## Overall Architecture

The EduScan backend uses **LangGraph** to build a directed state graph (StateGraph) pipeline. When a user uploads an image or text, it goes through the full pipeline: OCR → Analyze → Retrieve → Solve → Verify → Enrich, calling multiple different LLMs along the way.

```
User uploads image/text
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  API Layer: POST /api/v1/scan/solve                      │
│  → ScanService.scan_and_solve()                          │
└───────────────────────┬──────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────┐
│              LangGraph solve_graph                        │
│                                                          │
│  ┌─────┐   ┌─────────┐   ┌──────────┐   ┌───────┐      │
│  │ OCR │──▶│ ANALYZE  │──▶│ RETRIEVE │──▶│ SOLVE │      │
│  │LLM1 │   │  LLM2   │   │(VectorDB)│   │ LLM3  │      │
│  └─────┘   └─────────┘   └──────────┘   └───┬───┘      │
│                                               │          │
│                                               ▼          │
│                                        ┌────────────┐    │
│                                        │QUICK VERIFY│    │
│                                        │   LLM4     │    │
│                                        └─────┬──────┘    │
│                                              │           │
│                              ┌───────────────┼────────┐  │
│                              │               │        │  │
│                              ▼               ▼        ▼  │
│                         Verified        Failed     Timeout│
│                         confidence    attempt<2    Skip   │
│                           ≥0.8       ┌──▶SOLVE     │     │
│                              │       │  (switch    │     │
│                              ▼       │   model)    ▼     │
│                         ┌────────┐   │       ┌────────┐  │
│                         │ ENRICH │◀──┘       │ ENRICH │  │
│                         │        │           │(caution)│  │
│                         └───┬────┘           └───┬────┘  │
│                             │                    │       │
│                             ▼                    ▼       │
│                            END                  END      │
└──────────────────────────────┬───────────────────────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼                     ▼
          ┌──────────────┐      ┌──────────────┐
          │DEEP EVALUATE │      │  EMBEDDING   │
          │ LLM5 (async) │      │ OpenAI (async)│
          └──────────────┘      └──────────────┘
```

---

## LLM Registry — Model Registry

> File: `app/llm/registry.py`

All LLM calls go through a unified Registry to obtain model instances. The underlying implementation uses LangChain's Chat Model abstraction.

### Supported Providers

| Provider | LangChain Class | API Key Config |
|----------|----------------|-------------|
| `claude` | `ChatAnthropic` (langchain_anthropic) | `ANTHROPIC_API_KEY` |
| `openai` | `ChatOpenAI` (langchain_openai) | `OPENAI_API_KEY` |
| `gemini` | `ChatGoogleGenerativeAI` (langchain_google_genai) | `GOOGLE_API_KEY` |

### Model Tiers

Each provider has different model tiers used for different tasks:

| Provider | strong (core solving) | fast (lightweight tasks) | verify | evaluate |
|----------|-----------------|----------------|--------|----------|
| claude | claude-sonnet-4-20250514 | claude-haiku-4-5-20251001 | — | — |
| openai | gpt-4o | gpt-4o-mini | — | — |
| gemini | gemini-2.5-flash | gemini-2.5-flash-lite | gemini-2.5-flash-lite | gemini-2.5-flash |

### Two Core Functions

**`get_llm(tier, provider)`** — Get a model by tier and provider:

```python
# Get the default provider's fast model
llm = get_llm("fast")

# Get Gemini's verify model
llm = get_llm("verify", "gemini")
```

All models use `temperature=0.1`. API keys are loaded from `.env` via pydantic-settings.

**`select_llm(preferred, subject, attempt)`** — Smart model selection (used in the Solve stage):

```python
# First attempt: select provider by subject
llm = select_llm(preferred=None, subject="math", attempt=0)
# → math uses claude-sonnet-4

# Retry: automatically rotate to the next provider
llm = select_llm(preferred=None, subject="math", attempt=1)
# → rotates to openai gpt-4o
```

Subject-to-provider mapping:

| Subject | Default Provider |
|---------|-------------|
| math | claude |
| physics | claude |
| chinese | claude |
| chemistry | openai |
| biology | openai |
| english | openai |

---

## Complete Call Pipeline

### Stage 1: OCR — Image Text Extraction

> File: `app/services/ocr_service.py` → `GeminiVisionOCRProvider`
> Graph node: `app/graph/nodes/ocr.py`

**Model**: Gemini 2.5 Flash Lite (fixed)
**Call method**: Multimodal — image base64 + text instruction

```python
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",
    temperature=0.0,  # OCR requires no creativity
)

message = HumanMessage(content=[
    {"type": "text", "text": "Extract ALL text from this image..."},
    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
])

result = await llm.ainvoke([message])
```

**Prompt highlights**:
- Detect image orientation (phone photos may be rotated)
- Output math expressions in LaTeX `$...$` format
- Preserve original layout, auto-number multiple problems
- Output only extracted text, no additional explanation

**Preprocessing**: Before calling, use Pillow's `ImageOps.exif_transpose()` to correct EXIF rotation.

**Fallback**: If the configured OCR provider is not implemented, automatically fall back to Gemini Vision.

**Skip condition**: If the user directly inputs text (not an image), skip OCR and use input_text directly.

---

### Stage 2: Analyze — Problem Classification

> File: `app/graph/nodes/analyze.py`
> Prompt: `app/llm/prompts/analysis.py`

**Model**: Default provider's **fast** tier (e.g., claude-haiku-4-5)
**Purpose**: Identify subject, problem type, difficulty, knowledge points

```python
llm = get_llm("fast")
messages = build_analysis_messages(ocr_text, grade_level)
result = await llm.ainvoke(messages)
parsed = json.loads(result.content)
```

**System Prompt**:
```
You are an expert education AI that classifies student homework problems.
Analyze the given problem text and identify:
1. Subject (math, physics, chemistry, biology, english, chinese)
2. Problem type (equation, geometry, word_problem, proof, multiple_choice, fill_in_blank)
3. Difficulty (easy, medium, hard)
4. Key knowledge points

Respond ONLY in JSON.
```

**Output example**:
```json
{
  "subject": "math",
  "problem_type": "equation",
  "difficulty": "medium",
  "knowledge_points": ["algebra", "linear_equations"]
}
```

**Fallback**: When the LLM call fails, use the keyword-matching fallback function `_detect_subject_fallback()`, which scans for subject keywords in the text (e.g., "equation"→math, "force"→physics).

---

### Stage 3: Retrieve — RAG Search

> File: `app/graph/nodes/retrieve.py`

**Current status**: Placeholder returning empty results. Pending pgvector integration.

**Design goal**: Based on the problem text, retrieve from the knowledge base:
- `related_formulas` — related formulas
- `similar_problems` — similar historical problems

Retrieved results are injected as context into the Solve stage prompt.

---

### Stage 4: Solve — Core Problem Solving

> File: `app/graph/nodes/solve.py`
> Prompt: `app/llm/prompts/solve.py`

**Model**: `select_llm()` smart selection — picks the **strong** tier for the appropriate provider by subject
**This is the most critical LLM call in the entire pipeline.**

```python
llm = select_llm(
    preferred=state.get("preferred_provider"),
    subject=state.get("detected_subject", "math"),
    attempt=state.get("attempt_count", 0),
)

# Build RAG context
context = _build_context(related_formulas, similar_problems)

messages = build_solve_messages(
    ocr_text=ocr_text,
    subject=subject,
    grade_level=grade_level,
    context=context,  # RAG retrieval results injected here
)

result = await llm.ainvoke(messages)
```

**System Prompt**:
```
You are an experienced {subject} teacher helping a {grade_level} student.
Your goal is to provide clear, educational explanations that help the student
understand the solution process.

IMPORTANT: Respond ONLY in valid JSON format.
```

**User Prompt structure**:
```
Please solve the following problem step by step...

Math formatting rules:
- formula fields: pure LaTeX without $ delimiters
- description/calculation fields: use $ and $$ to wrap math expressions
- Use \frac{}{}, x^{}, \sqrt{} and other LaTeX syntax

## Reference Context (if RAG results available)
- Related formulas...
- Similar problems...

## Problem
{ocr_text}

Respond in JSON format:
{
  "question_type": "...",
  "knowledge_points": [...],
  "steps": [{"step": 1, "description": "...", "formula": "...", "calculation": "..."}],
  "final_answer": "...",
  "explanation": "...",
  "tips": "..."
}
```

**JSON parsing fallback**:
1. First try `json.loads(result.content)`
2. If that fails, try extracting the first `{...}` block from the text
3. If both fail, construct a fallback structure with the raw response in `final_answer`

**Retry mechanism**: If the subsequent Quick Verify fails, `attempt_count + 1`, re-enter the Solve node. `select_llm` automatically rotates to a different provider (e.g., Claude → OpenAI → Gemini).

---

### Stage 5: Quick Verify — Fast Answer Verification

> File: `app/graph/nodes/quick_verify.py`
> Prompt: `app/llm/prompts/verify.py`

**Model**: Gemini 2.5 Flash Lite (fixed)
**Purpose**: Use a different model to independently verify whether the answer is correct
**Timeout**: Hard limit of **5 seconds**

```python
llm = get_llm("verify", "gemini")
messages = build_verify_messages(problem_text, final_answer, steps_summary, subject)

result = await asyncio.wait_for(
    llm.ainvoke(messages),
    timeout=5.0,  # timeout → skip verification
)
```

**System Prompt**:
```
You are a math/science verification assistant. Please independently verify
whether the given answer to the following problem is correct.

Requirements:
1. Independently calculate the correct answer yourself
2. Compare it with the given answer
3. Check key steps for logical errors

Return ONLY JSON:
{
  "independent_answer": "your calculated answer",
  "is_correct": true/false,
  "error_description": "if incorrect, explain which step went wrong",
  "confidence": 0.0-1.0
}
```

**Decision logic** (`app/graph/edges.py`):

| Condition | Route | Description |
|-----------|-------|-------------|
| `is_correct=true && confidence≥0.8` | → ENRICH | Verification passed |
| `verify_passed=None` (timeout/error/low confidence) | → ENRICH | Cannot verify, skip |
| `is_correct=false && attempt<2` | → SOLVE (retry) | Switch model and re-solve |
| `is_correct=false && attempt≥2` | → ENRICH (caution) | Max retries reached, flag warning |

**Fallback**: Both timeout and exceptions return `verify_passed=None`, never blocking the main flow.

---

### Stage 6: Enrich — Result Enrichment

> File: `app/graph/nodes/enrich.py`

**No LLM call**. Pure data assembly: packages the solution result + related formulas + difficulty + quality score into `final_solution`.

---

### Stage 7: Deep Evaluate — Deep Quality Assessment (Async)

> File: `app/graph/nodes/deep_evaluate.py`
> Prompt: `app/llm/prompts/deep_evaluate.py`

**Model**: Gemini 2.5 Flash (fixed)
**Execution**: `asyncio.create_task()` — runs asynchronously after the user has already received results

```python
# Triggered in scan_service.py
asyncio.create_task(self._run_deep_evaluate_background(...))
```

```python
llm = get_llm("evaluate", "gemini")
messages = build_deep_evaluate_messages(
    problem_text, solution_raw, final_answer, steps, subject, grade_level
)
result = await llm.ainvoke(messages)
```

**System Prompt**:
```
You are a senior teacher comprehensively evaluating the quality of an
AI-generated solution for a K12 student homework problem.

Scoring dimensions (0.0-1.0):
- correctness: Whether the answer and every calculation step is correct
- completeness: Whether all key concepts are covered, whether any steps are missing
- clarity: Whether it is easy to understand for students at this grade level
- pedagogy: Whether it guides the student to think rather than just giving the answer
- format: Whether LaTeX formatting, step numbering, and layout are well-structured
- overall: Weighted average of the above five dimensions
```

**Output example**:
```json
{
  "correctness": 0.95,
  "completeness": 0.9,
  "clarity": 0.85,
  "pedagogy": 0.8,
  "format": 0.9,
  "overall": 0.88,
  "improvement_suggestions": "Step 3 could include more intermediate derivation",
  "better_approach": null
}
```

**Persistence**: Written to `Solution.deep_evaluation` (JSONB) and `Solution.quality_score`.

---

### Stage 8: Embedding — Vector Storage

> File: `app/llm/embeddings.py`

**Model**: OpenAI `text-embedding-3-small` (1536 dimensions)
**Execution**: Best-effort; failure does not affect the main flow

```python
_embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector = await _embeddings.aembed_query(text)
```

Used to embed problem text into vectors, stored in pgvector, providing the data foundation for the Retrieve stage's "similar problem search".

---

## Follow-up Conversation

> File: `app/graph/followup_graph.py`
> Prompt: `app/llm/prompts/followup.py`
> API: `POST /api/v1/scan/{scan_id}/followup`

A separate LangGraph for user follow-up questions on a specific problem.

```
START → build_context → generate_reply → END
```

```python
llm = get_llm("strong")  # Default provider's strong model
messages = build_followup_messages(
    conversation_history,  # Full conversation history
    user_message,
    subject, grade_level,
)
result = await llm.ainvoke(messages)
```

**System Prompt**:
```
You are a patient {subject} teacher having a conversation with a {grade_level} student.
You previously helped them solve a problem. Now they have a follow-up question.
Be encouraging, clear, and educational. Use LaTeX for any formulas.
```

**Conversation history format**: Uses LangChain's `SystemMessage` / `HumanMessage` / `AIMessage` alternating to maintain full context.

**Persistence**: Each conversation turn is saved to the `conversation_messages` table, managed by `ConversationService`.

---

## Retry and Error Handling

### Solve Retry (Provider Rotation)

```
Attempt 1 (attempt=0): Select provider by subject → e.g., Claude Sonnet
        │
        ▼ Quick Verify failed
        │
Attempt 2 (attempt=1): Rotate to next provider → e.g., OpenAI GPT-4o
        │
        ▼ Quick Verify failed again
        │
Attempt 3 (attempt=2): Rotate to next provider → e.g., Gemini Flash
        │
        ▼ Still failed
        │
Mark verification_status = "caution", return last result
```

### Error Handling by Stage

| Stage | Failure Handling |
|-------|---------|
| OCR | If provider not implemented, fall back to Gemini Vision |
| Analyze | On LLM failure, use keyword-matching fallback |
| Solve | On JSON parse failure, try extracting `{...}` substring |
| Quick Verify | 5s timeout or exception → skip verification, don't block |
| Deep Evaluate | Exception → log error, doesn't affect already-returned results |
| Embedding | Exception → silently ignore |

---

## Model Selection Strategy

### Design Rationale for Task-Based Model Assignment

| Task Type | Requirement | Selection Strategy |
|-----------|------|---------|
| OCR | Multimodal, free tier | Gemini Flash Lite (fixed) |
| Classification | Fast, low cost | Default provider's fast tier |
| Solving | Strong reasoning | Provider's strong tier by subject |
| Verification | Independent second opinion, fast | Gemini Flash Lite (fixed, different from solve model) |
| Deep Evaluation | Comprehensive analysis | Gemini Flash (async, doesn't affect response time) |
| Follow-up | Strong conversational ability | Default provider's strong tier |
| Embedding | High-quality embeddings | OpenAI text-embedding-3-small (fixed) |

### Why Is Verification Fixed to Gemini?

- **Model independence**: Solve uses Claude/OpenAI; verification uses Gemini to avoid "checking your own work"
- **Cost control**: Gemini Flash Lite has generous free tier
- **Speed**: Needs a fast-responding model under the 5-second timeout

---

## Prompt Design Guidelines

### Common Principles for All Prompts

1. **Enforce JSON output**: All prompts require `Respond ONLY in JSON`
2. **Role setting**: Oriented toward K12 students with clear, educational language
3. **LaTeX conventions**:
   - `formula` fields: pure LaTeX, e.g., `\frac{-b \pm \sqrt{b^2-4ac}}{2a}`
   - Text fields: `$...$` for inline math, `$$...$$` for display math
4. **Language**: All prompts in English for consistency

### Prompt File Mapping

| Prompt File | Stage | Language |
|------------|---------|------|
| `prompts/analysis.py` | Analyze | English |
| `prompts/solve.py` | Solve | English |
| `prompts/verify.py` | Quick Verify | English |
| `prompts/evaluate.py` | (Reserved) | English |
| `prompts/deep_evaluate.py` | Deep Evaluate | English |
| `prompts/followup.py` | Follow-up | English |

---

## Call Summary Table

LLM calls for a complete problem-solving request:

| # | Stage | Model | Call Method | Sync/Async | Required |
|---|-------|-------|---------|----------|------|
| 1 | OCR | Gemini 2.5 Flash Lite | Multimodal (base64 image) | Sync | When image provided |
| 2 | Analyze | fast tier (e.g., Haiku) | Text → JSON | Sync | Yes |
| 3 | Solve | strong tier (e.g., Sonnet 4) | Text → JSON | Sync | Yes |
| 4 | Quick Verify | Gemini 2.5 Flash Lite | Text → JSON, 5s timeout | Sync | Yes (skippable) |
| 5 | Deep Evaluate | Gemini 2.5 Flash | Text → JSON | Background async | No |
| 6 | Embedding | OpenAI embedding-3-small | Embedding API | Sync (best-effort) | No |
| 7 | Follow-up | strong tier | Multi-turn conversation | Sync | Only on follow-up |

**Minimum calls**: 3 (text input, no image: Analyze + Solve + Verify)
**Typical calls**: 5 (image input: OCR + Analyze + Solve + Verify + Deep Evaluate)
**Maximum calls**: 9 (image + 3 Solve retries: OCR + Analyze + 3×Solve + 3×Verify + Deep Evaluate)

---

## Key File Index

```
backend/app/
├── llm/
│   ├── __init__.py              # Exports get_llm, select_llm
│   ├── registry.py              # Model registry, Provider/Tier/Subject mapping
│   ├── embeddings.py            # OpenAI Embedding wrapper
│   └── prompts/
│       ├── __init__.py          # Exports all prompt building functions
│       ├── analysis.py          # Analyze stage prompt
│       ├── solve.py             # Solve stage prompt
│       ├── verify.py            # Quick Verify stage prompt
│       ├── evaluate.py          # Evaluate prompt (reserved)
│       ├── deep_evaluate.py     # Deep Evaluate stage prompt
│       └── followup.py          # Follow-up conversation prompt
├── graph/
│   ├── state.py                 # SolveState / FollowUpState type definitions
│   ├── solve_graph.py           # Main solve LangGraph definition
│   ├── followup_graph.py        # Follow-up conversation LangGraph definition
│   ├── edges.py                 # Conditional edges: retry decision logic
│   └── nodes/
│       ├── ocr.py               # OCR node
│       ├── analyze.py           # Problem analysis node (calls LLM)
│       ├── retrieve.py          # RAG retrieval node (pending implementation)
│       ├── solve.py             # Problem solving node (calls LLM)
│       ├── quick_verify.py      # Quick verification node (calls LLM)
│       ├── enrich.py            # Result enrichment node (pure logic)
│       └── deep_evaluate.py     # Deep evaluation (calls LLM)
├── services/
│   ├── scan_service.py          # Service layer orchestrating the entire flow
│   ├── ocr_service.py           # OCR provider strategy pattern
│   ├── embedding_service.py     # Vector embedding service
│   └── conversation_service.py  # Conversation history management
├── config.py                    # Environment config (API keys, model names)
└── api/v1/scan.py               # HTTP route entry point
```

---

## LangGraph State Data Flow

`SolveState` (TypedDict) is passed between nodes. Each node reads the fields it needs and writes new fields:

```
OCR writes:
  → ocr_text, ocr_confidence

ANALYZE reads ocr_text, writes:
  → detected_subject, problem_type, difficulty, knowledge_points

RETRIEVE reads ocr_text, detected_subject, writes:
  → related_formulas, similar_problems

SOLVE reads ocr_text, detected_subject, grade_level, related_formulas, similar_problems, writes:
  → solution_raw, solution_parsed, llm_provider, llm_model, prompt_tokens, completion_tokens

QUICK VERIFY reads ocr_text, solution_parsed, detected_subject, writes:
  → verify_passed, verify_confidence, independent_answer, verify_error

ENRICH reads solution_parsed, related_formulas, difficulty, quality_score, writes:
  → final_solution, related_formula_ids
```
