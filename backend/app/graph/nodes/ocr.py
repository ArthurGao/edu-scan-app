from app.graph.state import SolveState
from app.services.ocr_service import OCRService

ocr_service = OCRService()


async def ocr_node(state: SolveState) -> dict:
    """Extract text from image using OCR provider."""
    image_bytes = state.get("image_bytes")
    if not image_bytes:
        return {"ocr_text": "", "ocr_confidence": 0.0, "error": "No image data provided"}

    try:
        text = await ocr_service.extract_text(image_bytes)
        return {"ocr_text": text, "ocr_confidence": 1.0}
    except Exception as e:
        return {"ocr_text": "", "ocr_confidence": 0.0, "error": str(e)}
