/**
 * Integration tests — end-to-end query flow.
 *
 * These tests require Redis + ingestion service running.
 * Skip them in CI with: npx vitest run --exclude tests/integration.test.ts
 *
 * For now, these serve as documentation of the expected integration behavior.
 */

import { describe, it, expect } from "vitest";

// Mark all integration tests as skipped by default
// Enable by running: INTEGRATION=true npx vitest run tests/integration.test.ts
const runIntegration = process.env.INTEGRATION === "true";

describe.skipIf(!runIntegration)("Integration: Full Query Flow", () => {
  const API_URL = `http://localhost:${process.env.API_PORT ?? 3000}`;

  it("should return health status", async () => {
    const res = await fetch(`${API_URL}/health`);
    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data.status).toBeDefined();
  });

  it("should answer a query with sources", async () => {
    const res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "What is the employee leave policy?",
        userId: "test-user",
        sessionId: "test-session",
      }),
    });

    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data.answer).toBeDefined();
    expect(data.sources).toBeInstanceOf(Array);
    expect(data.metadata.cached).toBe(false); // First query should be a miss
  });

  it("should return cached response on repeat query", async () => {
    // Second identical query should hit cache
    const res = await fetch(`${API_URL}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: "What is the employee leave policy?",
        userId: "test-user",
        sessionId: "test-session",
      }),
    });

    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data.metadata.cached).toBe(true);
    expect(data.metadata.totalTimeMs).toBeLessThan(200); // Cached should be fast
  });

  it("should list ingested documents", async () => {
    const res = await fetch(`${API_URL}/documents`);
    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data.totalDocuments).toBeGreaterThan(0);
    expect(data.documents).toBeInstanceOf(Array);
  });

  it("should return cache metrics", async () => {
    const res = await fetch(`${API_URL}/chat/metrics`);
    expect(res.ok).toBe(true);
    const data = await res.json();
    expect(data.hits).toBeDefined();
    expect(data.misses).toBeDefined();
    expect(data.hitRate).toBeDefined();
  });
});
