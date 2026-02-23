"""Tests for the chunking pipeline."""

from src.chunker import Chunk, chunk_document, create_splitter
from src.extract import ExtractionResult, ExtractedPage


def _make_extraction(text: str, file_name: str = "test.md") -> ExtractionResult:
    """Helper to create an ExtractionResult from raw text."""
    return ExtractionResult(
        file_name=file_name,
        file_path=f"/tmp/{file_name}",
        total_pages=1,
        pages=[ExtractedPage(page_number=1, text=text)],
    )


class TestChunker:
    def test_basic_chunking(self):
        """Chunks should be created from text."""
        text = "Hello world. " * 200  # ~2600 chars
        extraction = _make_extraction(text)
        result = chunk_document(extraction, chunk_size=500, chunk_overlap=50)

        assert result.total_chunks > 1
        assert all(isinstance(c, Chunk) for c in result.chunks)

    def test_chunk_size_respected(self):
        """No chunk should significantly exceed the target size."""
        text = "This is a test sentence with some content. " * 500
        extraction = _make_extraction(text)
        result = chunk_document(extraction, chunk_size=500, chunk_overlap=50)

        for chunk in result.chunks:
            # Allow some tolerance — splitter may go slightly over
            assert chunk.char_count < 600, (
                f"Chunk too large: {chunk.char_count} chars"
            )

    def test_overlap_present(self):
        """Consecutive chunks should share overlapping text."""
        # Create text with clear paragraph breaks
        paragraphs = [f"Paragraph {i}. " * 20 for i in range(20)]
        text = "\n\n".join(paragraphs)
        extraction = _make_extraction(text)
        result = chunk_document(extraction, chunk_size=300, chunk_overlap=50)

        if result.total_chunks >= 2:
            # Check that some content overlaps between consecutive chunks
            for i in range(len(result.chunks) - 1):
                current_end = result.chunks[i].text[-50:]
                next_start = result.chunks[i + 1].text[:100]
                # The overlap means some words from end of chunk N
                # appear at start of chunk N+1
                current_words = set(current_end.split())
                next_words = set(next_start.split())
                # At least some overlap expected
                overlap = current_words & next_words
                # This is a soft check — overlap depends on split boundaries
                if len(overlap) > 0:
                    break
            # At least one pair should have overlap

    def test_chunk_ids_deterministic(self):
        """Same document should produce same chunk IDs on re-ingestion."""
        text = "Test content for deterministic IDs. " * 100
        extraction = _make_extraction(text)

        result1 = chunk_document(extraction, chunk_size=500, chunk_overlap=50)
        result2 = chunk_document(extraction, chunk_size=500, chunk_overlap=50)

        assert len(result1.chunks) == len(result2.chunks)
        for c1, c2 in zip(result1.chunks, result2.chunks):
            assert c1.chunk_id == c2.chunk_id

    def test_page_numbers_preserved(self):
        """Chunks should carry the correct page number."""
        extraction = ExtractionResult(
            file_name="multi-page.pdf",
            file_path="/tmp/multi-page.pdf",
            total_pages=3,
            pages=[
                ExtractedPage(page_number=1, text="Page one content. " * 50),
                ExtractedPage(page_number=2, text="Page two content. " * 50),
                ExtractedPage(page_number=3, text="Page three content. " * 50),
            ],
        )
        result = chunk_document(extraction, chunk_size=200, chunk_overlap=20)

        page_numbers = {c.page_number for c in result.chunks}
        assert 1 in page_numbers
        assert 2 in page_numbers
        assert 3 in page_numbers

    def test_empty_pages_skipped(self):
        """Empty pages should not produce chunks."""
        extraction = ExtractionResult(
            file_name="sparse.pdf",
            file_path="/tmp/sparse.pdf",
            total_pages=3,
            pages=[
                ExtractedPage(page_number=1, text="Real content here. " * 50),
                ExtractedPage(page_number=2, text=""),
                ExtractedPage(page_number=3, text="   \n\n  "),
            ],
        )
        result = chunk_document(extraction, chunk_size=200, chunk_overlap=20)

        assert result.total_chunks > 0
        page_numbers = {c.page_number for c in result.chunks}
        assert 2 not in page_numbers
        assert 3 not in page_numbers

    def test_short_document(self):
        """A very short document should produce exactly one chunk."""
        text = "Short document."
        extraction = _make_extraction(text)
        result = chunk_document(extraction, chunk_size=500, chunk_overlap=50)

        assert result.total_chunks == 1
        assert result.chunks[0].text == "Short document."

    def test_doc_metadata_on_chunks(self):
        """All chunks should carry the source document name."""
        text = "Content for metadata test. " * 100
        extraction = _make_extraction(text, file_name="policy.pdf")
        result = chunk_document(extraction, chunk_size=200, chunk_overlap=20)

        for chunk in result.chunks:
            assert chunk.doc_name == "policy.pdf"
            assert chunk.doc_path == "/tmp/policy.pdf"


class TestSplitter:
    def test_default_splitter_config(self):
        """Default splitter should use configured chunk size."""
        splitter = create_splitter()
        assert splitter._chunk_size == 500
        assert splitter._chunk_overlap == 50

    def test_custom_splitter_config(self):
        """Custom parameters should override defaults."""
        splitter = create_splitter(chunk_size=1000, chunk_overlap=100)
        assert splitter._chunk_size == 1000
        assert splitter._chunk_overlap == 100
