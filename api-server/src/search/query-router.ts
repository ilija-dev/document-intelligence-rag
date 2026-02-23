/**
 * Query Router — the full query processing flow.
 *
 * This is the central orchestrator:
 *   query → normalize → check Redis cache
 *     → HIT: return cached response (< 100ms)
 *     → MISS: hybrid search → LLM generate → cache result → return
 *
 * The router also records the query in conversation history for
 * multi-turn context and analytics.
 */

import {
  getCachedResponse,
  setCachedResponse,
  type CachedResponse,
} from "../cache/cache-strategy.js";
import { hybridSearch, type SearchFilters, type SearchChunk } from "./hybrid-search.js";
import { generateAnswer } from "../llm/generator.js";
import { saveConversation, getConversationHistory } from "../history/conversation.js";

// ── Types ──────────────────────────────────────────────────

export interface QueryRequest {
  query: string;
  userId?: string;
  sessionId?: string;
  filters?: SearchFilters;
}

export interface QueryResponse {
  answer: string;
  sources: Array<{
    docName: string;
    pageNumber: number;
    chunkText: string;
    score: number;
  }>;
  cached: boolean;
  searchTimeMs: number;
  generationTimeMs: number;
  totalTimeMs: number;
}

// ── Query Processing ───────────────────────────────────────

/**
 * Process a user query through the full RAG pipeline.
 *
 * Flow:
 * 1. Check Redis cache (normalized query as key)
 * 2. On HIT → return immediately (<100ms)
 * 3. On MISS → hybrid search → LLM generation → cache → return
 */
export async function processQuery(
  request: QueryRequest
): Promise<QueryResponse> {
  const totalStart = Date.now();
  const { query, userId, sessionId, filters } = request;

  // ── Step 1: Check cache ──────────────────────────────────
  const cached = await getCachedResponse(query, filters);
  if (cached) {
    console.log(`[QueryRouter] Cache HIT for query: "${query.slice(0, 50)}..."`);

    // Record in history even for cached responses
    if (userId) {
      await saveConversation({
        userId,
        sessionId: sessionId ?? "default",
        query,
        response: cached.answer,
        sources: cached.sources,
        wasCached: true,
        searchTimeMs: 0,
        generationTimeMs: 0,
      });
    }

    return {
      answer: cached.answer,
      sources: cached.sources,
      cached: true,
      searchTimeMs: 0,
      generationTimeMs: cached.generationTimeMs,
      totalTimeMs: Date.now() - totalStart,
    };
  }

  console.log(`[QueryRouter] Cache MISS for query: "${query.slice(0, 50)}..."`);

  // ── Step 2: Hybrid search ────────────────────────────────
  const searchResult = await hybridSearch(query, filters);

  // ── Step 3: Get conversation history for context ─────────
  let conversationHistory: Array<{ role: string; content: string }> = [];
  if (userId && sessionId) {
    const history = await getConversationHistory(userId, sessionId, 5);
    conversationHistory = history.flatMap((h) => [
      { role: "user", content: h.query },
      { role: "assistant", content: h.response },
    ]);
  }

  // ── Step 4: Generate answer with LLM ─────────────────────
  const genStart = Date.now();
  const answer = await generateAnswer(
    query,
    searchResult.chunks,
    conversationHistory
  );
  const generationTimeMs = Date.now() - genStart;

  // ── Step 5: Build sources list ───────────────────────────
  const sources = searchResult.chunks.map((chunk) => ({
    docName: chunk.docName,
    pageNumber: chunk.pageNumber,
    chunkText: chunk.text.slice(0, 200) + (chunk.text.length > 200 ? "..." : ""),
    score: Math.round(chunk.score * 1000) / 1000,
  }));

  // ── Step 6: Cache the response ───────────────────────────
  const cacheEntry: CachedResponse = {
    answer,
    sources,
    cachedAt: new Date().toISOString(),
    generationTimeMs,
  };
  await setCachedResponse(query, cacheEntry, filters);

  // ── Step 7: Record in conversation history ───────────────
  if (userId) {
    await saveConversation({
      userId,
      sessionId: sessionId ?? "default",
      query,
      response: answer,
      sources,
      wasCached: false,
      searchTimeMs: searchResult.searchTimeMs,
      generationTimeMs,
    });
  }

  return {
    answer,
    sources,
    cached: false,
    searchTimeMs: searchResult.searchTimeMs,
    generationTimeMs,
    totalTimeMs: Date.now() - totalStart,
  };
}
