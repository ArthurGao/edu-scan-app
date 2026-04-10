# EduScan Admin Panel

Admin dashboard for managing users, exam papers, and practice questions.

## Prerequisites

- Node.js 18+
- Backend running at `http://localhost:8000` (see `../backend/`)
- Clerk account (shares keys with frontend)

## Setup

```bash
# Install dependencies
npm install

# Copy environment variables from frontend (same Clerk keys)
cp ../frontend/.env.local .env.local

# Start dev server on port 3001
npm run dev
```

Open [http://localhost:3001](http://localhost:3001).

## Pages

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Stats overview, tier distribution, daily activity |
| Users | `/users` | Search, filter by role, enable/disable, promote/demote |
| Exam Papers | `/exams` | Upload PDF, crawl NZQA, list papers, delete |
| Question Bank | `/questions` | Browse questions by exam/type, view images + answers |

## Upload Exam PDF

1. Go to **Exam Papers** → click **Upload PDF**
2. Fill in title, year, subject, language
3. Select the exam PDF (required) and marking schedule PDF (optional)
4. Click **Upload & Parse** — AI extracts questions and answers automatically

## Crawl NZQA

1. Go to **Exam Papers** → click **Crawl NZQA**
2. Paste the NZQA past exams page URL, e.g.:
   ```
   https://www2.nzqa.govt.nz/ncea/subjects/past-exams-and-exemplars/litnum/32406/
   ```
3. Click **Start Crawl** — discovers, downloads, and parses all exam PDFs on the page

## Tech Stack

- Next.js 16 (App Router)
- React 19
- Tailwind CSS v4
- Clerk (authentication)
- Axios (API client)
