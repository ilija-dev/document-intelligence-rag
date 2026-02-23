#!/usr/bin/env npx tsx
/**
 * Latency benchmark: measure P50/P95 with and without cache.
 *
 * This script demonstrates the ~70% latency reduction from caching.
 * It sends the same queries twice — first to warm the cache, then
 * to measure cached latency — and compares the results.
 *
 * Usage:
 *   npx tsx benchmarks/latency_test.ts
 *
 * Requirements:
 *   - API server running on port 3000
 *   - Redis running
 *   - Ingestion service with documents loaded
 */

const API_URL = process.env.API_URL ?? "http://localhost:3000";

const TEST_QUERIES = [
  "What is the employee leave policy?",
  "How many days of sick leave do employees get?",
  "What is the password policy?",
  "What are the expense reimbursement limits?",
  "How do I authenticate API requests?",
  "What is the deployment rollback procedure?",
  "What is the hotel rate for business travel?",
  "How does the performance review process work?",
  "What are the VPN requirements for remote access?",
  "What is the procurement approval process?",
  "How do I set up my development environment?",
  "What are the code review standards?",
  "What is the remote work policy?",
  "What are the 401k matching details?",
  "How many PTO days do I get in year 3?",
];

interface LatencyResult {
  query: string;
  uncachedMs: number;
  cachedMs: number;
  reduction: number;
}

async function sendQuery(query: string): Promise<{ timeMs: number; cached: boolean }> {
  const start = Date.now();
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      userId: "benchmark",
      sessionId: "latency-test",
    }),
  });

  const elapsed = Date.now() - start;
  const data = await res.json() as { metadata: { cached: boolean } };
  return { timeMs: elapsed, cached: data.metadata?.cached ?? false };
}

function percentile(arr: number[], p: number): number {
  const sorted = [...arr].sort((a, b) => a - b);
  const idx = Math.ceil((p / 100) * sorted.length) - 1;
  return sorted[Math.max(0, idx)];
}

async function runBenchmark() {
  console.log("=== Document Intelligence RAG — Latency Benchmark ===\n");
  console.log(`Target: ${API_URL}`);
  console.log(`Queries: ${TEST_QUERIES.length}\n`);

  // First, invalidate all caches
  try {
    await fetch(`${API_URL}/documents/invalidate-cache`, { method: "POST" });
    console.log("Cache invalidated.\n");
  } catch (e) {
    console.warn("Could not invalidate cache:", (e as Error).message);
  }

  const results: LatencyResult[] = [];

  // Phase 1: Uncached queries
  console.log("--- Phase 1: Uncached Queries (cold) ---");
  const uncachedTimes: number[] = [];

  for (const query of TEST_QUERIES) {
    try {
      const result = await sendQuery(query);
      uncachedTimes.push(result.timeMs);
      console.log(`  ${result.timeMs}ms | ${query.slice(0, 50)}`);
    } catch (e) {
      console.error(`  FAILED | ${query.slice(0, 50)}: ${(e as Error).message}`);
      uncachedTimes.push(-1);
    }
  }

  // Phase 2: Cached queries (same queries again)
  console.log("\n--- Phase 2: Cached Queries (warm) ---");
  const cachedTimes: number[] = [];

  for (const query of TEST_QUERIES) {
    try {
      const result = await sendQuery(query);
      cachedTimes.push(result.timeMs);
      console.log(`  ${result.timeMs}ms ${result.cached ? "(CACHED)" : "(MISS)"} | ${query.slice(0, 50)}`);
    } catch (e) {
      console.error(`  FAILED | ${query.slice(0, 50)}: ${(e as Error).message}`);
      cachedTimes.push(-1);
    }
  }

  // Build results
  for (let i = 0; i < TEST_QUERIES.length; i++) {
    if (uncachedTimes[i] > 0 && cachedTimes[i] > 0) {
      results.push({
        query: TEST_QUERIES[i],
        uncachedMs: uncachedTimes[i],
        cachedMs: cachedTimes[i],
        reduction: Math.round(
          ((uncachedTimes[i] - cachedTimes[i]) / uncachedTimes[i]) * 100
        ),
      });
    }
  }

  // Summary
  const validUncached = uncachedTimes.filter((t) => t > 0);
  const validCached = cachedTimes.filter((t) => t > 0);

  console.log("\n=== Results ===\n");
  console.log("Uncached (cold):");
  console.log(`  P50: ${percentile(validUncached, 50)}ms`);
  console.log(`  P95: ${percentile(validUncached, 95)}ms`);
  console.log(`  Avg: ${Math.round(validUncached.reduce((a, b) => a + b, 0) / validUncached.length)}ms`);

  console.log("\nCached (warm):");
  console.log(`  P50: ${percentile(validCached, 50)}ms`);
  console.log(`  P95: ${percentile(validCached, 95)}ms`);
  console.log(`  Avg: ${Math.round(validCached.reduce((a, b) => a + b, 0) / validCached.length)}ms`);

  const avgReduction =
    results.length > 0
      ? Math.round(results.reduce((a, b) => a + b.reduction, 0) / results.length)
      : 0;
  console.log(`\nAverage latency reduction: ${avgReduction}%`);

  // Get cache metrics
  try {
    const metricsRes = await fetch(`${API_URL}/chat/metrics`);
    const metrics = await metricsRes.json();
    console.log("\nCache Metrics:");
    console.log(`  Hit Rate: ${(metrics as { hitRate: number }).hitRate.toFixed(1)}%`);
    console.log(`  Hits: ${(metrics as { hits: number }).hits}`);
    console.log(`  Misses: ${(metrics as { misses: number }).misses}`);
  } catch {
    // ignore
  }
}

runBenchmark().catch(console.error);
