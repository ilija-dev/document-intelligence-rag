/**
 * Hybrid search: combine vector similarity with metadata filtering.
 *
 * Pure vector similarity works for 4 documents. At 1,500+, you get false
 * positives — chunks that are semantically similar but from the wrong
 * category or time period. Hybrid search adds metadata filters: "find me
 * chunks about return policies" uses vector search, but "find me chunks
 * about return policies from the 2024 handbook" adds a metadata filter on
 * document date. This dramatically improves precision.
 *
 * The flow:
 *   1. Call the Python ingestion service's /search endpoint (top-20 candidates)
 *   2. Apply metadata filters (category, date, doc name)
 *   3. Re-rank by combining similarity score with metadata relevance
 *   4. Return top-5 chunks to the LLM
 */

import { config } from "../config.js";

// ── Types ──────────────────────────────────────────────────

export interface SearchFilters {
  category?: string;
  docName?: string;
  nResults?: number;
}

export interface SearchChunk {
  chunkId: string;
  text: string;
  score: number;
  docName: string;
  pageNumber: number;
  category: string;
  chunkIndex: number;
}

export interface HybridSearchResult {
  query: string;
  chunks: SearchChunk[];
  searchTimeMs: number;
  totalCandidates: number;
}

// ── Ingestion Service Client ───────────────────────────────

interface IngestionSearchResponse {
  query: string;
  results: Array<{
    chunk_id: string;
    text: string;
    score: number;
    doc_name: string;
    page_number: number;
    category: string;
    chunk_index: number;
  }>;
  total_candidates: number;
  search_time_ms: number;
}

/**
 * Call the Python ingestion service for vector search.
 */
async function vectorSearch(
  query: string,
  filters: SearchFilters
): Promise<IngestionSearchResponse> {
  const body: Record<string, unknown> = {
    query,
    n_results: filters.nResults ?? 20,
  };

  if (filters.category) body.category = filters.category;
  if (filters.docName) body.doc_name = filters.docName;

  const response = await fetch(`${config.ingestion.baseUrl}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(
      `Ingestion service search failed (${response.status}): ${error}`
    );
  }

  return (await response.json()) as IngestionSearchResponse;
}

// ── Re-ranking ─────────────────────────────────────────────

/**
 * Re-rank search results by combining vector similarity with
 * diversity and position penalties.
 *
 * The re-ranking logic:
 * 1. Base score from vector similarity (0-1)
 * 2. Diversity bonus: penalize chunks from the same document that
 *    are too close together (same page) to increase source diversity
 * 3. This ensures the LLM gets context from multiple perspectives
 */
function rerank(chunks: SearchChunk[]): SearchChunk[] {
  // Track which docs we've already included
  const docPageCounts = new Map<string, Set<number>>();

  return chunks
    .map((chunk) => {
      const key = chunk.docName;
      const pages = docPageCounts.get(key) ?? new Set();

      // Penalize duplicate pages from the same document
      let adjustedScore = chunk.score;
      if (pages.has(chunk.pageNumber)) {
        adjustedScore *= 0.7; // 30% penalty for same doc+page
      } else if (pages.size > 0) {
        adjustedScore *= 0.9; // 10% penalty for same doc, different page
      }

      pages.add(chunk.pageNumber);
      docPageCounts.set(key, pages);

      return { ...chunk, score: adjustedScore };
    })
    .sort((a, b) => b.score - a.score);
}

// ── Main Search Function ───────────────────────────────────

/**
 * Perform hybrid search: vector similarity + metadata filtering + re-ranking.
 *
 * Returns the top-5 most relevant chunks for the LLM context window.
 */
export async function hybridSearch(
  query: string,
  filters: SearchFilters = {}
): Promise<HybridSearchResult> {
  const start = Date.now();

  // Step 1: Get top-20 candidates from vector search
  const rawResults = await vectorSearch(query, {
    ...filters,
    nResults: 20,
  });

  // Step 2: Map to our internal type
  let chunks: SearchChunk[] = rawResults.results.map((r) => ({
    chunkId: r.chunk_id,
    text: r.text,
    score: r.score,
    docName: r.doc_name,
    pageNumber: r.page_number,
    category: r.category,
    chunkIndex: r.chunk_index,
  }));

  // Step 3: Re-rank for diversity
  chunks = rerank(chunks);

  // Step 4: Return top-5 for LLM context
  const topK = filters.nResults ?? 5;
  chunks = chunks.slice(0, topK);

  const elapsed = Date.now() - start;

  return {
    query,
    chunks,
    searchTimeMs: elapsed,
    totalCandidates: rawResults.total_candidates,
  };
}
