from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_or_guest_user, get_db
from app.models.user import User
from app.schemas.common import PaginatedResponse
from app.schemas.formula import FormulaDetailResponse, FormulaResponse, SaveFormulaRequest
from app.services.formula_service import FormulaService

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def get_formulas(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    category: Optional[str] = Query(None, description="Filter by category"),
    grade_level: Optional[str] = Query(None, description="Filter by grade level"),
    keyword: Optional[str] = Query(None, description="Search keyword"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """Get formulas with optional filters and search."""
    service = FormulaService(db)
    items, total = await service.get_formulas(
        subject, category, grade_level, keyword, page, limit
    )
    pages = (total + limit - 1) // limit if total > 0 else 1
    return PaginatedResponse(
        items=items, total=total, page=page, pages=pages, limit=limit
    )


@router.post("", response_model=FormulaResponse, status_code=status.HTTP_201_CREATED)
async def save_formula(
    request: SaveFormulaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_or_guest_user),
):
    """Save a formula to the library."""
    service = FormulaService(db)
    return await service.save_formula(
        name=request.name,
        latex=request.latex,
        subject=request.subject or "math",
        description=request.description,
    )


@router.get("/{formula_id}", response_model=FormulaDetailResponse)
async def get_formula(formula_id: int, db: AsyncSession = Depends(get_db)):
    """Get formula details with related formulas."""
    service = FormulaService(db)
    result = await service.get_formula_by_id(formula_id)
    if not result:
        raise HTTPException(status_code=404, detail="Formula not found")
    return result
