"""PDF parsing service: PyMuPDF for text/image extraction, AI for question splitting."""

import json
import logging
import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm.registry import get_llm

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ParsedSubQuestion:
    question_number: str  # "1", "2", etc.
    sub_question: str  # "a", "b", "c", etc.
    text: str
    question_type: str = ""  # "numeric", "multichoice", "explanation"
    has_image: bool = False
    image_bytes: bytes | None = None
    order_index: int = 0


@dataclass
class ParsedExam:
    title: str
    raw_text: str
    questions: list[ParsedSubQuestion] = field(default_factory=list)


@dataclass
class ScheduleAnswer:
    question_number: str
    sub_question: str
    correct_answer: str
    accepted_answers: list[str] = field(default_factory=list)
    explanation: str = ""
    question_type: str = ""
    marks: str = ""  # "A" or "H"
    outcome: int | None = None


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

EXAM_PARSE_SYSTEM = """You are an exam paper parser. Given the extracted text of an exam paper,
split it into individual sub-questions and return structured JSON.

Rules:
- Each main question (e.g. "Question 1", "QUESTION ONE") contains multiple sub-questions (a), (b), (c), etc.
- Include the context/preamble text that precedes sub-question (a) as part of (a)'s text, since students need that context.
- For sub-questions after (a), include any relevant context text that appears between it and the previous sub-question.
- Skip page numbers, headers, footers, and instructions (e.g. "Check that this booklet has pages 2-27").
- Classify each sub-question as "numeric", "multichoice", or "explanation":
  - numeric: asks for a number, measurement, or calculation
  - multichoice: asks to tick/circle/select from options
  - explanation: asks to explain, agree/disagree, or justify with reasoning
- Use simple numbering for question_number: "1", "2", "3" (not "ONE", "TWO")

- For multichoice questions, extract the options as a list of strings in order.
- For non-multichoice questions, omit the "options" field or set it to null.

Return ONLY a JSON array, no markdown, no explanation:
[
  {
    "question_number": "1",
    "sub_question": "a",
    "question_text": "full text of the sub-question including any preamble context",
    "question_type": "multichoice",
    "options": ["option 1 text", "option 2 text", "option 3 text", "option 4 text"]
  },
  ...
]"""

SCHEDULE_PARSE_SYSTEM = """You are a marking schedule parser. Given the extracted text of an exam marking schedule,
extract the correct answer for each sub-question and return structured JSON.

Rules:
- Extract the correct/expected answer for each sub-question.
- For numeric answers, extract the primary numeric value (e.g. "7.38", "$187", "3 L").
- For multichoice, extract the correct option (e.g. "(ii)", "(iv)", "Choice D").
- For explanation/holistic questions, summarize what the correct position/approach is.
- Extract all accepted alternative answers if mentioned (e.g. "Accept 7.38, 738, 19:38").
- Identify marks as "A" (achieved/correct) or "H" (holistic/explanation).
- Include the full marking criteria as the explanation.
- Use simple numbering: "1", "2", "3" (not "ONE", "TWO")

Return ONLY a JSON array, no markdown:
[
  {
    "question_number": "1",
    "sub_question": "a",
    "correct_answer": "7.38 p.m.",
    "accepted_answers": ["7.38", "7:38", "738", "19:38"],
    "question_type": "numeric",
    "marks": "A",
    "explanation": "7:38 p.m. (p.m. not required). Accept 7.38, 19:38, 738."
  },
  ...
]"""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class PDFParserService:
    """Parse exam PDFs using PyMuPDF (text extraction) + AI (question splitting)."""

    async def parse_exam_pdf(self, file_bytes: bytes) -> ParsedExam:
        """Extract text from exam PDF, then use AI to split into questions."""
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        title = self._extract_title(doc)
        raw_text = self._extract_full_text(doc)
        page_images = self._extract_all_images(doc)

        # Extract per-question cropped images using PDF positioning
        question_images = self.extract_question_images(doc)

        doc.close()

        # AI splits text into structured questions
        questions = await self._ai_parse_questions(raw_text, page_images)

        # Attach cropped images to parsed questions
        for q in questions:
            key = f"Q{q.question_number}_{q.sub_question}"
            if key in question_images:
                q.image_bytes = question_images[key]
                q.has_image = True

        # Create passage entries (reading context pages) and insert before
        # each question's sub-questions
        passage_keys = sorted(
            k for k in question_images if "_passage_" in k
        )
        if passage_keys:
            # Group passage images by question number
            from collections import defaultdict
            passages_by_q: dict[str, list[str]] = defaultdict(list)
            for pk in passage_keys:
                # "Q1_passage_0" → q_num="1"
                q_num = pk.split("_")[0][1:]  # strip "Q"
                passages_by_q[q_num].append(pk)

            # Insert passage entries before each question's first sub
            extra: list[ParsedSubQuestion] = []
            for q_num, pkeys in passages_by_q.items():
                for i, pk in enumerate(pkeys):
                    extra.append(ParsedSubQuestion(
                        question_number=q_num,
                        sub_question=f"passage-{i}",
                        text="[Reading passage]",
                        question_type="passage",
                        has_image=True,
                        image_bytes=question_images[pk],
                        order_index=-1,  # will be re-indexed below
                    ))

            # Merge: passage entries first per question, then original subs
            merged: list[ParsedSubQuestion] = []
            seen_questions: set[str] = set()
            for q in questions:
                if q.question_number not in seen_questions:
                    seen_questions.add(q.question_number)
                    # Insert passage entries for this question
                    merged.extend(
                        p for p in extra if p.question_number == q.question_number
                    )
                merged.append(q)
            # Re-index
            for i, q in enumerate(merged):
                q.order_index = i
            questions = merged

        return ParsedExam(title=title, raw_text=raw_text, questions=questions)

    async def parse_schedule_pdf(self, file_bytes: bytes) -> list[ScheduleAnswer]:
        """Extract text from marking schedule PDF, then use AI to extract answers."""
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        raw_text = self._extract_full_text(doc)
        doc.close()

        return await self._ai_parse_schedule(raw_text)

    def get_answer_map(self, answers: list[ScheduleAnswer]) -> dict[str, ScheduleAnswer]:
        """Build a lookup map: '1_a' → ScheduleAnswer."""
        return {
            f"{a.question_number}_{a.sub_question.lower()}": a
            for a in answers
        }

    # ---------------------------------------------------------------------------
    # AI parsing
    # ---------------------------------------------------------------------------

    async def _ai_parse_questions(
        self, raw_text: str, page_images: dict[int, list[bytes]]
    ) -> list[ParsedSubQuestion]:
        """Use LLM to parse exam text into structured questions."""
        llm = get_llm(tier="fast", provider="gemini")

        messages = [
            SystemMessage(content=EXAM_PARSE_SYSTEM),
            HumanMessage(content=f"Parse this exam paper:\n\n{raw_text}"),
        ]

        result = await llm.ainvoke(messages)
        parsed = self._extract_json_array(result.content)

        questions = []
        has_any_image = len(page_images) > 0

        for i, item in enumerate(parsed):
            questions.append(ParsedSubQuestion(
                question_number=str(item.get("question_number", "")),
                sub_question=str(item.get("sub_question", "")),
                text=item.get("question_text", ""),
                question_type=item.get("question_type", ""),
                has_image=has_any_image,  # simplified: mark if PDF has images
                order_index=i,
            ))

        return questions

    async def _ai_parse_schedule(self, raw_text: str) -> list[ScheduleAnswer]:
        """Use LLM to parse marking schedule into structured answers."""
        llm = get_llm(tier="fast", provider="gemini")

        messages = [
            SystemMessage(content=SCHEDULE_PARSE_SYSTEM),
            HumanMessage(content=f"Parse this marking schedule:\n\n{raw_text}"),
        ]

        result = await llm.ainvoke(messages)
        parsed = self._extract_json_array(result.content)

        answers = []
        for item in parsed:
            answers.append(ScheduleAnswer(
                question_number=str(item.get("question_number", "")),
                sub_question=str(item.get("sub_question", "")),
                correct_answer=item.get("correct_answer", ""),
                accepted_answers=item.get("accepted_answers", []),
                explanation=item.get("explanation", ""),
                question_type=item.get("question_type", ""),
                marks=item.get("marks", ""),
            ))

        return answers

    # ---------------------------------------------------------------------------
    # Per-question image extraction via PDF coordinate positioning
    # ---------------------------------------------------------------------------

    # Patterns for locating question boundaries in the PDF
    _QUESTION_RE = re.compile(r"QUESTION\s+(ONE|TWO|THREE|FOUR|FIVE)\s*:?\s*(.*)")
    _SUB_RE = re.compile(r"^\(([a-f])\)")
    _NUMBER_MAP = {
        "ONE": "1", "TWO": "2", "THREE": "3", "FOUR": "4", "FIVE": "5",
    }
    _HEADER_MARGIN = 40   # skip page number at top
    _FOOTER_MARGIN = 40   # skip footer at bottom
    _SIDE_MARGIN = 30     # left/right trim
    _IMAGE_DPI = 150      # resolution for cropped images

    def extract_question_images(
        self, doc: fitz.Document,
    ) -> dict[str, bytes]:
        """Extract a cropped PNG image for each sub-question.

        Strategy:
        - Find all QUESTION headers and (a)/(b)/(c) markers with y-coordinates.
        - For each sub-question, crop from the *context start* to the next
          sub-question boundary.
        - Context start = the QUESTION header (if on the same page) or the
          previous sub-question's end, plus any preamble text/images above
          the current (x) marker on the same page.
        - For sub-questions that share a page with prior ones, include from
          the *end of the previous sub-question* so shared context (tables,
          graphs) is preserved.

        Returns a dict keyed by "Q{n}_{letter}" → PNG bytes.
        """
        markers = self._find_markers(doc)
        if not markers:
            return {}

        images: dict[str, bytes] = {}

        # --- Extract passage/context pages for each question ---
        # For reading exams, pages between QUESTION header and first sub
        # contain the reading passage that students need.
        self._extract_passage_images(doc, markers, images)

        # --- Extract per-sub-question cropped images ---
        for i, marker in enumerate(markers):
            if marker["type"] != "sub":
                continue

            q_num = marker["question"]
            sub = marker["label"]
            page_idx = marker["page"]
            page = doc[page_idx]
            page_w = page.rect.width
            page_h = page.rect.height

            # --- Determine y_top: where to start cropping ---
            y_top = self._find_context_top(markers, i, page_idx)

            # --- Determine y_bottom: where to stop cropping ---
            y_bottom = self._find_crop_bottom(markers, i, page_idx, page_h)

            # Crop and render
            clip = fitz.Rect(
                self._SIDE_MARGIN,
                max(0, y_top),
                page_w - self._SIDE_MARGIN,
                min(page_h, y_bottom),
            )
            pix = page.get_pixmap(clip=clip, dpi=self._IMAGE_DPI)
            key = f"Q{q_num}_{sub}"
            images[key] = pix.tobytes("png")

        return images

    def _extract_passage_images(
        self,
        doc: fitz.Document,
        markers: list[dict],
        images: dict[str, bytes],
    ) -> None:
        """Extract full-page passage images for each question.

        For reading/literacy exams, there are passage pages between the
        QUESTION header and the first sub-question. These need to be shown
        as context before the sub-questions.

        Produces keys like "Q1_passage_0", "Q1_passage_1", etc.
        """
        # Group markers by question number
        question_headers: dict[str, dict] = {}
        first_subs: dict[str, dict] = {}

        for m in markers:
            q = m["question"]
            if not q:
                continue
            if m["type"] == "question" and q not in question_headers:
                question_headers[q] = m
            if m["type"] == "sub" and q not in first_subs:
                first_subs[q] = m

        for q_num, header in question_headers.items():
            first_sub = first_subs.get(q_num)
            if not first_sub:
                continue

            header_page = header["page"]
            sub_page = first_sub["page"]

            # Only extract if there are passage pages between header and first sub
            if sub_page <= header_page:
                continue

            # Render each passage page (from header page to the page before first sub)
            for page_offset, page_idx in enumerate(range(header_page, sub_page)):
                page = doc[page_idx]
                clip = fitz.Rect(
                    self._SIDE_MARGIN,
                    self._HEADER_MARGIN,
                    page.rect.width - self._SIDE_MARGIN,
                    page.rect.height - self._FOOTER_MARGIN,
                )
                pix = page.get_pixmap(clip=clip, dpi=self._IMAGE_DPI)
                key = f"Q{q_num}_passage_{page_offset}"
                images[key] = pix.tobytes("png")

    def _find_markers(
        self, doc: fitz.Document,
    ) -> list[dict]:
        """Scan every page for QUESTION headers and (a)-(f) sub-question markers.

        Returns a sorted list of marker dicts:
          {"page": int, "y": float, "type": "question"|"sub",
           "question": str, "label": str, "title": str}
        """
        markers: list[dict] = []
        current_question = ""
        current_title = ""

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                for line in block["lines"]:
                    text = "".join(s["text"] for s in line["spans"]).strip()
                    y = line["bbox"][1]

                    qm = self._QUESTION_RE.match(text)
                    if qm:
                        current_question = self._NUMBER_MAP.get(
                            qm.group(1), qm.group(1)
                        )
                        current_title = qm.group(2).strip()
                        markers.append({
                            "page": page_idx, "y": y, "type": "question",
                            "question": current_question,
                            "label": current_question,
                            "title": current_title,
                        })

                    sm = self._SUB_RE.match(text)
                    if sm:
                        markers.append({
                            "page": page_idx, "y": y, "type": "sub",
                            "question": current_question,
                            "label": sm.group(1),
                            "title": "",
                        })

        markers.sort(key=lambda m: (m["page"], m["y"]))
        return markers

    def _find_context_top(
        self, markers: list[dict], current_idx: int, page_idx: int,
    ) -> float:
        """Find the y-coordinate where cropping should start for a sub-question.

        Rules:
        1. For the first sub-question (a) of a question: include from the
           QUESTION header (if on same page) or page top, so shared context
           like passages/tables/graphs is captured.
        2. For subsequent subs (b), (c), etc.: start from just above the
           current sub's own marker — each sub only shows its own content.
        """
        marker = markers[current_idx]

        # Check if this is the first sub of its question on this page
        is_first_sub = True
        question_header_y = None

        for j in range(current_idx - 1, -1, -1):
            prev = markers[j]
            if prev["page"] != page_idx:
                break
            if prev["type"] == "question":
                question_header_y = prev["y"]
                break
            if prev["type"] == "sub" and prev["question"] == marker["question"]:
                is_first_sub = False
                break

        if is_first_sub:
            # First sub: include QUESTION header or page top for shared context
            if question_header_y is not None:
                return question_header_y - 5
            return self._HEADER_MARGIN

        # Subsequent subs: start from just above their own (x) marker
        return marker["y"] - 10

    def _find_crop_bottom(
        self, markers: list[dict], current_idx: int,
        page_idx: int, page_height: float,
    ) -> float:
        """Find the y-coordinate where cropping should end."""
        for j in range(current_idx + 1, len(markers)):
            nxt = markers[j]
            if nxt["page"] == page_idx:
                return nxt["y"] - 5
            if nxt["page"] > page_idx:
                break
        return page_height - self._FOOTER_MARGIN

    # ---------------------------------------------------------------------------
    # PyMuPDF text/image extraction
    # ---------------------------------------------------------------------------

    def _extract_title(self, doc: fitz.Document) -> str:
        """Extract exam title from the first page."""
        if len(doc) == 0:
            return "Unknown Exam"

        page = doc[0]
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                text = "".join(span["text"] for span in line["spans"]).strip()
                if "Numeracy" in text and any(str(y) in text for y in range(2020, 2030)):
                    return text

        # Fallback: look for any large bold text
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block["lines"]:
                spans = line["spans"]
                if spans and spans[0]["size"] >= 14:
                    text = "".join(s["text"] for s in spans).strip()
                    if len(text) > 5:
                        return text

        return "Exam Paper"

    # Patterns to strip from extracted text (watermarks, repeated noise)
    _NOISE_PATTERNS = [
        re.compile(r"(?:DO NOT WRITE IN(?:\s+THIS)?(?:\s+AREA)?[^\n]*\n?)+", re.IGNORECASE),
        re.compile(r"(?:SUPERVISOR'?S?\s+USE\s+ONLY[^\n]*\n?)+", re.IGNORECASE),
    ]

    def _extract_full_text(self, doc: fitz.Document) -> str:
        """Extract all text from the PDF, filtering out watermarks and noise."""
        parts = []
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            if text:
                # Remove watermark/noise patterns
                for pattern in self._NOISE_PATTERNS:
                    text = pattern.sub("", text)
                # Collapse multiple blank lines
                text = re.sub(r"\n{3,}", "\n\n", text).strip()
                if text:
                    parts.append(f"--- Page {i + 1} ---\n{text}")
        return "\n\n".join(parts)

    def _extract_all_images(self, doc: fitz.Document) -> dict[int, list[bytes]]:
        """Extract images from all pages as PNG bytes."""
        page_images: dict[int, list[bytes]] = {}
        for page_num in range(len(doc)):
            page = doc[page_num]
            images = []
            for img_info in page.get_images(full=True):
                xref = img_info[0]
                try:
                    pix = fitz.Pixmap(doc, xref)
                    if pix.n > 4:
                        pix = fitz.Pixmap(fitz.csRGB, pix)
                    images.append(pix.tobytes("png"))
                except Exception:
                    continue
            if images:
                page_images[page_num] = images
        return page_images

    # ---------------------------------------------------------------------------
    # JSON extraction helper
    # ---------------------------------------------------------------------------

    def _extract_json_array(self, content: str) -> list[dict]:
        """Extract a JSON array from LLM response, handling markdown fences."""
        content = content.strip()

        # Remove markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            content = "\n".join(lines).strip()

        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
            return []
        except json.JSONDecodeError:
            # Try to find array in the content
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(content[start:end])
                except json.JSONDecodeError:
                    pass

            logger.error("Failed to parse LLM response as JSON array: %s", content[:200])
            return []
