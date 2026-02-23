"""
Document text extraction with per-page tracking.

Supports PDF (via PyMuPDF), markdown, and plain text files.
The critical design choice: every extracted block carries its page number.
This enables source attribution in the final RAG answer — "Answer from
HR-Policy.pdf, page 3" — which is essential for user trust.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class ExtractedPage:
    """A single page of extracted text with its metadata."""

    page_number: int
    text: str
    char_count: int = 0

    def __post_init__(self) -> None:
        self.char_count = len(self.text)


@dataclass
class ExtractionResult:
    """Full extraction output for one document."""

    file_name: str
    file_path: str
    total_pages: int
    pages: list[ExtractedPage] = field(default_factory=list)
    extraction_errors: list[str] = field(default_factory=list)

    @property
    def total_chars(self) -> int:
        return sum(p.char_count for p in self.pages)

    @property
    def non_empty_pages(self) -> int:
        return sum(1 for p in self.pages if p.text.strip())


def extract_pdf(file_path: Path) -> ExtractionResult:
    """
    Extract text from a PDF using PyMuPDF (fitz).

    PyMuPDF is chosen over alternatives because:
    - 10x faster than pdfplumber for text extraction
    - Handles complex layouts (multi-column, tables) better than PyPDF2
    - Preserves reading order across columns
    """
    result = ExtractionResult(
        file_name=file_path.name,
        file_path=str(file_path),
        total_pages=0,
    )

    try:
        doc = fitz.open(str(file_path))
        result.total_pages = len(doc)

        for page_num in range(len(doc)):
            try:
                page = doc[page_num]
                # "text" sort mode preserves natural reading order
                text = page.get_text("text", sort=True)

                # Clean up common PDF extraction artifacts
                text = _clean_extracted_text(text)

                result.pages.append(
                    ExtractedPage(
                        page_number=page_num + 1,  # 1-indexed for humans
                        text=text,
                    )
                )
            except Exception as e:
                error_msg = f"Error extracting page {page_num + 1}: {e}"
                logger.warning(error_msg)
                result.extraction_errors.append(error_msg)

        doc.close()
    except Exception as e:
        error_msg = f"Failed to open PDF {file_path}: {e}"
        logger.error(error_msg)
        result.extraction_errors.append(error_msg)

    logger.info(
        f"Extracted {result.non_empty_pages}/{result.total_pages} pages "
        f"from {result.file_name} ({result.total_chars:,} chars)"
    )
    return result


def extract_text_file(file_path: Path) -> ExtractionResult:
    """
    Extract text from .txt or .md files.

    For non-PDF files, we treat the entire file as one "page" since
    they don't have physical page boundaries. The page_number is set to 1
    for consistency with the chunking pipeline.
    """
    result = ExtractionResult(
        file_name=file_path.name,
        file_path=str(file_path),
        total_pages=1,
    )

    try:
        text = file_path.read_text(encoding="utf-8")
        text = _clean_extracted_text(text)

        # For long text files, split into synthetic "pages" of ~3000 chars
        # to keep page-level attribution meaningful
        if len(text) > 4000:
            pages = _split_into_synthetic_pages(text, chars_per_page=3000)
            result.total_pages = len(pages)
            for i, page_text in enumerate(pages):
                result.pages.append(
                    ExtractedPage(page_number=i + 1, text=page_text)
                )
        else:
            result.pages.append(ExtractedPage(page_number=1, text=text))

    except Exception as e:
        error_msg = f"Failed to read {file_path}: {e}"
        logger.error(error_msg)
        result.extraction_errors.append(error_msg)

    logger.info(
        f"Extracted {result.file_name} ({result.total_chars:,} chars, "
        f"{result.total_pages} page(s))"
    )
    return result


def extract_document(file_path: str | Path) -> ExtractionResult:
    """
    Route document to the appropriate extractor based on file extension.

    This is the main entry point for the extraction layer.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in settings.supported_extensions:
        raise ValueError(
            f"Unsupported file type: {suffix}. "
            f"Supported: {settings.supported_extensions}"
        )

    if suffix == ".pdf":
        return extract_pdf(path)
    elif suffix in (".txt", ".md"):
        return extract_text_file(path)
    else:
        raise ValueError(f"No extractor for {suffix}")


def _clean_extracted_text(text: str) -> str:
    """
    Clean common extraction artifacts.

    PDF extraction often produces double newlines, trailing spaces,
    and form-feed characters. Cleaning these improves chunk quality
    downstream.
    """
    # Remove form feed and vertical tab characters
    text = text.replace("\f", "\n").replace("\v", "\n")
    # Collapse 3+ newlines into 2 (preserve paragraph breaks)
    import re

    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove trailing whitespace per line
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    # Strip leading/trailing whitespace
    text = text.strip()
    return text


def _split_into_synthetic_pages(
    text: str, chars_per_page: int = 3000
) -> list[str]:
    """
    Split long text files into synthetic pages at paragraph boundaries.

    Instead of cutting at exactly 3000 chars (which would split mid-sentence),
    we find the nearest paragraph break (\n\n) to the target split point.
    """
    if len(text) <= chars_per_page:
        return [text]

    pages: list[str] = []
    start = 0

    while start < len(text):
        end = start + chars_per_page

        if end >= len(text):
            pages.append(text[start:].strip())
            break

        # Find nearest paragraph break near the target split point
        # Search in a window around the target
        search_start = max(start, end - 200)
        search_end = min(len(text), end + 200)
        window = text[search_start:search_end]

        # Prefer splitting at paragraph breaks
        para_break = window.rfind("\n\n")
        if para_break != -1:
            split_at = search_start + para_break + 2
        else:
            # Fall back to sentence boundary
            sentence_end = window.rfind(". ")
            if sentence_end != -1:
                split_at = search_start + sentence_end + 2
            else:
                # Last resort: split at target
                split_at = end

        page_text = text[start:split_at].strip()
        if page_text:
            pages.append(page_text)
        start = split_at

    return pages
