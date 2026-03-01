from typing import List, Optional

from pydantic import BaseModel


class FormulaResponse(BaseModel):
    id: str
    subject: str
    category: Optional[str]
    name: str
    latex: str
    description: Optional[str]
    grade_levels: List[str]

    class Config:
        from_attributes = True


class FormulaDetailResponse(FormulaResponse):
    keywords: List[str]
    related_formulas: List[FormulaResponse]


class SaveFormulaRequest(BaseModel):
    name: str
    latex: str
    subject: Optional[str] = "math"
    description: Optional[str] = None
