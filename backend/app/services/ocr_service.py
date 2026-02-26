from abc import ABC, abstractmethod
from typing import Optional

from app.config import get_settings

settings = get_settings()


class BaseOCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @abstractmethod
    async def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image bytes."""
        pass


class GoogleOCRProvider(BaseOCRProvider):
    """Google Cloud Vision OCR provider."""

    async def extract_text(self, image_bytes: bytes) -> str:
        # TODO: Implement Google Cloud Vision OCR
        # from google.cloud import vision
        raise NotImplementedError


class BaiduOCRProvider(BaseOCRProvider):
    """Baidu OCR provider (good for Chinese + math formulas)."""

    async def extract_text(self, image_bytes: bytes) -> str:
        # TODO: Implement Baidu OCR API
        raise NotImplementedError


class TesseractOCRProvider(BaseOCRProvider):
    """Local Tesseract OCR (free, offline)."""

    async def extract_text(self, image_bytes: bytes) -> str:
        # TODO: Implement Tesseract OCR
        # import pytesseract
        raise NotImplementedError


class MockOCRProvider(BaseOCRProvider):
    """Mock OCR provider for testing."""

    async def extract_text(self, image_bytes: bytes) -> str:
        return "Find the value of x in the equation 2x + 5 = 15."


class OCRService:
    """
    OCR service with multiple provider support.
    
    Providers:
    - google: Google Cloud Vision (recommended for accuracy)
    - baidu: Baidu OCR (good for Chinese + handwriting)
    - tesseract: Local Tesseract (free, offline)
    - mock: Mock provider for testing
    """

    PROVIDERS = {
        "google": GoogleOCRProvider,
        "baidu": BaiduOCRProvider,
        "tesseract": TesseractOCRProvider,
        "mock": MockOCRProvider,
    }

    def __init__(self, provider: Optional[str] = None):
        provider_name = provider or settings.ocr_provider or "mock"
        provider_class = self.PROVIDERS.get(provider_name, MockOCRProvider)
        self.provider = provider_class()

    async def extract_text(self, image_bytes: bytes) -> str:
        """
        Extract text from image.
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            Extracted text string
        """
        try:
            return await self.provider.extract_text(image_bytes)
        except NotImplementedError:
            # Fallback to mock if provider not implemented
            mock = MockOCRProvider()
            return await mock.extract_text(image_bytes)
