#!/usr/bin/env npx tsx
/**
 * Interactive CLI demo — shows cache hits, source attribution, and search.
 *
 * Usage:
 *   npx tsx demo/demo.ts
 *
 * Requirements:
 *   - API server running on port 3000
 *   - Redis running
 *   - Ingestion service with documents loaded
 */

import * as readline from "readline";

const API_URL = process.env.API_URL ?? "http://localhost:3000";
const USER_ID = "demo-user";
const SESSION_ID = `demo-${Date.now()}`;

async function chat(query: string, filters?: { category?: string }) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      userId: USER_ID,
      sessionId: SESSION_ID,
      filters,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API error (${res.status}): ${err}`);
  }

  return res.json() as Promise<{
    answer: string;
    sources: Array<{ docName: string; pageNumber: number; score: number }>;
    metadata: {
      cached: boolean;
      searchTimeMs: number;
      generationTimeMs: number;
      totalTimeMs: number;
    };
  }>;
}

async function getMetrics() {
  const res = await fetch(`${API_URL}/chat/metrics`);
  return res.json() as Promise<{
    hits: number;
    misses: number;
    hitRate: number;
  }>;
}

async function getStats() {
  const res = await fetch(`${API_URL}/documents/stats`);
  return res.json() as Promise<{
    totalDocuments: number;
    totalChunks: number;
    avgChunksPerDoc: number;
    categoryCounts: Record<string, number>;
  }>;
}

function printHeader() {
  console.log(`
+--------------------------------------------------+
|     Document Intelligence RAG — Interactive Demo   |
+--------------------------------------------------+
|  Commands:                                         |
|    /stats    - Show collection statistics           |
|    /metrics  - Show cache metrics                   |
|    /filter <category> - Set category filter         |
|    /clear    - Clear category filter                |
|    /quit     - Exit                                 |
+--------------------------------------------------+
`);
}

async function main() {
  printHeader();

  // Check health
  try {
    const health = await fetch(`${API_URL}/health`);
    const data = await health.json() as { status: string; services: Record<string, string> };
    console.log(`Status: ${data.status}`);
    console.log(`Services: ${JSON.stringify(data.services)}\n`);
  } catch (e) {
    console.error(`Cannot connect to API server at ${API_URL}`);
    console.error("Make sure the server is running: npm run dev");
    process.exit(1);
  }

  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  let activeFilter: { category?: string } | undefined;

  function prompt() {
    const filterStr = activeFilter?.category
      ? ` [filter: ${activeFilter.category}]`
      : "";
    rl.question(`\nYou${filterStr}> `, async (input) => {
      const trimmed = input.trim();

      if (!trimmed) {
        prompt();
        return;
      }

      // Handle commands
      if (trimmed === "/quit" || trimmed === "/exit") {
        console.log("Goodbye!");
        rl.close();
        process.exit(0);
      }

      if (trimmed === "/stats") {
        try {
          const stats = await getStats();
          console.log("\n--- Collection Statistics ---");
          console.log(`  Documents: ${stats.totalDocuments}`);
          console.log(`  Total chunks: ${stats.totalChunks}`);
          console.log(`  Avg chunks/doc: ${stats.avgChunksPerDoc}`);
          console.log(`  Categories:`);
          for (const [cat, count] of Object.entries(stats.categoryCounts)) {
            console.log(`    ${cat}: ${count}`);
          }
        } catch (e) {
          console.error("Failed to get stats:", (e as Error).message);
        }
        prompt();
        return;
      }

      if (trimmed === "/metrics") {
        try {
          const metrics = await getMetrics();
          console.log("\n--- Cache Metrics ---");
          console.log(`  Hits: ${metrics.hits}`);
          console.log(`  Misses: ${metrics.misses}`);
          console.log(`  Hit Rate: ${metrics.hitRate.toFixed(1)}%`);
        } catch (e) {
          console.error("Failed to get metrics:", (e as Error).message);
        }
        prompt();
        return;
      }

      if (trimmed.startsWith("/filter ")) {
        activeFilter = { category: trimmed.slice(8).trim() };
        console.log(`Filter set to: ${activeFilter.category}`);
        prompt();
        return;
      }

      if (trimmed === "/clear") {
        activeFilter = undefined;
        console.log("Filter cleared.");
        prompt();
        return;
      }

      // Regular query
      try {
        const start = Date.now();
        const result = await chat(trimmed, activeFilter);
        const elapsed = Date.now() - start;

        console.log("\n--- Answer ---");
        console.log(result.answer);

        console.log("\n--- Sources ---");
        for (const source of result.sources) {
          console.log(
            `  [${source.score.toFixed(3)}] ${source.docName}, Page ${source.pageNumber}`
          );
        }

        console.log("\n--- Performance ---");
        console.log(
          `  ${result.metadata.cached ? "CACHED" : "GENERATED"} | ` +
            `Search: ${result.metadata.searchTimeMs}ms | ` +
            `LLM: ${result.metadata.generationTimeMs}ms | ` +
            `Total: ${result.metadata.totalTimeMs}ms (client: ${elapsed}ms)`
        );
      } catch (e) {
        console.error("Error:", (e as Error).message);
      }

      prompt();
    });
  }

  prompt();
}

main().catch(console.error);
