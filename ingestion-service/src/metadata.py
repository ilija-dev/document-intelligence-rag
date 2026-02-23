"""
Document metadata management.

At 1,500+ documents, vector similarity alone returns false positives — chunks
that are semantically similar but from the wrong category or time period.
Structured metadata (category, date, source) enables the hybrid search layer
to filter results before they reach the LLM.

Interview point: "Metadata filtering is what separates a demo RAG from a
production RAG. Without it, a query about '2024 return policy' might return
chunks from the 2022 version because they're semantically identical."
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Category detection patterns — maps keywords in filename/content to categories
CATEGORY_PATTERNS: dict[str, list[str]] = {
    "hr_policy": ["hr", "human resource", "employee", "leave", "benefits", "onboarding"],
    "it_policy": ["it", "security", "password", "network", "vpn", "software"],
    "finance": ["finance", "budget", "expense", "invoice", "procurement", "reimbursement"],
    "travel": ["travel", "trip", "flight", "hotel", "per diem", "booking"],
    "product": ["product", "feature", "specification", "release", "roadmap", "api"],
    "troubleshooting": ["troubleshoot", "error", "fix", "issue", "debug", "problem"],
    "meeting_notes": ["meeting", "minutes", "agenda", "action item", "standup"],
    "knowledge_base": ["how to", "guide", "tutorial", "faq", "instructions", "setup"],
}


@dataclass
class DocumentMetadata:
    """Metadata attached to every chunk for filtering at search time."""

    doc_name: str
    doc_path: str
    category: str
    ingestion_date: str  # ISO format
    page_count: int
    chunk_count: int = 0
    file_size_bytes: int = 0
    tags: list[str] = field(default_factory=list)

    def to_chroma_metadata(self, page_number: int, chunk_index: int) -> dict:
        """
        Flatten to a dict for ChromaDB metadata storage.

        ChromaDB metadata values must be str, int, float, or bool.
        Lists are joined as comma-separated strings.
        """
        return {
            "doc_name": self.doc_name,
            "category": self.category,
            "ingestion_date": self.ingestion_date,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "page_count": self.page_count,
            "tags": ",".join(self.tags) if self.tags else "",
        }


def detect_category(file_name: str, sample_text: str = "") -> str:
    """
    Infer document category from filename and content.

    Uses a simple keyword-matching approach. In production, you'd use
    a classifier model, but keyword matching is transparent, debuggable,
    and good enough for 80% of cases.
    """
    # Normalize for matching
    name_lower = file_name.lower().replace("-", " ").replace("_", " ")
    text_lower = sample_text[:2000].lower() if sample_text else ""
    combined = f"{name_lower} {text_lower}"

    best_category = "general"
    best_score = 0

    for category, keywords in CATEGORY_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in combined)
        if score > best_score:
            best_score = score
            best_category = category

    logger.debug(f"Category for {file_name}: {best_category} (score={best_score})")
    return best_category


def extract_tags(file_name: str, text: str = "") -> list[str]:
    """Extract simple tags from filename for additional filtering."""
    tags: list[str] = []

    # Extract year if present in filename
    year_match = re.search(r"20[12]\d", file_name)
    if year_match:
        tags.append(f"year:{year_match.group()}")

    # Extract version if present
    version_match = re.search(r"v(\d+(?:\.\d+)*)", file_name, re.IGNORECASE)
    if version_match:
        tags.append(f"version:{version_match.group(1)}")

    # File extension as tag
    suffix = Path(file_name).suffix.lower()
    if suffix:
        tags.append(f"type:{suffix[1:]}")

    return tags


def build_metadata(
    file_name: str,
    file_path: str,
    page_count: int,
    chunk_count: int,
    sample_text: str = "",
    file_size_bytes: int = 0,
) -> DocumentMetadata:
    """Build complete metadata for a document."""
    return DocumentMetadata(
        doc_name=file_name,
        doc_path=file_path,
        category=detect_category(file_name, sample_text),
        ingestion_date=datetime.now().isoformat(),
        page_count=page_count,
        chunk_count=chunk_count,
        file_size_bytes=file_size_bytes,
        tags=extract_tags(file_name, sample_text),
    )
