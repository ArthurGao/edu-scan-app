from typing import List, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.formula import Formula
from app.schemas.formula import FormulaDetailResponse, FormulaResponse


class FormulaService:
    """Service for formula database operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_formulas(
        self,
        subject: Optional[str] = None,
        category: Optional[str] = None,
        grade_level: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[List[FormulaResponse], int]:
        """
        Get formulas with optional filters.

        Returns:
            Tuple of (formulas list, total count)
        """
        query = select(Formula)
        count_query = select(func.count(Formula.id))

        if subject:
            query = query.where(Formula.subject == subject)
            count_query = count_query.where(Formula.subject == subject)
        if category:
            query = query.where(Formula.category == category)
            count_query = count_query.where(Formula.category == category)
        if grade_level:
            query = query.where(Formula.grade_levels.any(grade_level))
            count_query = count_query.where(Formula.grade_levels.any(grade_level))
        if keyword:
            kw_filter = or_(
                Formula.name.ilike(f"%{keyword}%"),
                Formula.keywords.any(keyword),
            )
            query = query.where(kw_filter)
            count_query = count_query.where(kw_filter)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(Formula.subject, Formula.name)
        query = query.offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        formulas = result.scalars().all()

        items = [
            FormulaResponse(
                id=str(f.id),
                subject=f.subject,
                category=f.category,
                name=f.name,
                latex=f.latex,
                description=f.description,
                grade_levels=f.grade_levels or [],
            )
            for f in formulas
        ]
        return items, total

    async def get_formula_by_id(self, formula_id: int) -> Optional[FormulaDetailResponse]:
        """Get formula with related formulas."""
        result = await self.db.execute(
            select(Formula).where(Formula.id == formula_id)
        )
        formula = result.scalar_one_or_none()
        if not formula:
            return None

        # Get related formulas
        related = []
        if formula.related_ids:
            related_ids = [int(rid) for rid in formula.related_ids]
            rel_result = await self.db.execute(
                select(Formula).where(Formula.id.in_(related_ids))
            )
            rel_formulas = rel_result.scalars().all()
            related = [
                FormulaResponse(
                    id=str(f.id),
                    subject=f.subject,
                    category=f.category,
                    name=f.name,
                    latex=f.latex,
                    description=f.description,
                    grade_levels=f.grade_levels or [],
                )
                for f in rel_formulas
            ]

        return FormulaDetailResponse(
            id=str(formula.id),
            subject=formula.subject,
            category=formula.category,
            name=formula.name,
            latex=formula.latex,
            description=formula.description,
            grade_levels=formula.grade_levels or [],
            keywords=formula.keywords or [],
            related_formulas=related,
        )

    async def find_related_formulas(
        self,
        problem_text: str,
        subject: Optional[str] = None,
    ) -> List[FormulaResponse]:
        """
        Find formulas related to a problem.

        Uses keyword matching and subject filtering.
        """
        # Extract keywords from problem text (simple word tokenization)
        words = set(problem_text.lower().split())
        # Remove common stop words
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "of", "in", "to", "for", "and", "or", "that", "this", "it", "with"}
        keywords = words - stop_words

        query = select(Formula)
        if subject:
            query = query.where(Formula.subject == subject)

        # Search by keyword overlap
        conditions = []
        for kw in list(keywords)[:10]:  # Limit to 10 keywords
            conditions.append(Formula.keywords.any(kw))
            conditions.append(Formula.name.ilike(f"%{kw}%"))

        if conditions:
            query = query.where(or_(*conditions))

        query = query.limit(5)
        result = await self.db.execute(query)
        formulas = result.scalars().all()

        return [
            FormulaResponse(
                id=str(f.id),
                subject=f.subject,
                category=f.category,
                name=f.name,
                latex=f.latex,
                description=f.description,
                grade_levels=f.grade_levels or [],
            )
            for f in formulas
        ]
