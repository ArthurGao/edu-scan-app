# Tiered AI Model Routing & Subscription System

> Design doc for routing AI solve requests to different models based on user subscription tier, with free API providers for free users and premium models for paid users.

## Overview

Free users get AI-powered homework solving via free API providers (Gemini → Groq fallback). Paid users get direct access to Claude and other premium models. All users have usage limits tracked per day. A Subscription table manages user tiers; a UsageRecord table tracks daily consumption.

## Model Routing Strategy

```
Request → Check user tier
  ├─ paid → Claude / OpenAI (subject-based routing, existing logic)
  └─ free → Check daily usage
       ├─ Limit exceeded → 429 "Daily limit reached, upgrade for more"
       └─ Under limit → Gemini 2.5 Flash (primary, higher quality)
            ├─ Success → Return result
            └─ Fail/rate-limited → Groq + Qwen3 32B (fallback)
                 ├─ Success → Return result
                 └─ Fail → 503 "Service busy, retry later"
```

### Usage Limits

| User Tier | Daily Solve Limit | Models |
|-----------|-------------------|--------|
| Free | 20/day | Gemini 2.5 Flash → Groq Qwen3 32B fallback |
| Premium | Unlimited | Claude / OpenAI (subject-based) |
| Guest (no account) | 10/day per IP | Same as free |

### Free API Provider Capacity

| Provider | Free Tier Limits | Role |
|----------|-----------------|------|
| Gemini 2.5 Flash | 10 RPM, 250 RPD | Primary (higher quality) |
| Groq Qwen3 32B | 60 RPM, 14,400 RPD | Fallback (higher volume) |

## Data Model

### New Table: `subscriptions`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | Integer, PK | auto | Primary key |
| `user_id` | Integer, FK(users.id), unique | — | One-to-one with user |
| `plan` | String(20) | `"free"` | `free` / `premium` |
| `status` | String(20) | `"active"` | `active` / `expired` / `cancelled` |
| `started_at` | DateTime | now() | Subscription start |
| `expires_at` | DateTime, nullable | None | Expiry; null = never expires (free tier) |
| `payment_provider` | String(20), nullable | None | `stripe` / `apple` / `google` |
| `external_subscription_id` | String(255), nullable | None | Third-party subscription ID |
| `created_at` | DateTime | now() | Record created |
| `updated_at` | DateTime | now() | Record updated |

### New Table: `usage_records`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | Integer, PK | auto | Primary key |
| `user_id` | Integer, FK(users.id) | — | User reference |
| `date` | Date | — | Calendar date |
| `solve_count` | Integer | 0 | Number of solves today |
| `provider_used` | String(20) | — | Last provider: `gemini` / `groq` / `claude` |

**Constraints:**
- UNIQUE on `(user_id, date)` — one record per user per day
- INDEX on `(user_id, date)` for fast lookups

### Design Decisions

- New users get a `plan="free"` Subscription created automatically at registration.
- When `expires_at` is non-null and in the past, the system auto-downgrades to free behavior and sets `status="expired"`.
- UsageRecord aggregates per day; historical data can be cleaned up periodically.
- Subscription is a separate table (not a field on User) to support future payment integration cleanly.

## LLM Registry Changes

### New provider in `registry.py`

```python
LLM_REGISTRY = {
    "claude": ChatAnthropic,
    "openai": ChatOpenAI,
    "gemini": ChatGoogleGenerativeAI,
    "groq": ChatGroq,              # NEW
}

MODEL_CONFIG = {
    # ... existing configs unchanged ...
    "groq": {
        "strong": "qwen-qwq-32b",     # Strong reasoning for solving
        "fast": "qwen3-32b",          # Faster fallback
    },
}
```

### `select_llm()` signature change

```python
def select_llm(
    preferred: str | None,
    subject: str,
    attempt: int = 0,
    user_tier: str = "paid",    # NEW parameter
) -> BaseChatModel:
```

### Routing logic

```
user_tier == "paid":
    → Existing logic unchanged (subject-based: math→claude, chemistry→openai)

user_tier == "free":
    attempt 0 → Gemini strong
    attempt 1 → Groq strong (when Gemini fails/rate-limited)
    attempt 2 → Groq fast (last resort)
```

### New configuration

```env
GROQ_API_KEY=gsk_xxxxx
```

```python
# config.py
groq_api_key: str | None = None
```

### New dependency

```
langchain-groq
```

## Service Layer

### New file: `app/services/subscription_service.py`

```
SubscriptionService:

  get_user_tier(user_id, db) -> str
    1. Query Subscription WHERE user_id AND status="active"
    2. If expires_at is non-null and past → update status="expired", return "free"
    3. Return subscription.plan ("free" or "premium")
    4. No record found → auto-create free subscription, return "free"

  check_usage_limit(user_id, db) -> (allowed: bool, remaining: int)
    1. Query UsageRecord WHERE user_id AND date=today
    2. No record → create one, return (True, 20)
    3. solve_count >= 20 → return (False, 0)
    4. Return (True, 20 - solve_count)

  increment_usage(user_id, provider_used, db) -> None
    1. UPSERT UsageRecord: solve_count += 1
    2. Record provider_used
```

### `scan_service.py` changes

```
Current solve flow:
  1. Receive image/text
  2. OCR → analyze → cache lookup → LLM solve

Updated flow:
  1. Receive image/text
  2. user_tier = subscription_service.get_user_tier(user_id)
  3. if tier == "free":
       allowed, remaining = check_usage_limit(user_id)
       if not allowed → raise DailyLimitExceeded(remaining=0)
  4. OCR → analyze → cache lookup → LLM solve
     (select_llm receives user_tier parameter)
  5. On success → increment_usage(user_id, provider_used)
```

### Guest mode

- `solve-guest` endpoint has no user_id → default `tier="free"`, rate-limit by IP (10/day).
- UsageRecord uses `ip_address` field in place of `user_id` for guest scenarios.

### Error responses

| Scenario | HTTP Status | Response |
|----------|-------------|----------|
| Daily limit exceeded | 429 | `{ "error": "daily_limit_exceeded", "remaining": 0, "upgrade_url": "..." }` |
| All free APIs rate-limited | 503 | `{ "error": "service_busy", "retry_after": 60 }` |
| Subscription expired | 200 (degraded) | Auto-routes as free tier, no error |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/subscription/me` | Current user's subscription status + today's usage |
| `GET` | `/api/v1/subscription/usage` | Usage history (by day) |
| `POST` | `/api/v1/admin/subscription/{user_id}` | Admin: manually set user plan (for testing/gifting) |

## File Manifest

### New files

| File | Purpose |
|------|---------|
| `app/models/subscription.py` | Subscription + UsageRecord models |
| `app/schemas/subscription.py` | Request/response schemas |
| `app/services/subscription_service.py` | Tier lookup, rate limiting, usage tracking |
| `app/api/v1/subscription.py` | Subscription API endpoints |
| `alembic/versions/023_add_subscription_and_usage.py` | Database migration |

### Modified files

| File | Change |
|------|--------|
| `app/llm/registry.py` | Add Groq provider, MODEL_CONFIG, user_tier param in select_llm |
| `app/core/config.py` | Add `groq_api_key` |
| `app/services/scan_service.py` | Add tier check and usage tracking to solve flow |
| `app/api/v1/exams.py` | Add IP rate limiting for solve-guest |
| `app/api/v1/router.py` | Register subscription routes |
| `requirements.txt` | Add `langchain-groq` |

## Implementation Order

1. Database migration (models + alembic)
2. Groq integration into registry
3. SubscriptionService
4. scan_service changes
5. API endpoints
6. Tests
