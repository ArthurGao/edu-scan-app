"""
Generate K12 seed problems using Claude and export as Alembic migration 015.

Features:
  - Concurrent topic processing (asyncio semaphore)
  - Incremental progress saved to .progress_015.jsonl after each problem
  - Resume: re-running skips already-completed topics automatically
  - Use --clear-cache to start fresh

Usage (from backend/ directory):
    python -m scripts.generate_seed_problems --export-migration
    python -m scripts.generate_seed_problems --dry-run --subjects math --per-topic 2
    python -m scripts.generate_seed_problems --export-migration --concurrency 8
    python -m scripts.generate_seed_problems --clear-cache   # discard progress and restart
"""

import argparse
import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PROGRESS_FILE = Path(__file__).parent / ".progress_015.jsonl"

# ──────────────────────────────────────────────
# Topic definitions
# ──────────────────────────────────────────────

SEED_TOPICS: dict[str, list[dict]] = {
    "math": [
        {"grade": "grade-7",  "topic": "linear equations",              "difficulty": "easy"},
        {"grade": "grade-7",  "topic": "ratios and proportions",        "difficulty": "easy"},
        {"grade": "grade-8",  "topic": "Pythagorean theorem",           "difficulty": "easy"},
        {"grade": "grade-8",  "topic": "systems of linear equations",   "difficulty": "medium"},
        {"grade": "grade-9",  "topic": "quadratic equations",           "difficulty": "medium"},
        {"grade": "grade-9",  "topic": "factoring polynomials",         "difficulty": "medium"},
        {"grade": "grade-9",  "topic": "circle geometry",               "difficulty": "medium"},
        {"grade": "grade-10", "topic": "trigonometry: sine and cosine", "difficulty": "medium"},
        {"grade": "grade-10", "topic": "sequences and series",          "difficulty": "medium"},
        {"grade": "grade-11", "topic": "logarithms",                    "difficulty": "hard"},
        {"grade": "grade-11", "topic": "differentiation",               "difficulty": "hard"},
        {"grade": "grade-11", "topic": "integration",                   "difficulty": "hard"},
        {"grade": "grade-11", "topic": "vectors",                       "difficulty": "hard"},
    ],
    "physics": [
        {"grade": "grade-9",  "topic": "kinematics: SUVAT equations",  "difficulty": "easy"},
        {"grade": "grade-9",  "topic": "Newton's laws of motion",      "difficulty": "easy"},
        {"grade": "grade-10", "topic": "work, energy, and power",      "difficulty": "medium"},
        {"grade": "grade-10", "topic": "momentum and collisions",      "difficulty": "medium"},
        {"grade": "grade-10", "topic": "Ohm's law and circuits",       "difficulty": "medium"},
        {"grade": "grade-11", "topic": "circular motion",              "difficulty": "hard"},
        {"grade": "grade-11", "topic": "refraction and Snell's law",   "difficulty": "medium"},
        {"grade": "grade-11", "topic": "ideal gas law",                "difficulty": "medium"},
        {"grade": "grade-11", "topic": "electromagnetic induction",    "difficulty": "hard"},
    ],
    "chemistry": [
        {"grade": "grade-9",  "topic": "balancing chemical equations", "difficulty": "easy"},
        {"grade": "grade-9",  "topic": "mole calculations",            "difficulty": "medium"},
        {"grade": "grade-10", "topic": "acids and bases: pH",          "difficulty": "medium"},
        {"grade": "grade-10", "topic": "stoichiometry and yield",      "difficulty": "medium"},
        {"grade": "grade-11", "topic": "electrochemistry: redox",      "difficulty": "hard"},
        {"grade": "grade-11", "topic": "enthalpy and Hess's law",      "difficulty": "hard"},
        {"grade": "grade-11", "topic": "chemical equilibrium",         "difficulty": "hard"},
    ],
}

# ──────────────────────────────────────────────
# Prompts
# ──────────────────────────────────────────────

GENERATE_PROBLEMS_PROMPT = """\
Generate {n} distinct {subject} exam problems for {grade} students on the topic: "{topic}".
Difficulty level: {difficulty}.

Requirements:
- Problems should be typical exam/textbook questions (include specific numbers)
- Each problem must be self-contained (all needed info is in the problem text)
- Vary the style: calculation, word problem, multi-step
- Do NOT include the answer

Respond ONLY in valid JSON:
{{
  "problems": [
    {{
      "ocr_text": "Full problem text exactly as a student would see it",
      "problem_type": "calculation|word_problem|proof|multi_step",
      "knowledge_points": ["concept1", "concept2"]
    }}
  ]
}}"""

SOLVE_PROBLEM_PROMPT = """\
You are an experienced {subject} teacher. Solve this {grade} exam problem step by step.

Problem:
{problem}

Respond ONLY in valid JSON:
{{
  "question_type": "short description of problem type",
  "knowledge_points": ["concept1", "concept2"],
  "steps": [
    {{
      "step": 1,
      "description": "what this step does",
      "formula": "LaTeX formula if applicable (no $ delimiters here)",
      "calculation": "the actual calculation with $inline math$"
    }}
  ],
  "final_answer": "the final answer with units",
  "explanation": "one-sentence summary of the method used",
  "tips": "key tip for solving similar problems"
}}"""

# ──────────────────────────────────────────────
# LLM helpers
# ──────────────────────────────────────────────

def _fix_latex_escapes(text: str) -> str:
    # Fix unescaped LaTeX backslashes in JSON strings.
    # Claude sometimes returns \frac, \sqrt etc. as single backslashes,
    # which are invalid JSON escape sequences. This regex doubles them.
    # Valid single-char JSON escapes (\", \\, \/, \b, \f, \n, \r, \t) are left untouched.
    # \uXXXX is only left untouched when followed by exactly 4 hex digits —
    # LaTeX commands like \underline, \underbrace also start with \u but are NOT valid
    # JSON unicode escapes and must be doubled.
    return re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', text)


async def _llm_json(prompt: str, sem: asyncio.Semaphore) -> dict | None:
    from langchain_core.messages import HumanMessage
    from app.llm.registry import get_llm

    llm = get_llm("fast", "claude")
    async with sem:
        try:
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            text = response.content.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            text = text.strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return json.loads(_fix_latex_escapes(text))
        except Exception as e:
            log.warning(f"LLM call failed: {e}")
            return None


# ──────────────────────────────────────────────
# Progress file (incremental save)
# ──────────────────────────────────────────────

def load_progress() -> tuple[list[dict], set[str]]:
    """Load saved records and return (records, set of completed topic keys)."""
    if not PROGRESS_FILE.exists():
        return [], set()

    records = []
    for line in PROGRESS_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    # A topic is "done" if it has any saved records
    done = {f"{r['subject']}|{r['grade']}|{r['topic']}" for r in records}
    log.info(f"Loaded {len(records)} records from progress file ({len(done)} topics done)")
    return records, done


def append_record(record: dict) -> None:
    """Append one completed record to the progress file immediately."""
    with PROGRESS_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────
# Concurrent topic processing
# ──────────────────────────────────────────────

async def process_topic(
    sem: asyncio.Semaphore,
    subject: str,
    grade: str,
    topic: str,
    difficulty: str,
    per_topic: int,
    dry_run: bool,
) -> list[dict]:
    """Generate + solve all problems for one topic. Returns completed records."""
    log.info(f"  → [{grade}] {topic} ({difficulty})")

    prompt = GENERATE_PROBLEMS_PROMPT.format(
        n=per_topic, subject=subject, grade=grade, topic=topic, difficulty=difficulty
    )
    data = await _llm_json(prompt, sem)
    problems = data.get("problems", []) if data else []

    if not problems:
        log.warning(f"  ⚠ No problems generated for '{topic}'")
        return []

    async def solve_one(problem: dict) -> dict | None:
        ocr_text = problem.get("ocr_text", "").strip()
        if not ocr_text:
            return None
        solve_prompt = SOLVE_PROBLEM_PROMPT.format(
            subject=subject, grade=grade, problem=ocr_text
        )
        solution = await _llm_json(solve_prompt, sem)
        if not solution:
            log.warning(f"    ⚠ Solve failed: {ocr_text[:60]}")
            return None

        record = {
            "subject": subject,
            "grade": grade,
            "topic": topic,
            "difficulty": difficulty,
            "ocr_text": ocr_text,
            "problem_type": problem.get("problem_type", "calculation"),
            "knowledge_points": problem.get("knowledge_points", []),
            "solution": solution,
        }
        log.info(f"    ✓ [{subject}/{grade}] {ocr_text[:55]}... → {str(solution.get('final_answer', '?'))[:40]}")
        if not dry_run:
            append_record(record)
        return record

    results = await asyncio.gather(*[solve_one(p) for p in problems])
    return [r for r in results if r is not None]


async def collect_all(
    subjects: list[str],
    per_topic: int,
    concurrency: int,
    dry_run: bool,
    existing_records: list[dict],
    done_topics: set[str],
) -> list[dict]:
    sem = asyncio.Semaphore(concurrency)
    tasks = []

    for subject in subjects:
        for topic_def in SEED_TOPICS.get(subject, []):
            grade = topic_def["grade"]
            topic = topic_def["topic"]
            difficulty = topic_def["difficulty"]
            key = f"{subject}|{grade}|{topic}"

            if key in done_topics:
                log.info(f"  ⏭ Skipping (already done): [{grade}] {topic}")
                continue

            tasks.append(process_topic(sem, subject, grade, topic, difficulty, per_topic, dry_run))

    log.info(f"\nRunning {len(tasks)} topics concurrently (max {concurrency} at a time)...")
    results = await asyncio.gather(*tasks)

    new_records = [rec for topic_records in results for rec in topic_records]
    all_records = existing_records + new_records
    log.info(f"\nDone — {len(new_records)} new records, {len(all_records)} total")
    return all_records


# ──────────────────────────────────────────────
# Migration export
# ──────────────────────────────────────────────

MIGRATION_TEMPLATE = '''\
"""Seed K12 practice problems for RAG warm-up (Claude-generated)

Revision ID: 015_seed_problems
Revises: 014_seed_knowledge_base
Create Date: {date}

Auto-generated by: python -m scripts.generate_seed_problems --export-migration
DO NOT EDIT the SEED_RECORDS list manually — re-run the script to regenerate.
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015_seed_problems"
down_revision: Union[str, None] = "014_seed_knowledge_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# fmt: off
SEED_RECORDS = {records_json}
# fmt: on


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        INSERT INTO users (email, nickname, is_active, created_at, updated_at)
        VALUES (\'seed@eduscan.internal\', \'Seed Data\', false, NOW(), NOW())
        ON CONFLICT (email) DO NOTHING
    """))

    seed_user_id = conn.execute(
        sa.text("SELECT id FROM users WHERE email = \'seed@eduscan.internal\'")
    ).scalar()

    for rec in SEED_RECORDS:
        solution = rec["solution"]

        scan_id = conn.execute(
            sa.text("""
                INSERT INTO scan_records
                    (user_id, ocr_text, subject, difficulty, problem_type, knowledge_points, created_at)
                VALUES
                    (:user_id, :ocr_text, :subject, :difficulty, :problem_type,
                     :knowledge_points::jsonb, NOW())
                RETURNING id
            """),
            {{
                "user_id": seed_user_id,
                "ocr_text": rec["ocr_text"],
                "subject": rec["subject"],
                "difficulty": rec["difficulty"],
                "problem_type": rec["problem_type"],
                "knowledge_points": json.dumps(rec["knowledge_points"]),
            }},
        ).scalar()

        conn.execute(
            sa.text("""
                INSERT INTO solutions
                    (scan_id, ai_provider, model, content, steps, final_answer,
                     knowledge_points, quality_score, attempt_number,
                     verification_status, created_at)
                VALUES
                    (:scan_id, \'claude\', \'seed-data\', :content, :steps::jsonb,
                     :final_answer, :knowledge_points::jsonb, 0.90, 1,
                     \'verified\', NOW())
            """),
            {{
                "scan_id": scan_id,
                "content": json.dumps(solution),
                "steps": json.dumps(solution.get("steps", [])),
                "final_answer": solution.get("final_answer", ""),
                "knowledge_points": json.dumps(solution.get("knowledge_points", rec["knowledge_points"])),
            }},
        )


def downgrade() -> None:
    op.execute("""
        DELETE FROM users WHERE email = \'seed@eduscan.internal\'
    """)
'''


def write_migration(records: list[dict], output_dir: Path) -> Path:
    records_json = json.dumps(records, ensure_ascii=False, indent=2)
    indented = "\n".join("    " + line for line in records_json.splitlines())
    indented = "[\n" + indented + "\n]"
    content = MIGRATION_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d"),
        records_json=indented,
    )
    out_path = output_dir / "015_seed_problems.py"
    out_path.write_text(content, encoding="utf-8")
    return out_path


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

async def main(
    subjects: list[str],
    per_topic: int,
    mode: str,
    concurrency: int,
    migration_dir: Path,
    clear_cache: bool,
) -> None:
    if clear_cache and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        log.info(f"Progress cache cleared: {PROGRESS_FILE}")

    existing_records, done_topics = ([], set()) if mode == "dry-run" else load_progress()

    all_records = await collect_all(
        subjects, per_topic, concurrency, mode == "dry-run", existing_records, done_topics
    )

    if mode == "dry-run":
        for r in all_records:
            print(f"\n[{r['subject']} {r['grade']}] {r['ocr_text'][:100]}")
            print(f"  → {r['solution'].get('final_answer', '?')}")
        return

    if not all_records:
        log.error("No records to write, aborting.")
        return

    path = write_migration(all_records, migration_dir)
    log.info(f"\n✓ Migration written: {path}  ({len(all_records)} records)")
    log.info(f"  Progress cache:     {PROGRESS_FILE}  (safe to delete after committing)")
    log.info("Next steps:")
    log.info("  git add alembic/versions/015_seed_problems.py && git commit")
    log.info("  Deploy command: alembic upgrade head && python -m scripts.backfill_embeddings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate K12 seed problems via Claude → migration 015")
    parser.add_argument("--export-migration", action="store_const", const="export-migration", dest="mode",
                        help="Write alembic/versions/015_seed_problems.py (default)")
    parser.add_argument("--dry-run", action="store_const", const="dry-run", dest="mode",
                        help="Print without saving")
    parser.add_argument("--subjects", nargs="+", default=["math", "physics", "chemistry"],
                        choices=["math", "physics", "chemistry"])
    parser.add_argument("--per-topic", type=int, default=5, dest="per_topic",
                        help="Problems per topic (default: 5)")
    parser.add_argument("--concurrency", type=int, default=5,
                        help="Max concurrent LLM calls (default: 5)")
    parser.add_argument("--migration-dir", type=Path, dest="migration_dir",
                        default=Path(__file__).parent.parent / "alembic" / "versions")
    parser.add_argument("--clear-cache", action="store_true", dest="clear_cache",
                        help="Delete progress file and start fresh")
    args = parser.parse_args()

    mode = args.mode or "export-migration"
    asyncio.run(main(args.subjects, args.per_topic, mode, args.concurrency, args.migration_dir, args.clear_cache))
