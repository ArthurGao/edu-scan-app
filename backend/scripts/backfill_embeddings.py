"""
Backfill embeddings for existing formulas, scan_records, and knowledge_base entries.

Usage (from backend/ directory):
    python -m scripts.backfill_embeddings                        # all tables
    python -m scripts.backfill_embeddings --table formulas       # only formulas
    python -m scripts.backfill_embeddings --table scan_records   # only scan_records
    python -m scripts.backfill_embeddings --table knowledge_base # only knowledge_base
    python -m scripts.backfill_embeddings --batch-size 100       # larger batches
"""

import argparse
import asyncio
import logging

from sqlalchemy import select, update

from app.database import AsyncSessionLocal
from app.llm.embeddings import embed_texts
from app.models.formula import Formula
from app.models.knowledge_base import KnowledgeBase
from app.models.scan_record import ScanRecord

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Text builders
# ──────────────────────────────────────────────

def _formula_text(name: str, description: str | None, keywords: list | None) -> str:
    parts = [name]
    if description:
        parts.append(description)
    if keywords:
        parts.append(f"Keywords: {', '.join(keywords)}")
    return "\n".join(parts)


def _scan_text(ocr_text: str, subject: str | None, knowledge_points: list | None) -> str:
    parts = [ocr_text]
    if subject:
        parts.append(f"Subject: {subject}")
    if knowledge_points:
        parts.append(f"Concepts: {', '.join(knowledge_points)}")
    return "\n".join(parts)


def _kb_text(title: str, content: str, category: str | None) -> str:
    parts = [title]
    if category:
        parts.append(f"Category: {category}")
    parts.append(content)
    return "\n".join(parts)


# ──────────────────────────────────────────────
# Backfill functions
# ──────────────────────────────────────────────

async def backfill_formulas(batch_size: int) -> None:
    log.info("Starting formula embedding backfill...")
    total = 0

    async with AsyncSessionLocal() as db:
        while True:
            result = await db.execute(
                select(Formula.id, Formula.name, Formula.description, Formula.keywords)
                .where(Formula.embedding.is_(None))
                .limit(batch_size)
            )
            rows = result.all()
            if not rows:
                break

            texts = [_formula_text(r.name, r.description, r.keywords) for r in rows]
            vectors = await embed_texts(texts)

            for row, vec in zip(rows, vectors):
                await db.execute(
                    update(Formula).where(Formula.id == row.id).values(embedding=vec)
                )

            await db.commit()
            total += len(rows)
            log.info(f"  formulas: {total} done")

    log.info(f"Formula backfill complete — {total} records updated.")


async def backfill_scan_records(batch_size: int) -> None:
    log.info("Starting scan_record embedding backfill...")
    total = 0

    async with AsyncSessionLocal() as db:
        while True:
            result = await db.execute(
                select(
                    ScanRecord.id,
                    ScanRecord.ocr_text,
                    ScanRecord.subject,
                    ScanRecord.knowledge_points,
                )
                .where(ScanRecord.embedding.is_(None))
                .where(ScanRecord.ocr_text.isnot(None))
                .limit(batch_size)
            )
            rows = result.all()
            if not rows:
                break

            texts = [_scan_text(r.ocr_text, r.subject, r.knowledge_points) for r in rows]
            vectors = await embed_texts(texts)

            for row, vec in zip(rows, vectors):
                await db.execute(
                    update(ScanRecord).where(ScanRecord.id == row.id).values(embedding=vec)
                )

            await db.commit()
            total += len(rows)
            log.info(f"  scan_records: {total} done")

    log.info(f"Scan record backfill complete — {total} records updated.")


async def backfill_knowledge_base(batch_size: int) -> None:
    log.info("Starting knowledge_base embedding backfill...")
    total = 0

    async with AsyncSessionLocal() as db:
        while True:
            result = await db.execute(
                select(
                    KnowledgeBase.id,
                    KnowledgeBase.title,
                    KnowledgeBase.content,
                    KnowledgeBase.category,
                )
                .where(KnowledgeBase.embedding.is_(None))
                .limit(batch_size)
            )
            rows = result.all()
            if not rows:
                break

            texts = [_kb_text(r.title, r.content, r.category) for r in rows]
            vectors = await embed_texts(texts)

            for row, vec in zip(rows, vectors):
                await db.execute(
                    update(KnowledgeBase)
                    .where(KnowledgeBase.id == row.id)
                    .values(embedding=vec)
                )

            await db.commit()
            total += len(rows)
            log.info(f"  knowledge_base: {total} done")

    log.info(f"Knowledge base backfill complete — {total} records updated.")


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────

async def main(table: str, batch_size: int) -> None:
    runners = {
        "formulas": backfill_formulas,
        "scan_records": backfill_scan_records,
        "knowledge_base": backfill_knowledge_base,
    }

    if table == "all":
        for name, fn in runners.items():
            await fn(batch_size)
    elif table in runners:
        await runners[table](batch_size)
    else:
        log.error(f"Unknown table '{table}'. Choose: {list(runners.keys())} or 'all'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill vector embeddings")
    parser.add_argument(
        "--table",
        default="all",
        choices=["all", "formulas", "scan_records", "knowledge_base"],
        help="Which table to backfill (default: all)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        dest="batch_size",
        help="Records per batch (default: 50)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.table, args.batch_size))
