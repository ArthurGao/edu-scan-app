# EduScan

AI-powered homework helper for K12 students. Upload a homework photo, get step-by-step solutions.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python FastAPI + SQLAlchemy 2.0 + LiteLLM |
| Frontend | Next.js 16 + Tailwind CSS + KaTeX |
| Mobile | React Native (Expo 50) + Zustand + React Query |
| Database | PostgreSQL 16 (pgvector) |
| Cache | Redis 7 |
| AI | Claude / GPT-4 / Gemini (via LiteLLM) |

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- (Mobile) Xcode (iOS) / Android Studio (Android), or just use web mode

## Quick Start

### 1. Start Infrastructure

```bash
cd backend
docker-compose up -d postgres redis
```

This starts PostgreSQL (:5432) and Redis (:6379).

### 2. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env   # Then edit .env with your API keys

# Run database migrations
alembic upgrade head

# Start server
uvicorn app.main:app --reload   # http://localhost:8000
```

### 3. Frontend

```bash
cd frontend
npm install

# Configure environment
echo 'NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1' > .env.local

npm run dev   # http://localhost:3000
```

### 4. Mobile

```bash
cd mobile
npm install

# Configure environment
echo 'EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1' > .env

npm run web       # Fastest, no native tooling needed
npm run ios       # Requires Xcode
npm run android   # Requires Android emulator
```

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection, e.g. `postgresql+asyncpg://postgres:postgres@localhost:5432/eduscan` |
| `REDIS_URL` | Yes | Redis connection, e.g. `redis://localhost:6379/0` |
| `JWT_SECRET_KEY` | Yes | Secret for JWT token signing |
| `ANTHROPIC_API_KEY` | Yes* | Claude API key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `GOOGLE_API_KEY` | Yes* | Gemini API key |
| `OCR_PROVIDER` | No | `google` / `baidu` / `tesseract` / `mock` (default: mock) |

*At least one AI provider key is required.

### Frontend (`frontend/.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL (default: `http://localhost:8000/api/v1`) |

### Mobile (`mobile/.env`)

| Variable | Description |
|----------|-------------|
| `EXPO_PUBLIC_API_BASE_URL` | Backend API URL (default: `http://localhost:8000/api/v1`) |

## Project Structure

```
edu-scan-app/
├── backend/           # FastAPI service
│   ├── app/
│   │   ├── api/v1/    # REST endpoints
│   │   ├── services/  # Business logic (AI, OCR, auth)
│   │   ├── models/    # SQLAlchemy ORM models
│   │   ├── schemas/   # Pydantic request/response
│   │   └── core/      # Security, exceptions
│   ├── tests/
│   └── docker-compose.yml
├── frontend/          # Next.js web dashboard
│   └── src/
│       ├── app/       # Pages (home, history, mistakes, formulas)
│       ├── components/ # Sidebar, UploadZone, SolutionDisplay
│       └── lib/       # API client, types
├── mobile/            # React Native (Expo) app
│   └── src/
│       ├── app/       # Screens (auth, main tabs, scan)
│       ├── services/  # API client per domain
│       ├── stores/    # Zustand state
│       └── theme/     # Design tokens
└── docs/              # Design documents
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/login` | JWT login |
| POST | `/api/v1/scan/solve` | Solve problem (auth required) |
| POST | `/api/v1/scan/solve-guest` | Solve problem (guest mode) |
| GET | `/api/v1/scan/stream/{id}` | SSE streaming solution |
| GET | `/api/v1/history` | Scan history |
| GET/POST/PATCH/DELETE | `/api/v1/mistakes` | Mistake book CRUD |
| GET | `/api/v1/formulas` | Formula search |

## Development Commands

### Backend

```bash
pytest                        # Run tests
pytest --cov=app              # Tests with coverage
black . && isort .            # Format code
ruff check .                  # Lint
mypy app                      # Type check
alembic revision --autogenerate -m "msg"  # New migration
```

### Frontend

```bash
npm run build     # Production build
npm run lint      # ESLint
```

### Mobile

```bash
npm run lint        # ESLint
npm run type-check  # TypeScript check
npm run test        # Jest tests
```

## Docker (Full Stack)

```bash
cd backend
docker-compose up -d   # Starts API, PostgreSQL, Redis, MinIO
```

| Service | Port |
|---------|------|
| API | 8000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| MinIO (S3) | 9000 / 9001 (console) |
