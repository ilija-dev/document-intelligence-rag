#!/usr/bin/env python3
"""
Retrieval quality benchmark: Precision@k and Recall@k.

Tests the search pipeline against labeled queries with known relevant
documents. This is the most important benchmark because it measures
whether the RAG system actually returns the right information.

Usage:
    python benchmarks/retrieval_quality.py

Requirements:
    - Ingestion service running with sample docs loaded
"""

import json
import sys
import time
from dataclasses import dataclass

try:
    import httpx
except ImportError:
    print("Install httpx: pip install httpx")
    sys.exit(1)

INGESTION_URL = "http://localhost:8100"

# ── Labeled test queries ────────────────────────────────────
# Each entry: (query, list of expected doc name substrings)
LABELED_QUERIES = [
    (
        "How many days of annual leave do employees get?",
        ["leave-policy", "hr-employee-leave"],
    ),
    (
        "What is the password minimum length?",
        ["password", "information-security", "it-"],
    ),
    (
        "What is the hotel rate limit for business travel?",
        ["expense", "travel", "finance"],
    ),
    (
        "How do I authenticate API requests with OAuth?",
        ["api-auth", "api-reference", "product-api"],
    ),
    (
        "What is the deployment rollback procedure?",
        ["deploy", "production", "kb-how-to-deploy"],
    ),
    (
        "What is the sick leave policy?",
        ["leave-policy", "hr-employee-leave"],
    ),
    (
        "How often do passwords expire?",
        ["password", "security", "it-"],
    ),
    (
        "What is the meal limit while traveling?",
        ["expense", "travel", "finance"],
    ),
    (
        "What are the code review requirements?",
        ["development-standards", "software", "it-software"],
    ),
    (
        "What is the VPN encryption protocol?",
        ["vpn", "remote-access", "it-vpn"],
    ),
    (
        "How does the performance review process work?",
        ["performance-review", "hr-performance"],
    ),
    (
        "What is the procurement approval threshold?",
        ["procurement", "finance"],
    ),
    (
        "What are the remote work eligibility requirements?",
        ["remote-work", "hr-remote"],
    ),
    (
        "What is the 401k company match percentage?",
        ["benefits", "compensation", "faq", "kb-faq"],
    ),
    (
        "What is the client entertainment expense limit?",
        ["expense", "finance"],
    ),
    (
        "How do I set up my development environment?",
        ["development-environment", "setup", "kb-how-to-set"],
    ),
    (
        "What is the code of conduct gift limit?",
        ["code-of-conduct", "hr-code"],
    ),
    (
        "What is the onboarding process for new employees?",
        ["onboarding", "hr-onboarding"],
    ),
    (
        "What is the API rate limit?",
        ["api", "product-api", "product-troubleshooting"],
    ),
    (
        "What were the Q4 2024 revenue numbers?",
        ["meeting-q4-2024", "q4-2024"],
    ),
]


@dataclass
class QueryResult:
    query: str
    expected_docs: list[str]
    retrieved_docs: list[str]
    relevant_in_top1: bool
    relevant_in_top5: bool
    search_time_ms: float


def is_relevant(doc_name: str, expected_patterns: list[str]) -> bool:
    """Check if a retrieved doc matches any expected pattern."""
    doc_lower = doc_name.lower()
    return any(pattern.lower() in doc_lower for pattern in expected_patterns)


def run_benchmark():
    print("=== Document Intelligence RAG — Retrieval Quality Benchmark ===\n")

    client = httpx.Client(base_url=INGESTION_URL, timeout=30)

    # Check service health
    try:
        health = client.get("/health")
        health.raise_for_status()
    except Exception as e:
        print(f"Ingestion service not available: {e}")
        sys.exit(1)

    # Get collection stats
    stats = client.get("/stats").json()
    print(f"Collection: {stats['total_documents']} documents, {stats['total_chunks']} chunks\n")

    results: list[QueryResult] = []

    for query, expected_docs in LABELED_QUERIES:
        try:
            start = time.time()
            response = client.post(
                "/search",
                json={"query": query, "n_results": 5},
            )
            elapsed_ms = (time.time() - start) * 1000
            response.raise_for_status()
            data = response.json()

            retrieved = [r["doc_name"] for r in data["results"]]
            top1_relevant = len(retrieved) > 0 and is_relevant(retrieved[0], expected_docs)
            top5_relevant = any(is_relevant(doc, expected_docs) for doc in retrieved[:5])

            result = QueryResult(
                query=query,
                expected_docs=expected_docs,
                retrieved_docs=retrieved[:5],
                relevant_in_top1=top1_relevant,
                relevant_in_top5=top5_relevant,
                search_time_ms=elapsed_ms,
            )
            results.append(result)

            status = "OK" if top5_relevant else "MISS"
            print(f"  [{status}] {query[:60]}")
            if not top5_relevant:
                print(f"       Expected: {expected_docs}")
                print(f"       Got: {retrieved[:3]}")

        except Exception as e:
            print(f"  [ERR] {query[:60]}: {e}")

    # Summary
    total = len(results)
    p_at_1 = sum(1 for r in results if r.relevant_in_top1) / total if total else 0
    p_at_5 = sum(1 for r in results if r.relevant_in_top5) / total if total else 0
    avg_time = sum(r.search_time_ms for r in results) / total if total else 0

    print(f"\n=== Results ({total} queries) ===\n")
    print(f"  Precision@1: {p_at_1:.0%} ({sum(1 for r in results if r.relevant_in_top1)}/{total})")
    print(f"  Recall@5:    {p_at_5:.0%} ({sum(1 for r in results if r.relevant_in_top5)}/{total})")
    print(f"  Avg search:  {avg_time:.0f}ms")
    print()

    if p_at_5 < 0.8:
        print("WARNING: Recall@5 below 80% — check chunking parameters or embedding model")
    else:
        print("Retrieval quality is within acceptable thresholds.")


if __name__ == "__main__":
    run_benchmark()
