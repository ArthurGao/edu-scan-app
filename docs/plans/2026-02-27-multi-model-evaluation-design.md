# Multi-Model Answer Evaluation System Design

**Date**: 2026-02-27
**Status**: Draft
**Author**: AI-assisted brainstorming

## 1. Goals

1. **Correctness verification** — Validate final answers are mathematically/logically correct
2. **Solution quality improvement** — Ensure steps are clear, complete, and pedagogically sound
3. **Model selection optimization** — Accumulate data to improve per-subject model routing
4. **Data-driven prompt iteration** — Identify weak areas in solve prompts and improve them over time

## 2. Architecture Overview

### Current Pipeline

```
OCR → ANALYZE → RETRIEVE → SOLVE → EVALUATE → ENRICH → END
```

### New Pipeline

```
OCR → ANALYZE → RETRIEVE → SOLVE → QUICK_VERIFY → (conditional) → ENRICH → END
                                                                        ↓
                                                                (async) DEEP_EVALUATE
```

### Two-Phase Evaluation Strategy

| Phase | Node | Timing | Model | Purpose |
|-------|------|--------|-------|---------|
| Phase 1 | `quick_verify` | Synchronous | Gemini 2.5 Flash-Lite | Validate final answer correctness |
| Phase 2 | `deep_evaluate` | Asynchronous | Gemini 2.5 Flash | Full 6-dimension quality scoring |

**Why Gemini?**
- Free tier: Flash-Lite 1000 req/day, Flash 250 req/day (no credit card required)
- Independent model from solve providers (Claude/GPT), avoids self-evaluation bias
- Fast inference, suitable for verification tasks

## 3. Phase 1: Quick Verify (Synchronous)

### Node: `quick_verify`

**Purpose**: Independent answer verification before returning to user. Does NOT re-solve the problem — asks Gemini to independently calculate and compare.

### Prompt Design

```
你是一个数学/理科验算助手。请独立验算以下题目的答案是否正确。

题目：{ocr_text}
给出的答案：{final_answer}
解题步骤摘要：{steps_summary}

要求：
1. 自己独立计算出正确答案
2. 对比给出的答案
3. 检查关键步骤是否有逻辑错误

返回 JSON：
{
  "independent_answer": "你算出的答案",
  "is_correct": true/false,
  "error_description": "如果错误，说明哪步出错",
  "confidence": 0.0-1.0
}
```

### Key Design Decisions

- **Model**: Gemini 2.5 Flash-Lite (free 1000 req/day, 15 RPM)
- **Input**: Only problem text + final answer + step summary (minimal tokens)
- **Timeout**: 5 seconds hard limit; on timeout, skip verification (don't block user)
- **Confidence threshold**: `confidence < 0.6` treated as "uncertain", triggers retry

### Conditional Logic (replaces current `should_retry`)

```python
def should_retry_after_verify(state: SolveState) -> str:
    if state.verify_passed and state.verify_confidence >= 0.8:
        return "enrich"          # Answer verified correct
    if state.verify_passed is None:
        return "enrich"          # Timeout/skip, proceed without verification
    if state.attempt_count < 2:
        return "solve"           # Failed verification, retry with different provider
    return "enrich"              # Max retries reached, return with caution flag
```

### State Additions

```python
# New fields in SolveState
verify_passed: Optional[bool] = None        # Whether verification passed
verify_confidence: float = 0.0              # Verification confidence score
independent_answer: Optional[str] = None    # Gemini's independently calculated answer
verify_error: Optional[str] = None          # Error description if verification failed
```

## 4. Phase 2: Deep Evaluate (Asynchronous)

### Node: `deep_evaluate`

**Purpose**: Comprehensive quality assessment after response is returned to user. Results stored for data accumulation and model routing optimization.

### Trigger

Fired as a background task after `ENRICH` completes and response is sent to user. Does not affect user-facing latency.

### Evaluation Dimensions (6)

```json
{
  "correctness": 0.95,
  "completeness": 0.8,
  "clarity": 0.9,
  "pedagogy": 0.85,
  "format": 0.9,
  "overall": 0.88,
  "improvement_suggestions": "第2步可以补充为什么要移项的原因",
  "better_approach": null
}
```

| Dimension | What it Measures |
|-----------|-----------------|
| `correctness` | Mathematical/logical accuracy of answer and steps |
| `completeness` | Coverage of all knowledge points, no missing steps |
| `clarity` | Readability and understandability for K12 students |
| `pedagogy` | Educational value: guides thinking vs. just gives answer |
| `format` | LaTeX formatting, step numbering, structure |
| `overall` | Weighted average of above dimensions |

**Note**: Replaced original `relevance` with `pedagogy` — more meaningful for K12 education.

### Model

- **Gemini 2.5 Flash** (free 250 req/day, 10 RPM)
- Uses "strong" tier for thorough evaluation
- Full solution context passed (all steps, formulas, explanation)

### Storage

New JSONB column on `solutions` table:

```python
deep_evaluation = Column(JSONB, nullable=True)  # Populated async after response
```

## 5. User-Facing Verification Status

### Response Schema Addition

```python
class SolutionResponse(BaseModel):
    # ... existing fields ...
    verification_status: str          # "verified" | "unverified" | "caution"
    verification_confidence: float    # 0.0-1.0
```

### Status Mapping

| Status | Condition | Frontend Display |
|--------|-----------|-----------------|
| `verified` | quick_verify pass AND confidence >= 0.8 | Green badge "已验证 ✓" |
| `unverified` | Verification timeout or skipped | No badge shown |
| `caution` | Failed after max retries | Yellow badge "建议核实 ⚠" |

## 6. Data Accumulation & Optimization

### What Data is Collected

| Data | Source | Purpose |
|------|--------|---------|
| Per-model correctness rate by subject | quick_verify results | Optimize `SUBJECT_PROVIDER_MAP` routing |
| Per-model correctness rate by difficulty | quick_verify + analyze | Decide when to use strong vs fast models |
| Common improvement suggestions | deep_evaluate | Improve solve prompt templates |
| Better approach discoveries | deep_evaluate | Identify solve prompt blind spots |
| Quality score trends over time | deep_evaluate | Track overall system improvement |

### Future Use: Automatic Routing Optimization

Once enough data is accumulated (e.g., 500+ evaluations per subject):

```python
# Example: data-driven routing
SUBJECT_PROVIDER_MAP = {
    "math": best_provider_for("math", min_samples=500),
    "physics": best_provider_for("physics", min_samples=500),
    # ...
}
```

## 7. Gemini Model Configuration Update

**URGENT**: `gemini-2.0-flash` retires on March 3, 2026. Must update before then.

### Updated Registry

```python
MODEL_CONFIG = {
    "claude": {
        "strong": "claude-sonnet-4-20250514",
        "fast": "claude-haiku-4-5-20251001",
    },
    "openai": {
        "strong": "gpt-4o",
        "fast": "gpt-4o-mini",
    },
    "gemini": {
        "strong": "gemini-2.5-flash",
        "fast": "gemini-2.5-flash-lite",
        "verify": "gemini-2.5-flash-lite",     # NEW: sync verification
        "evaluate": "gemini-2.5-flash",         # NEW: async deep evaluation
    },
}
```

## 8. File Changes

| File | Action | Description |
|------|--------|-------------|
| `graph/nodes/quick_verify.py` | **Create** | Synchronous answer verification node |
| `graph/nodes/deep_evaluate.py` | **Create** | Asynchronous deep evaluation node |
| `graph/nodes/evaluate.py` | **Remove/Deprecate** | Replaced by quick_verify + deep_evaluate |
| `graph/solve_graph.py` | **Modify** | Replace evaluate with quick_verify, add conditional edge |
| `graph/edges.py` | **Modify** | New `should_retry_after_verify()` logic |
| `graph/state.py` | **Modify** | Add verify_* fields to SolveState |
| `llm/registry.py` | **Modify** | Update Gemini models, add verify/evaluate tiers |
| `llm/prompts/verify.py` | **Create** | Quick verification prompt template |
| `llm/prompts/deep_evaluate.py` | **Create** | Deep evaluation prompt template |
| `schemas/scan.py` | **Modify** | Add verification_status to SolutionResponse |
| `models/solution.py` | **Modify** | Add deep_evaluation JSONB column |
| `services/scan_service.py` | **Modify** | Trigger async deep_evaluate after response |

## 9. Rate Limit Considerations

### Free Tier Budget (per day)

| Operation | Model | Daily Limit | Expected Usage |
|-----------|-------|-------------|----------------|
| Quick Verify | Flash-Lite | 1000 req | ~1 per solve (+ retries) |
| Deep Evaluate | Flash | 250 req | ~1 per solve |

**Estimation**: With ~200 solves/day, free tier is sufficient. If exceeding limits:
- Quick Verify: gracefully skip (return `unverified`)
- Deep Evaluate: queue and process next day

### Fallback Strategy

```python
async def quick_verify(state):
    try:
        result = await gemini_verify(state, timeout=5.0)
        return result
    except (RateLimitError, TimeoutError):
        # Graceful degradation: skip verification
        return {"verify_passed": None, "verify_confidence": 0.0}
```

## 10. Migration Plan

### Phase 1: Gemini Model Update (Day 1) — URGENT
- Update `registry.py` with Gemini 2.5 models
- Test existing solve pipeline still works

### Phase 2: Quick Verify (Day 2-3)
- Implement `quick_verify` node and prompt
- Update solve_graph conditional edges
- Add verification_status to response schema
- Frontend: display verification badges

### Phase 3: Deep Evaluate (Day 4-5)
- Implement async `deep_evaluate` node
- Add deep_evaluation column to solutions table (Alembic migration)
- Wire up background task in scan_service

### Phase 4: Data Dashboard (Future)
- Build analytics views for accumulated evaluation data
- Implement data-driven model routing optimization
