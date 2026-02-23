/**
 * Tests for cache key normalization and strategy.
 *
 * These tests verify the core caching logic WITHOUT requiring Redis.
 * The normalization tests are especially important because they validate
 * the key insight: different phrasings of the same question should
 * produce the same cache key.
 */

import { describe, it, expect } from "vitest";
import {
  normalizeQuery,
  generateCacheKey,
} from "../src/cache/cache-strategy.js";

describe("normalizeQuery", () => {
  it("should lowercase the query", () => {
    expect(normalizeQuery("HELLO WORLD")).toBe(normalizeQuery("hello world"));
  });

  it("should strip punctuation", () => {
    expect(normalizeQuery("What is the return policy?")).toBe(
      normalizeQuery("What is the return policy")
    );
  });

  it("should remove stop words", () => {
    const result = normalizeQuery("What is the return policy?");
    expect(result).not.toContain("what");
    expect(result).not.toContain("the");
    expect(result).toContain("return");
    expect(result).toContain("policy");
  });

  it("should sort words alphabetically", () => {
    const result = normalizeQuery("return policy");
    expect(result).toBe("policy return");
  });

  it("should produce same result for rephrased queries", () => {
    // These are the same question asked differently
    const v1 = normalizeQuery("What is the return policy?");
    const v2 = normalizeQuery("return policy what is");
    const v3 = normalizeQuery("the Return Policy");
    expect(v1).toBe(v2);
    expect(v2).toBe(v3);
  });

  it("should handle empty query", () => {
    expect(normalizeQuery("")).toBe("");
  });

  it("should handle query with only stop words", () => {
    const result = normalizeQuery("what is the");
    expect(result).toBe("");
  });

  it("should remove single-character words", () => {
    const result = normalizeQuery("I need a new policy");
    expect(result).not.toContain("a");
    expect(result).toContain("new");
    expect(result).toContain("policy");
  });
});

describe("generateCacheKey", () => {
  it("should generate consistent keys", () => {
    const key1 = generateCacheKey("What is the return policy?");
    const key2 = generateCacheKey("What is the return policy?");
    expect(key1).toBe(key2);
  });

  it("should generate same key for normalized-equivalent queries", () => {
    const key1 = generateCacheKey("What is the return policy?");
    const key2 = generateCacheKey("return policy what is");
    expect(key1).toBe(key2);
  });

  it("should generate different keys for different queries", () => {
    const key1 = generateCacheKey("return policy");
    const key2 = generateCacheKey("password requirements");
    expect(key1).not.toBe(key2);
  });

  it("should include filters in key generation", () => {
    const key1 = generateCacheKey("return policy", { category: "hr_policy" });
    const key2 = generateCacheKey("return policy", { category: "finance" });
    const key3 = generateCacheKey("return policy");
    expect(key1).not.toBe(key2);
    expect(key1).not.toBe(key3);
  });

  it("should prefix keys with 'rag:query:'", () => {
    const key = generateCacheKey("test query");
    expect(key).toMatch(/^rag:query:/);
  });

  it("should produce fixed-length hash in key", () => {
    const key1 = generateCacheKey("short");
    const key2 = generateCacheKey("a much longer query with many words");
    // Both should have same format: rag:query:<16-char-hash>
    expect(key1.length).toBe(key2.length);
  });
});
