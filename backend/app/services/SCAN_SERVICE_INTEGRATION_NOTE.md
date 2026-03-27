# Scan Service Integration for Tiered AI Model Routing

This note describes the changes needed in `scan_service.py` to integrate
subscription-tier-aware usage limits and model routing.

## 1. Add tier check BEFORE solving (usage limit gate)

In both `scan_and_solve()` (line ~50) and `scan_and_solve_stream()` (line ~95),
add a usage-limit check at the very beginning of each method, before any image
upload or graph invocation:

```python
from app.services.subscription_service import SubscriptionService

# At the top of scan_and_solve / scan_and_solve_stream:
sub_service = SubscriptionService(self.db)
allowed, remaining = await sub_service.check_usage_limit(user_id)
if not allowed:
    raise HTTPException(status_code=429, detail="Daily question limit reached")
```

For the guest endpoint, use `check_guest_usage(ip_hash)` instead, where
`ip_hash` is derived from the request IP (hash with SHA-256).

## 2. Pass user_tier to select_llm

The LangGraph pipeline calls `select_llm()` in the solve node. The user's tier
needs to be threaded through the graph state so the solve node can pass it:

- In the graph state dict passed to `self._graph.ainvoke(...)` (line ~70 and
  ~113), add a new key:

```python
user_tier = await sub_service.get_user_tier(user_id)
```

Then include `"user_tier": user_tier` in the `initial_input` dict.

- In the solve graph node (likely `app/graph/nodes/solve.py` or similar), read
  `state["user_tier"]` and pass it to `select_llm(..., user_tier=user_tier)`.
  The `select_llm` function already accepts `user_tier` and routes free users
  to Gemini/Groq.

## 3. Increment usage AFTER successful solve

After the graph returns a successful result, call:

```python
await sub_service.increment_usage(user_id)
```

For `scan_and_solve()`: add this after line ~81 (after `_persist_and_build_response`).

For `scan_and_solve_stream()`: add this after the stream completes successfully
(after the final result is persisted).

For the guest endpoint: use `increment_guest_usage(ip_hash)` instead.

## Summary of touched lines

| Location | Change |
|----------|--------|
| `scan_and_solve()` top (before image upload) | Add usage limit check |
| `scan_and_solve_stream()` top | Add usage limit check |
| `initial_input` dict in both methods | Add `"user_tier"` key |
| After `_persist_and_build_response` | Call `increment_usage()` |
| Solve graph node | Read `user_tier` from state, pass to `select_llm()` |
