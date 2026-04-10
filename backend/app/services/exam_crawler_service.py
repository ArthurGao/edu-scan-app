"""Crawl NZQA exam pages, download PDFs, parse and store questions."""

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


@dataclass
class CrawledPDF:
    """A PDF discovered on the page."""
    url: str
    title: str
    year: int
    language: str
    pdf_type: str  # "exam" | "schedule" | "report" | "exemplar" | "other"
    event: str = ""  # "event-1", "event-2", "week-1", "week-2"
    exam_code: str = ""  # e.g. "32406", "91946" — auto-detected from URL/content


@dataclass
class ExamSchedulePair:
    """Matched exam paper + its marking schedule."""
    exam: CrawledPDF
    schedule: CrawledPDF | None = None


LANGUAGE_PATTERNS = {
    "english": re.compile(r"\benglish\b", re.IGNORECASE),
    "te_reo_maori": re.compile(r"\b(māori|maori|te reo|whakamatautau|rauemi|pāngarau)\b", re.IGNORECASE),
    "cook_islands_maori": re.compile(r"\bcook island", re.IGNORECASE),
    "niuean": re.compile(r"\bniuean\b", re.IGNORECASE),
    "tokelauan": re.compile(r"\btokelau", re.IGNORECASE),
}
# NZQA filenames: -mex- = Maori exam, -mre- = Maori resource
MAORI_URL_RE = re.compile(r"-m(ex|re|qb)-", re.IGNORECASE)

PDF_TYPE_PATTERNS = {
    "schedule": re.compile(r"\b(schedule|marking)\b", re.IGNORECASE),
    "report": re.compile(r"\breport\b", re.IGNORECASE),
    "exemplar": re.compile(r"\bexemplar", re.IGNORECASE),
    "specification": re.compile(r"\bspecification", re.IGNORECASE),
}

YEAR_RE = re.compile(r"(202[0-9])")
EVENT_RE = re.compile(r"event[- ]?(\d)", re.IGNORECASE)
WEEK_RE = re.compile(r"week[- ]?(\d)", re.IGNORECASE)
EXAM_CODE_RE = re.compile(r"\b(\d{5})\b")  # 5-digit NZQA standard number

# Map known exam codes to subject and level
EXAM_CODE_MAP: dict[str, dict[str, str | int]] = {
    "32406": {"subject": "numeracy", "level": 1},
    "32403": {"subject": "literacy-reading", "level": 1},
    "32404": {"subject": "literacy-reading", "level": 1},
    "32407": {"subject": "literacy-writing", "level": 1},
    "32408": {"subject": "literacy-writing", "level": 1},
    "91946": {"subject": "mathematics", "level": 1},
    "91947": {"subject": "mathematics", "level": 1},
    "91948": {"subject": "mathematics", "level": 1},
    "91944": {"subject": "mathematics", "level": 1},
    "91945": {"subject": "mathematics", "level": 1},
    "91261": {"subject": "mathematics", "level": 2},
    "91262": {"subject": "mathematics", "level": 2},
    "91263": {"subject": "mathematics", "level": 2},
    "91264": {"subject": "mathematics", "level": 2},
    "91267": {"subject": "mathematics", "level": 2},
    "91269": {"subject": "mathematics", "level": 2},
    "91578": {"subject": "mathematics", "level": 3},
    "91579": {"subject": "mathematics", "level": 3},
    "91580": {"subject": "mathematics", "level": 3},
    "91587": {"subject": "mathematics", "level": 3},
}


class ExamCrawlerService:
    """Crawl NZQA pages to discover and download exam PDFs."""

    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout

    async def discover_pdfs(self, page_url: str) -> list[CrawledPDF]:
        """Fetch an NZQA page and discover all PDF links."""
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            resp = await client.get(page_url)
            resp.raise_for_status()

        html = resp.text
        pdfs = []

        # Find all <a> tags with .pdf links
        # Pattern: <a href="...pdf"...>link text</a>
        link_re = re.compile(
            r'<a\s[^>]*href="([^"]*\.pdf)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        for match in link_re.finditer(html):
            href = match.group(1)
            link_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()

            # NZQA new site often uses generic link text like "PDF (2.3 MB)".
            # Extract surrounding context (the text in the same row/container)
            # by looking at a window of text around the match in the HTML.
            context_text = link_text
            if link_text.startswith("PDF") or len(link_text) < 20:
                start = max(0, match.start() - 300)
                end = min(len(html), match.end() + 50)
                surrounding = re.sub(r"<[^>]+>", " ", html[start:end]).strip()
                surrounding = re.sub(r"\s+", " ", surrounding)
                context_text = surrounding

            url = urljoin(page_url, href)
            pdf = self._classify_pdf(url, link_text, context_text)
            pdfs.append(pdf)

        logger.info("Discovered %d PDFs on %s", len(pdfs), page_url)
        return pdfs

    async def download_pdf(self, url: str) -> bytes:
        """Download a PDF and return its bytes."""
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
        return resp.content

    def filter_exam_pdfs(
        self,
        pdfs: list[CrawledPDF],
        language: str = "english",
    ) -> list[CrawledPDF]:
        """Filter to only exam papers and schedules in the specified language.

        If no language-specific exam is found (older years), include
        papers without explicit language markers.
        """
        # Separate by type
        exams = [p for p in pdfs if p.pdf_type == "exam"]
        schedules = [p for p in pdfs if p.pdf_type == "schedule"]

        # Filter by language
        lang_exams = [p for p in exams if p.language == language]
        lang_schedules = [p for p in schedules if p.language == language]

        # For older papers without language markers, include "unknown" language
        if not lang_exams:
            lang_exams = [p for p in exams if p.language in (language, "unknown")]
        if not lang_schedules:
            lang_schedules = [p for p in schedules if p.language in (language, "unknown")]

        return lang_exams + lang_schedules

    def pair_exams_with_schedules(
        self, pdfs: list[CrawledPDF]
    ) -> list[ExamSchedulePair]:
        """Match exam papers with their corresponding marking schedules.

        Matching strategy: same year + same event.
        """
        exams = [p for p in pdfs if p.pdf_type == "exam"]
        schedules = [p for p in pdfs if p.pdf_type == "schedule"]

        # Build schedule lookup by (year, event)
        schedule_map: dict[tuple[int, str], CrawledPDF] = {}
        for s in schedules:
            key = (s.year, s.event)
            schedule_map[key] = s

        pairs = []
        for exam in exams:
            key = (exam.year, exam.event)
            schedule = schedule_map.get(key)

            # Fallback: try matching just by year if event doesn't match
            if not schedule:
                for s in schedules:
                    if s.year == exam.year:
                        schedule = s
                        break

            pairs.append(ExamSchedulePair(exam=exam, schedule=schedule))

        return pairs

    def _classify_pdf(self, url: str, link_text: str, context_text: str = "") -> CrawledPDF:
        """Classify a PDF by its URL, link text, and surrounding page context."""
        combined = f"{context_text or link_text} {url}"

        # Detect year
        year_match = YEAR_RE.search(combined)
        year = int(year_match.group(1)) if year_match else 0

        # Detect type
        pdf_type = "exam"  # default
        for ptype, pattern in PDF_TYPE_PATTERNS.items():
            if pattern.search(combined):
                pdf_type = ptype
                break
        # If link text or context contains "assessment paper" or "exam", it's an exam
        if re.search(r"\b(assessment paper|exam)\b", combined, re.IGNORECASE):
            pdf_type = "exam"

        # Detect language
        language = "unknown"
        for lang, pattern in LANGUAGE_PATTERNS.items():
            if pattern.search(combined):
                language = lang
                break
        # Check URL for Maori filename pattern (e.g. 91262-mex-2024.pdf)
        if language == "unknown" and MAORI_URL_RE.search(url):
            language = "te_reo_maori"
        # If no explicit non-English language detected, default to English.
        # NZQA always labels non-English papers explicitly (Te Reo Māori, Niuean, etc.)
        if language == "unknown" and pdf_type in ("exam", "schedule"):
            language = "english"

        # Detect event/week
        event = ""
        event_match = EVENT_RE.search(combined)
        week_match = WEEK_RE.search(combined)
        if event_match:
            event = f"event-{event_match.group(1)}"
        if week_match:
            event = f"{event}-week-{week_match.group(1)}" if event else f"week-{week_match.group(1)}"

        # Detect exam code from URL (e.g. "91946-exm-2025.pdf" → "91946")
        exam_code = ""
        code_match = EXAM_CODE_RE.search(url.split("/")[-1])
        if code_match and code_match.group(1) in EXAM_CODE_MAP:
            exam_code = code_match.group(1)
        elif code_match:
            # Try the combined text for known codes
            for code in EXAM_CODE_MAP:
                if code in combined:
                    exam_code = code
                    break

        # Use context for title when link text is generic like "PDF (2.3 MB)" or "(796KB)"
        title = link_text
        if (link_text.startswith("PDF") or link_text.startswith("(")) and context_text and len(context_text) > len(link_text):
            clean = re.sub(r"PDF\s*\([^)]*\)", "", context_text).strip()
            clean = re.sub(r"\([^)]*KB\)|\([^)]*MB\)", "", clean).strip()
            clean = re.sub(r"\s+", " ", clean).strip()
            if clean:
                title = clean[:100]
        # Still generic? Use exam code + year
        if title.startswith("(") or title.startswith("PDF"):
            if exam_code and year:
                title = f"{exam_code} Exam {year}"

        return CrawledPDF(
            url=url,
            title=title,
            year=year,
            language=language,
            pdf_type=pdf_type,
            event=event,
            exam_code=exam_code,
        )
