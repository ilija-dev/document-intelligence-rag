"""
Document chunking with RecursiveCharacterTextSplitter.

Chunk size is the single most impactful parameter in RAG:
- Too large (1000+ tokens): mixed topics per chunk → noisy retrieval
- Too small (100 tokens): fragments lose meaning → LLM can't reason
- 500 tokens / 50 overlap: sweet spot for document Q&A

The overlap prevents information loss at chunk boundaries — a sentence
spanning two chunks is captured in both.

Interview point: "I tested chunk sizes from 200–1000 tokens. At 200, the LLM
couldn't get enough context. At 1000, retrieval precision dropped because
chunks mixed multiple topics. 500 with 50-token overlap gave the best
Precision@5 on our evaluation set."
"""

import hashlib
import logging
from dataclasses import dataclass, field

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import settings
from .extract import ExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single chunk of text with full provenance tracking."""

    chunk_id: str  # Deterministic hash for deduplication
    text: str
    doc_name: str
    doc_path: str
    page_number: int
    chunk_index: int  # Position within the document
    char_count: int = 0
    token_estimate: int = 0  # Rough estimate: chars / 4

    def __post_init__(self) -> None:
        self.char_count = len(self.text)
        self.token_estimate = self.char_count // 4


@dataclass
class ChunkingResult:
    """Output of chunking an entire document."""

    doc_name: str
    total_chunks: int
    chunks: list[Chunk] = field(default_factory=list)
    avg_chunk_size: float = 0.0

    def __post_init__(self) -> None:
        if self.chunks:
            self.avg_chunk_size = sum(c.char_count for c in self.chunks) / len(
                self.chunks
            )


def _generate_chunk_id(doc_name: str, chunk_index: int, text: str) -> str:
    """
    Generate a deterministic chunk ID for deduplication.

    Using doc_name + chunk_index + text hash means re-ingesting the same
    document produces the same IDs, enabling upsert instead of duplicate inserts.
    """
    content = f"{doc_name}::{chunk_index}::{text[:200]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def create_splitter(
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> RecursiveCharacterTextSplitter:
    """
    Create a text splitter with the configured parameters.

    RecursiveCharacterTextSplitter is preferred over simple splitting because
    it tries to split at natural boundaries (paragraphs → sentences → words)
    rather than cutting mid-word. The hierarchy of separators:
    1. Double newline (paragraph break)
    2. Single newline
    3. Sentence-ending punctuation
    4. Space (word boundary)
    5. Empty string (character-level, last resort)
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.chunk_size,
        chunk_overlap=chunk_overlap or settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=True,
    )


def chunk_document(
    extraction: ExtractionResult,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> ChunkingResult:
    """
    Chunk an extracted document into overlapping segments.

    Each chunk carries its source document name and page number for
    source attribution in the final RAG answer.
    """
    splitter = create_splitter(chunk_size, chunk_overlap)
    chunks: list[Chunk] = []
    chunk_index = 0

    for page in extraction.pages:
        if not page.text.strip():
            continue

        # Split this page's text into chunks
        page_chunks = splitter.split_text(page.text)

        for text in page_chunks:
            text = text.strip()
            if not text:
                continue

            chunk = Chunk(
                chunk_id=_generate_chunk_id(
                    extraction.file_name, chunk_index, text
                ),
                text=text,
                doc_name=extraction.file_name,
                doc_path=extraction.file_path,
                page_number=page.page_number,
                chunk_index=chunk_index,
            )
            chunks.append(chunk)
            chunk_index += 1

    result = ChunkingResult(
        doc_name=extraction.file_name,
        total_chunks=len(chunks),
        chunks=chunks,
    )

    logger.info(
        f"Chunked {extraction.file_name}: {result.total_chunks} chunks, "
        f"avg size {result.avg_chunk_size:.0f} chars"
    )
    return result
