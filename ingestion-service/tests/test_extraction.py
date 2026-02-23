"""Tests for document text extraction."""

import tempfile
from pathlib import Path

import pytest

from src.extract import (
    ExtractionResult,
    _clean_extracted_text,
    _split_into_synthetic_pages,
    extract_document,
    extract_text_file,
)


class TestCleanText:
    def test_removes_form_feeds(self):
        assert "\f" not in _clean_extracted_text("Hello\fWorld")

    def test_collapses_newlines(self):
        result = _clean_extracted_text("A\n\n\n\n\nB")
        assert result == "A\n\nB"

    def test_strips_trailing_whitespace(self):
        result = _clean_extracted_text("Hello   \nWorld   ")
        assert result == "Hello\nWorld"

    def test_preserves_paragraph_breaks(self):
        result = _clean_extracted_text("Para 1\n\nPara 2")
        assert "\n\n" in result


class TestSyntheticPages:
    def test_short_text_single_page(self):
        pages = _split_into_synthetic_pages("Short text", chars_per_page=3000)
        assert len(pages) == 1

    def test_long_text_multiple_pages(self):
        text = "A" * 10000
        pages = _split_into_synthetic_pages(text, chars_per_page=3000)
        assert len(pages) >= 3

    def test_splits_at_paragraph_boundaries(self):
        # Create text with clear paragraph breaks
        paragraphs = ["Paragraph content " * 50 + "\n\n" for _ in range(10)]
        text = "".join(paragraphs)
        pages = _split_into_synthetic_pages(text, chars_per_page=500)

        # Pages shouldn't start mid-word in most cases
        for page in pages:
            assert not page.startswith(" ")


class TestTextFileExtraction:
    def test_extract_markdown(self):
        with tempfile.NamedTemporaryFile(
            suffix=".md", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("# Test Document\n\nThis is a test document with content.")
            f.flush()

            result = extract_document(f.name)

            assert result.file_name.endswith(".md")
            assert result.total_pages >= 1
            assert result.total_chars > 0
            assert "Test Document" in result.pages[0].text

        Path(f.name).unlink()

    def test_extract_txt(self):
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("Plain text content for testing.")
            f.flush()

            result = extract_document(f.name)

            assert result.total_pages == 1
            assert "Plain text content" in result.pages[0].text

        Path(f.name).unlink()

    def test_long_text_gets_synthetic_pages(self):
        with tempfile.NamedTemporaryFile(
            suffix=".txt", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("Long content paragraph. " * 500)
            f.flush()

            result = extract_document(f.name)
            # Long text should be split into multiple synthetic pages
            assert result.total_pages > 1

        Path(f.name).unlink()

    def test_unsupported_extension_raises(self):
        with tempfile.NamedTemporaryFile(
            suffix=".docx", mode="w", delete=False
        ) as f:
            f.write("test")
            f.flush()

            with pytest.raises(ValueError, match="Unsupported file type"):
                extract_document(f.name)

        Path(f.name).unlink()

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            extract_document("/nonexistent/path/file.pdf")

    def test_page_numbers_are_one_indexed(self):
        with tempfile.NamedTemporaryFile(
            suffix=".md", mode="w", delete=False, encoding="utf-8"
        ) as f:
            f.write("Content")
            f.flush()

            result = extract_document(f.name)
            assert result.pages[0].page_number == 1

        Path(f.name).unlink()
