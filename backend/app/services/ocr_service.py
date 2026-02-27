import base64
import io
import logging
from abc import ABC, abstractmethod
from typing import Optional

from PIL import Image, ImageOps

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseOCRProvider(ABC):
    """Abstract base class for OCR providers."""

    @abstractmethod
    async def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image bytes."""
        pass


class GeminiVisionOCRProvider(BaseOCRProvider):
    """Gemini Vision OCR — uses multimodal LLM to extract text from images.

    Advantages over traditional OCR:
    - Excellent at reading math formulas, handwriting, and mixed languages
    - Free tier: 1000 req/day with Flash-Lite
    - No extra SDK needed — uses langchain_google_genai already installed
    """

    async def extract_text(self, image_bytes: bytes) -> str:
        from langchain_core.messages import HumanMessage
        from langchain_google_genai import ChatGoogleGenerativeAI

        api_key = settings.google_api_key
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not set")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            google_api_key=api_key,
            temperature=0.0,
        )

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": (
                        "Extract ALL text from this image exactly as written. "
                        "The image may be rotated or sideways — detect the correct orientation first, then read the text.\n"
                        "For math expressions, use LaTeX notation wrapped in $ delimiters. "
                        "For example: $2x + 5 = 15$, $\\frac{1}{2}$, $x^{2}$.\n"
                        "Preserve the original layout with line breaks.\n"
                        "If there are multiple problems, number them.\n"
                        "Output ONLY the extracted text, nothing else."
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                },
            ]
        )

        result = await llm.ainvoke([message])
        return result.content.strip()


class GoogleOCRProvider(BaseOCRProvider):
    """Google Cloud Vision OCR provider."""

    async def extract_text(self, image_bytes: bytes) -> str:
        raise NotImplementedError


class BaiduOCRProvider(BaseOCRProvider):
    """Baidu OCR provider (good for Chinese + math formulas)."""

    async def extract_text(self, image_bytes: bytes) -> str:
        raise NotImplementedError


class TesseractOCRProvider(BaseOCRProvider):
    """Local Tesseract OCR (free, offline)."""

    async def extract_text(self, image_bytes: bytes) -> str:
        raise NotImplementedError


class MockOCRProvider(BaseOCRProvider):
    """Mock OCR provider for testing."""

    async def extract_text(self, image_bytes: bytes) -> str:
        return "Find the value of x in the equation $2x + 5 = 15$."


def fix_orientation(image_bytes: bytes) -> bytes:
    """Fix image orientation based on EXIF data.

    Phone cameras store pixels in one orientation and use EXIF tags to indicate
    how the image should be displayed. This applies the EXIF rotation so the
    actual pixel data matches the intended display orientation.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img)
        buf = io.BytesIO()
        fmt = img.format or "JPEG"
        img.save(buf, format=fmt)
        return buf.getvalue()
    except Exception:
        # If anything goes wrong, return original bytes
        return image_bytes


class OCRService:
    """
    OCR service with multiple provider support.

    Providers:
    - gemini: Gemini Vision (recommended — free, best for math)
    - google: Google Cloud Vision
    - baidu: Baidu OCR (good for Chinese + handwriting)
    - tesseract: Local Tesseract (free, offline)
    - mock: Mock provider for testing
    """

    PROVIDERS = {
        "gemini": GeminiVisionOCRProvider,
        "google": GoogleOCRProvider,
        "baidu": BaiduOCRProvider,
        "tesseract": TesseractOCRProvider,
        "mock": MockOCRProvider,
    }

    def __init__(self, provider: Optional[str] = None):
        provider_name = provider or settings.ocr_provider or "gemini"
        provider_class = self.PROVIDERS.get(provider_name, GeminiVisionOCRProvider)
        self.provider = provider_class()

    async def extract_text(self, image_bytes: bytes) -> str:
        """Extract text from image (auto-fixes EXIF orientation first)."""
        image_bytes = fix_orientation(image_bytes)
        try:
            return await self.provider.extract_text(image_bytes)
        except NotImplementedError:
            logger.warning("OCR provider not implemented, falling back to Gemini Vision")
            fallback = GeminiVisionOCRProvider()
            return await fallback.extract_text(image_bytes)
