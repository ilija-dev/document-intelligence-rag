"""
Retrieval quality tests — precision/recall on labeled test queries.

These tests validate that the full pipeline (extract → chunk → embed → store → search)
returns relevant results for known queries. This is the most important test suite
because it catches regressions in retrieval quality.

Note: These tests require the embedding model to be available and are slower
than unit tests. They should be run before deploying changes to the chunking
or embedding pipeline.
"""

import tempfile
from pathlib import Path

import pytest

from src.chunker import chunk_document
from src.embedder import embed_single, embed_texts
from src.extract import extract_document
from src.metadata import build_metadata

# These tests require the embedding model which is heavy
# Mark them so they can be skipped in CI with: pytest -m "not slow"
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def sample_docs():
    """Create a set of sample documents with known content."""
    docs = {
        "leave-policy.md": (
            "# Employee Leave Policy\n\n"
            "All employees are entitled to 20 days of paid annual leave per year. "
            "Sick leave is 10 days per year. A medical certificate is required "
            "for absences exceeding 3 consecutive days. Parental leave is 16 weeks "
            "for primary caregivers and 4 weeks for secondary caregivers.\n\n"
            "Leave requests must be submitted through the HR portal at least "
            "10 business days in advance."
        ),
        "password-policy.md": (
            "# Password Security Policy\n\n"
            "All passwords must be at least 14 characters long and include "
            "uppercase, lowercase, numbers, and special characters. Passwords "
            "expire every 90 days and you cannot reuse the last 12 passwords. "
            "Multi-factor authentication is required for all systems.\n\n"
            "Report compromised passwords immediately to security@company.com."
        ),
        "expense-policy.md": (
            "# Expense Reimbursement Policy\n\n"
            "Business expenses must be submitted within 30 days. Hotel maximum "
            "is $200 per night for standard markets. Meals while traveling are "
            "capped at $75 per day including tips. All expenses over $25 require "
            "a receipt.\n\n"
            "Client entertainment up to $100 per person requires director approval."
        ),
        "api-auth.md": (
            "# API Authentication Guide\n\n"
            "All API requests use OAuth 2.0 bearer tokens. Request a token via "
            "POST /oauth/token with your client_id and client_secret. Tokens "
            "expire after 30 minutes. Rate limit is 100 requests per minute.\n\n"
            "Never commit API keys or tokens to version control. Use environment "
            "variables or a secrets manager."
        ),
        "deployment-guide.md": (
            "# Production Deployment Guide\n\n"
            "Deployments follow a blue-green strategy with automatic rollback. "
            "All code must pass CI/CD tests and receive 2 reviewer approvals. "
            "Create a release branch from main, deploy to staging first, then "
            "promote to production after QA verification.\n\n"
            "Rollback triggers automatically if error rate exceeds 2% within "
            "10 minutes of deployment."
        ),
    }

    # Write documents to temp files and extract them
    tmp_dir = tempfile.mkdtemp()
    extractions = {}
    for filename, content in docs.items():
        path = Path(tmp_dir) / filename
        path.write_text(content, encoding="utf-8")
        extractions[filename] = extract_document(path)

    yield extractions

    # Cleanup
    import shutil
    shutil.rmtree(tmp_dir)


@pytest.fixture(scope="module")
def embedded_chunks(sample_docs):
    """Chunk and embed all sample documents."""
    all_chunks = []
    for filename, extraction in sample_docs.items():
        chunking = chunk_document(extraction, chunk_size=500, chunk_overlap=50)
        all_chunks.extend(chunking.chunks)

    # Embed all chunks
    texts = [c.text for c in all_chunks]
    embeddings = embed_texts(texts)

    return list(zip(all_chunks, embeddings.embeddings))


class TestRetrievalQuality:
    """Test that queries retrieve the correct documents."""

    # Labeled test queries: (query, expected_doc_name)
    TEST_QUERIES = [
        ("How many days of annual leave do employees get?", "leave-policy.md"),
        ("What is the password length requirement?", "password-policy.md"),
        ("What is the maximum hotel rate for business travel?", "expense-policy.md"),
        ("How do I authenticate API requests?", "api-auth.md"),
        ("How does the deployment rollback work?", "deployment-guide.md"),
        ("What is the sick leave policy?", "leave-policy.md"),
        ("How often do passwords expire?", "password-policy.md"),
        ("What is the meal limit while traveling?", "expense-policy.md"),
        ("What is the API rate limit?", "api-auth.md"),
        ("How many reviewer approvals are needed for deployment?", "deployment-guide.md"),
    ]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def test_precision_at_1(self, embedded_chunks):
        """The top-1 result should be from the correct document."""
        correct = 0
        total = len(self.TEST_QUERIES)

        for query, expected_doc in self.TEST_QUERIES:
            query_embedding = embed_single(query)

            # Rank all chunks by similarity
            scored = []
            for chunk, embedding in embedded_chunks:
                sim = self._cosine_similarity(query_embedding, embedding)
                scored.append((sim, chunk))

            scored.sort(key=lambda x: x[0], reverse=True)
            top_result = scored[0][1]

            if top_result.doc_name == expected_doc:
                correct += 1

        precision_at_1 = correct / total
        # We expect at least 80% P@1 on these clear-cut queries
        assert precision_at_1 >= 0.8, (
            f"Precision@1 too low: {precision_at_1:.0%} ({correct}/{total})"
        )

    def test_precision_at_5(self, embedded_chunks):
        """At least one of the top-5 results should be from the correct document."""
        correct = 0
        total = len(self.TEST_QUERIES)

        for query, expected_doc in self.TEST_QUERIES:
            query_embedding = embed_single(query)

            scored = []
            for chunk, embedding in embedded_chunks:
                sim = self._cosine_similarity(query_embedding, embedding)
                scored.append((sim, chunk))

            scored.sort(key=lambda x: x[0], reverse=True)
            top_5_docs = {scored[i][1].doc_name for i in range(min(5, len(scored)))}

            if expected_doc in top_5_docs:
                correct += 1

        recall_at_5 = correct / total
        # Top-5 should contain the right doc for all queries
        assert recall_at_5 >= 0.9, (
            f"Recall@5 too low: {recall_at_5:.0%} ({correct}/{total})"
        )
