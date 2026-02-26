# EduScan - Intelligent Learning Assistant

AI-powered educational problem solver backend and mobile application.

## Tech Stack

### Backend
- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLAlchemy 2.0
- **Cache**: Redis
- **AI**: LiteLLM (Claude/GPT/Gemini)
- **Migration**: Alembic

### Mobile
- **Framework**: React Native (Expo)
- **Language**: TypeScript
- **Navigation**: Expo Router

---

## 1. Prerequisites

- **Node.js**: v18+ (Verified v25.4.0)
- **Python**: 3.11+ (Verified v3.13.5)
- **Anaconda/Miniconda**
- **Docker & Docker Compose**
- **API Keys**: Anthropic, OpenAI, or Google (Gemini)

---

## 2. Backend Setup & Run

### Step 1: Clone and Setup Environment
```bash
cd backend
conda create -n edu-scan-app python=3.13 -y
conda activate edu-scan-app
conda env list
### Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env and add your AI provider API keys
```

### Step 3: Start Infrastructure
```bash
docker-compose up -d postgres redis
```

### Step 4: Run Migrations
```bash
alembic upgrade head
```

### Step 5: Start Development Server
```bash
uvicorn app.main:app --reload
```
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 3. Mobile App Setup & Run

### Step 1: Install Dependencies
```bash
cd mobile
npm install
```

### Step 2: Configure Environment
```bash
cp .env.example .env
# Default points to http://localhost:8000/api/v1
```

### Step 3: Run the App
- **Web Browser (Recommended for macOS speed)**:
  ```bash
  npm run web
  ```
- **iOS Simulator (Requires Xcode)**:
  ```bash
  npm run ios
  ```
- **Android Emulator (Requires Android Studio)**:
  ```bash
  npm run android
  ```
- **Physical Device**:
  1. Download **Expo Go** app.
  2. Run `npx expo start`.
  3. Scan the QR code.

---

## 4. Database Management (Alembic)

This project uses **Alembic** to manage schema changes.

### Standard Workflow
1. **Modify Models**: Update files in `app/models/`.
2. **Generate Migration**:
   ```bash
   alembic revision --autogenerate -m "description of change"
   ```
3. **Review**: Check `alembic/versions/` for correctness.
4. **Apply**: `alembic upgrade head`.

### Manual Database Creation (Docker)
If you need to manually create the database or user in an existing container:
```bash
# Enter container
docker exec -it backend-postgres-1 psql -U postgres

# Run SQL
CREATE DATABASE eduscan;
GRANT ALL PRIVILEGES ON DATABASE eduscan TO postgres;
\q
```

### Common Commands
| Command | Description |
| :--- | :--- |
| `alembic upgrade head` | Update to latest version. |
| `alembic downgrade -1` | Undo last migration. |
| `alembic history` | Show migration versions. |

---

## 5. API Reference Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/scan/solve | Upload problem image & solve |
| GET | /api/v1/scan/stream/{id}| Stream solution (SSE) |
| GET | /api/v1/history | Get scan history |
| POST | /api/v1/mistakes | Add to mistake book |
| GET | /api/v1/formulas | Search formulas |

---

## 6. Development Commands

```bash
# Run tests
pytest

# Code Formatting
black .
isort .

# Linting
ruff check .
```
