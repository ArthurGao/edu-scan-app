# EduScan - Intelligent Learning Assistant

## 1. Project Overview

### 1.1 Product Vision
An AI-powered mobile application for K12 students that scans homework problems, provides step-by-step solutions, and suggests related formulas and concepts.

### 1.2 Core Features
- **Problem Scanning**: Capture problems via camera or photo library
- **AI-Powered Solutions**: Multi-model support (Claude/GPT/Gemini)
- **Formula Association**: Automatically link related formulas and theorems
- **Learning History**: Track solved problems and study progress
- **Mistake Book**: Save difficult problems for review

### 1.3 Target Users
- Primary school students (Grades 3-6)
- Middle school students
- High school students
- Parents assisting with homework

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Native Mobile App                       │
│                        (TypeScript)                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  Camera  │  │   OCR    │  │ Solution │  │    History     │  │
│  │  Module  │  │  Preview │  │  Display │  │    Module      │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ REST API / WebSocket (SSE)
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway (Nginx)                         │
│           Rate Limiting │ SSL │ Load Balancing                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Python FastAPI Backend                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │    Auth     │  │    Scan     │  │      AI Gateway         │  │
│  │   Service   │  │   Service   │  │       (LiteLLM)         │  │
│  │             │  │             │  │  ┌─────┬─────┬───────┐  │  │
│  │ - JWT       │  │ - OCR       │  │  │Claude│ GPT │Gemini │  │  │
│  │ - Users     │  │ - Image     │  │  └─────┴─────┴───────┘  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  History    │  │  Formula    │  │       Mistake           │  │
│  │  Service    │  │  Service    │  │       Service           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌────────────┐      ┌────────────┐      ┌────────────┐
   │ PostgreSQL │      │   Redis    │      │  S3/MinIO  │
   │  - Users   │      │  - Cache   │      │  - Images  │
   │  - Records │      │  - Session │      │  - Assets  │
   │  - Formulas│      │  - Rate    │      │            │
   └────────────┘      └────────────┘      └────────────┘
```

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI | Async REST API, WebSocket support |
| Language | Python 3.11+ | AI ecosystem, rapid development |
| ORM | SQLAlchemy 2.0 | Database operations |
| Migration | Alembic | Database schema versioning |
| Validation | Pydantic v2 | Request/Response validation |
| Auth | python-jose + passlib | JWT authentication |
| LLM | LiteLLM | Unified interface for multiple AI models |
| Cache | Redis + aioredis | Session, rate limiting, caching |
| Task Queue | Celery (optional) | Background jobs |

### 3.2 Mobile (React Native)

| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | React Native 0.73+ | Cross-platform mobile |
| Language | TypeScript | Type safety |
| Navigation | React Navigation 6 | Screen navigation |
| State | Zustand | Lightweight state management |
| API Client | Axios + React Query | HTTP requests, caching |
| Camera | react-native-camera | Photo capture |
| Math Render | react-native-mathjax | LaTeX formula display |
| Storage | MMKV | Fast local storage |

### 3.3 Infrastructure

| Component | Technology | Purpose |
|-----------|------------|---------|
| Database | PostgreSQL 15+ | Primary data store |
| Cache | Redis 7+ | Caching, sessions |
| Storage | AWS S3 / MinIO | Image storage |
| Container | Docker + Compose | Local development |
| CI/CD | GitHub Actions | Automated deployment |

---

## 4. Database Design

### 4.1 Entity Relationship Diagram

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    users     │       │ scan_records │       │  solutions   │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │──┐    │ id (PK)      │──┐    │ id (PK)      │
│ email        │  │    │ user_id (FK) │  │    │ scan_id (FK) │
│ phone        │  └───<│ image_url    │  └───<│ ai_provider  │
│ password_hash│       │ ocr_text     │       │ model        │
│ nickname     │       │ subject      │       │ content      │
│ avatar_url   │       │ difficulty   │       │ steps (JSON) │
│ grade_level  │       │ created_at   │       │ formulas[]   │
│ created_at   │       └──────────────┘       │ rating       │
│ updated_at   │                              │ created_at   │
└──────────────┘                              └──────────────┘

┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│   formulas   │       │ mistake_book │       │learning_stats│
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │       │ id (PK)      │       │ id (PK)      │
│ subject      │       │ user_id (FK) │       │ user_id (FK) │
│ category     │       │ scan_id (FK) │       │ stat_date    │
│ name         │       │ notes        │       │ subject      │
│ latex        │       │ mastered     │       │ scan_count   │
│ description  │       │ review_count │       │ study_minutes│
│ grade_levels │       │ next_review  │       │ created_at   │
│ keywords[]   │       │ created_at   │       └──────────────┘
│ related_ids[]│       └──────────────┘
└──────────────┘
```

### 4.2 Table Definitions

See `backend/alembic/versions/001_initial_schema.py` for complete migration.

---

## 5. API Design

### 5.1 Authentication

```yaml
POST /api/v1/auth/register
  Request: { email, password, nickname?, grade_level? }
  Response: { user_id, access_token, refresh_token }

POST /api/v1/auth/login
  Request: { email, password }
  Response: { access_token, refresh_token, expires_in }

POST /api/v1/auth/refresh
  Request: { refresh_token }
  Response: { access_token, refresh_token }

GET /api/v1/auth/me
  Headers: Authorization: Bearer {token}
  Response: { user profile }
```

### 5.2 Scan & Solve

```yaml
POST /api/v1/scan/solve
  Headers: Authorization: Bearer {token}
  Request (multipart):
    - image: file (required)
    - subject: string (optional, auto-detect)
    - ai_provider: enum [claude, gpt, gemini] (optional, default: claude)
    - grade_level: string (optional)
  Response:
    - scan_id: string
    - ocr_text: string
    - solution:
        - question_type: string
        - knowledge_points: string[]
        - steps: Step[]
        - final_answer: string
        - explanation: string
    - related_formulas: Formula[]

GET /api/v1/scan/stream/{scan_id}
  Response: Server-Sent Events
    - event: ocr_complete
    - event: solution_chunk
    - event: complete
```

### 5.3 History & Mistakes

```yaml
GET /api/v1/history
  Query: subject?, start_date?, end_date?, page?, limit?
  Response: { items: ScanRecord[], total, page, pages }

POST /api/v1/mistakes
  Request: { scan_id, notes? }
  Response: { mistake_id }

GET /api/v1/mistakes
  Query: subject?, mastered?, page?, limit?
  Response: { items: Mistake[], total }

PATCH /api/v1/mistakes/{id}
  Request: { mastered?, notes? }
  Response: { updated mistake }
```

### 5.4 Formulas

```yaml
GET /api/v1/formulas
  Query: subject?, category?, grade_level?, keyword?, page?, limit?
  Response: { items: Formula[], total }

GET /api/v1/formulas/{id}
  Response: { formula with related formulas }
```

---

## 6. LLM Integration

### 6.1 LiteLLM Unified Interface

```python
# All models use the same interface
from litellm import completion

response = completion(
    model="claude-sonnet-4-20250514",  # or "gpt-4o", "gemini/gemini-1.5-pro"
    messages=[{"role": "user", "content": prompt}],
    stream=True
)
```

### 6.2 Model Selection Strategy

| Subject | Primary Model | Fallback |
|---------|--------------|----------|
| Math | Claude | GPT-4o |
| Physics | Claude | GPT-4o |
| Chemistry | GPT-4o | Claude |
| Biology | GPT-4o | Gemini |
| Default | Claude | GPT-4o |

### 6.3 Prompt Template Structure

```
System: You are an experienced {subject} teacher helping a {grade_level} student.

Task: Solve the following problem step by step.

Requirements:
1. Identify the problem type and key concepts
2. List required formulas (in LaTeX format)
3. Show detailed solution steps
4. Provide the final answer
5. Give study tips for similar problems

Problem: {ocr_text}

Output Format: JSON
{
  "question_type": "...",
  "knowledge_points": [...],
  "formulas": [{"name": "...", "latex": "..."}],
  "steps": [{"step": 1, "description": "...", "calculation": "..."}],
  "final_answer": "...",
  "tips": "..."
}
```

---

## 7. Project Structure

### 7.1 Backend Structure

```
backend/
├── alembic/                    # Database migrations
│   ├── versions/
│   │   └── 001_initial_schema.py
│   ├── env.py
│   └── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Settings and configuration
│   ├── database.py             # Database connection
│   ├── dependencies.py         # Dependency injection
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py       # API router aggregation
│   │   │   ├── auth.py         # Auth endpoints
│   │   │   ├── scan.py         # Scan endpoints
│   │   │   ├── history.py      # History endpoints
│   │   │   ├── mistakes.py     # Mistake book endpoints
│   │   │   └── formulas.py     # Formula endpoints
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── scan_record.py
│   │   ├── solution.py
│   │   ├── formula.py
│   │   ├── mistake_book.py
│   │   └── learning_stats.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── scan.py
│   │   ├── solution.py
│   │   ├── formula.py
│   │   └── common.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── scan_service.py
│   │   ├── ai_service.py
│   │   ├── ocr_service.py
│   │   ├── formula_service.py
│   │   └── storage_service.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT, password hashing
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── middleware.py       # Custom middleware
│   └── utils/
│       ├── __init__.py
│       └── prompt_templates.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_scan.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

### 7.2 Mobile Structure

```
mobile/
├── src/
│   ├── app/
│   │   ├── _layout.tsx         # Root layout (Expo Router)
│   │   ├── index.tsx           # Entry redirect
│   │   ├── (auth)/
│   │   │   ├── login.tsx
│   │   │   ├── register.tsx
│   │   │   └── _layout.tsx
│   │   ├── (main)/
│   │   │   ├── _layout.tsx     # Tab navigator
│   │   │   ├── home.tsx
│   │   │   ├── history.tsx
│   │   │   ├── formulas.tsx
│   │   │   ├── mistakes.tsx
│   │   │   └── profile.tsx
│   │   └── (scan)/
│   │       ├── camera.tsx
│   │       ├── preview.tsx
│   │       └── solution.tsx
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Card.tsx
│   │   │   └── Loading.tsx
│   │   ├── scan/
│   │   │   ├── CameraView.tsx
│   │   │   ├── ImageCropper.tsx
│   │   │   └── SolutionCard.tsx
│   │   ├── formula/
│   │   │   ├── FormulaCard.tsx
│   │   │   └── MathRenderer.tsx
│   │   └── history/
│   │       └── HistoryItem.tsx
│   ├── services/
│   │   ├── api.ts              # Axios instance
│   │   ├── auth.ts             # Auth API calls
│   │   ├── scan.ts             # Scan API calls
│   │   ├── history.ts
│   │   └── formulas.ts
│   ├── stores/
│   │   ├── authStore.ts        # Zustand auth store
│   │   ├── scanStore.ts
│   │   └── settingsStore.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useScan.ts
│   │   └── useFormulas.ts
│   ├── types/
│   │   ├── auth.ts
│   │   ├── scan.ts
│   │   ├── formula.ts
│   │   └── api.ts
│   ├── utils/
│   │   ├── storage.ts
│   │   ├── constants.ts
│   │   └── helpers.ts
│   └── theme/
│       ├── colors.ts
│       ├── typography.ts
│       └── spacing.ts
├── assets/
│   ├── images/
│   └── fonts/
├── app.json
├── package.json
├── tsconfig.json
├── babel.config.js
├── .env.example
└── README.md
```

---

## 8. Development Setup

### 8.1 Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose

### 8.2 Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys

# Start dependencies
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload
```

### 8.3 Mobile Setup

```bash
cd mobile
npm install
cp .env.example .env
# Edit .env with backend URL

# iOS
npx expo run:ios

# Android
npx expo run:android
```

---

## 9. Deployment

### 9.1 Docker Compose (Development)

```yaml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    
  postgres:
    image: postgres:15-alpine
    volumes: [postgres_data:/var/lib/postgresql/data]
    
  redis:
    image: redis:7-alpine
```

### 9.2 Production Deployment

- **Backend**: AWS ECS / Google Cloud Run / Railway
- **Database**: AWS RDS / Supabase / Neon
- **Cache**: AWS ElastiCache / Upstash Redis
- **Storage**: AWS S3 / Cloudflare R2
- **Mobile**: App Store / Google Play

---

## 10. Cost Estimation (10K Users/Month)

| Service | Estimated Cost |
|---------|---------------|
| Cloud Server | $50-100 |
| PostgreSQL (managed) | $25-50 |
| Redis (managed) | $10-20 |
| AI API (LiteLLM) | $200-500 |
| S3 Storage | $10-20 |
| **Total** | **$295-690** |

---

## 11. Development Roadmap

### Phase 1: MVP (4 weeks)
- [ ] Backend project setup
- [ ] User authentication
- [ ] Basic scan & solve flow
- [ ] Claude integration
- [ ] Mobile basic UI

### Phase 2: Core Features (4 weeks)
- [ ] Multi-model support (GPT, Gemini)
- [ ] Formula database
- [ ] History & mistake book
- [ ] Streaming responses
- [ ] OCR optimization

### Phase 3: Enhancement (4 weeks)
- [ ] Learning statistics
- [ ] Offline support
- [ ] Push notifications
- [ ] Performance optimization

### Phase 4: Launch (2 weeks)
- [ ] Testing & QA
- [ ] App Store submission
- [ ] Production deployment

---

*Document Version: 2.0*
*Last Updated: January 2025*
