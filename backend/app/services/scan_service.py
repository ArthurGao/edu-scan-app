from datetime import datetime
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.scan_record import ScanRecord
from app.models.solution import Solution
from app.schemas.scan import ScanResponse, SolutionResponse, SolutionStep
from app.services.ai_service import AIService
from app.services.ocr_service import OCRService
from app.services.storage_service import StorageService


class ScanService:
    """Service for handling problem scanning and solving."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_service = AIService()
        self.ocr_service = OCRService()
        self.storage_service = StorageService()

    async def scan_and_solve(
        self,
        user_id: int,
        image: UploadFile,
        subject: Optional[str] = None,
        ai_provider: Optional[str] = None,
        grade_level: Optional[str] = None,
    ) -> ScanResponse:
        """
        Process uploaded image and generate solution.
        """
        # 1. Upload image
        image_url = await self.storage_service.upload_image(image)

        # 2. Extract text using OCR
        image.file.seek(0)
        image_bytes = await image.read()
        ocr_text = await self.ocr_service.extract_text(image_bytes)

        # 3. Detect subject if not provided
        if not subject:
            subject = self._detect_subject(ocr_text)

        # 4. Generate solution using AI
        solution_data = await self.ai_service.solve(
            problem_text=ocr_text,
            subject=subject,
            grade_level=grade_level or "middle school",
            provider=ai_provider
        )

        # 5. Save scan record to database
        scan_record = ScanRecord(
            user_id=user_id,
            image_url=image_url,
            ocr_text=ocr_text,
            subject=subject,
        )
        self.db.add(scan_record)
        await self.db.flush() # Get scan_record.id

        # 6. Save solution
        solution = Solution(
            scan_id=scan_record.id,
            ai_provider=ai_provider or "claude",
            model="claude-3-sonnet-20240229", # Simplified
            content=solution_data.explanation or "",
            steps=[step.model_dump() for step in solution_data.steps],
        )
        self.db.add(solution)
        await self.db.commit()
        await self.db.refresh(scan_record)

        return ScanResponse(
            scan_id=str(scan_record.id),
            ocr_text=ocr_text,
            solution=solution_data,
            related_formulas=[],
            created_at=scan_record.created_at
        )

    async def get_scan_result(self, scan_id: int) -> Optional[ScanResponse]:
        """Retrieve a previous scan result."""
        result = await self.db.execute(
            select(ScanRecord)
            .options(selectinload(ScanRecord.solutions))
            .where(ScanRecord.id == scan_id)
        )
        scan_record = result.scalar_one_or_none()
        if not scan_record:
            return None

        solution = scan_record.solutions[0] if scan_record.solutions else None
        if not solution:
            return None

        # Reconstruct SolutionResponse from stored data
        steps = [SolutionStep(**s) for s in (solution.steps or [])]

        solution_response = SolutionResponse(
            question_type=solution.content[:50] if solution.content else "Unknown",
            knowledge_points=[],
            steps=steps,
            final_answer=steps[-1].calculation if steps else "",
            explanation=solution.content,
        )

        return ScanResponse(
            scan_id=str(scan_record.id),
            ocr_text=scan_record.ocr_text or "",
            solution=solution_response,
            related_formulas=[],
            created_at=scan_record.created_at,
        )

    def _detect_subject(self, ocr_text: str) -> str:
        """Auto-detect subject from problem text."""
        text = ocr_text.lower()
        if any(w in text for w in ["x", "y", "solve", "equation", "angle", "triangle"]):
            return "math"
        if any(w in text for w in ["force", "mass", "acceleration", "velocity", "energy"]):
            return "physics"
        if any(w in text for w in ["atom", "molecule", "reaction", "acid", "base"]):
            return "chemistry"
        return "math"
