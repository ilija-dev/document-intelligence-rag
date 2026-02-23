/**
 * Tests for the search and query routing logic.
 *
 * These are unit tests that mock external dependencies (Redis, ingestion
 * service, LLM). Integration tests with real services are in integration.test.ts.
 */

import { describe, it, expect } from "vitest";
import { buildContextPrompt, buildMessages, RAG_SYSTEM_PROMPT } from "../src/llm/prompts.js";
import type { SearchChunk } from "../src/search/hybrid-search.js";

const sampleChunks: SearchChunk[] = [
  {
    chunkId: "abc123",
    text: "All employees are entitled to 20 days of paid annual leave per year.",
    score: 0.92,
    docName: "leave-policy.pdf",
    pageNumber: 3,
    category: "hr_policy",
    chunkIndex: 5,
  },
  {
    chunkId: "def456",
    text: "Sick leave is 10 days per year. A medical certificate is required for absences exceeding 3 days.",
    score: 0.85,
    docName: "leave-policy.pdf",
    pageNumber: 4,
    category: "hr_policy",
    chunkIndex: 7,
  },
];

describe("buildContextPrompt", () => {
  it("should include query and all chunks", () => {
    const prompt = buildContextPrompt("How many leave days?", sampleChunks);
    expect(prompt).toContain("How many leave days?");
    expect(prompt).toContain("leave-policy.pdf");
    expect(prompt).toContain("20 days of paid annual leave");
    expect(prompt).toContain("Sick leave is 10 days");
  });

  it("should number chunks sequentially", () => {
    const prompt = buildContextPrompt("test", sampleChunks);
    expect(prompt).toContain("[1]");
    expect(prompt).toContain("[2]");
  });

  it("should include page numbers for source attribution", () => {
    const prompt = buildContextPrompt("test", sampleChunks);
    expect(prompt).toContain("Page: 3");
    expect(prompt).toContain("Page: 4");
  });

  it("should handle empty chunks gracefully", () => {
    const prompt = buildContextPrompt("test query", []);
    expect(prompt).toContain("No relevant documents were found");
  });
});

describe("buildMessages", () => {
  it("should start with system prompt", () => {
    const messages = buildMessages("test", sampleChunks);
    expect(messages[0].role).toBe("system");
    expect(messages[0].content).toBe(RAG_SYSTEM_PROMPT);
  });

  it("should end with user message containing context", () => {
    const messages = buildMessages("test", sampleChunks);
    const lastMsg = messages[messages.length - 1];
    expect(lastMsg.role).toBe("user");
    expect(lastMsg.content).toContain("leave-policy.pdf");
  });

  it("should include conversation history", () => {
    const history = [
      { role: "user", content: "What is the leave policy?" },
      { role: "assistant", content: "Employees get 20 days." },
    ];
    const messages = buildMessages("follow up question", sampleChunks, history);
    // System + 2 history + 1 current = 4 messages
    expect(messages.length).toBe(4);
    expect(messages[1].content).toBe("What is the leave policy?");
    expect(messages[2].content).toBe("Employees get 20 days.");
  });

  it("should limit conversation history to last 10 messages", () => {
    const history = Array.from({ length: 20 }, (_, i) => ({
      role: i % 2 === 0 ? "user" : "assistant",
      content: `Message ${i}`,
    }));
    const messages = buildMessages("test", sampleChunks, history);
    // System + 10 history + 1 current = 12 messages
    expect(messages.length).toBe(12);
  });
});

describe("RAG_SYSTEM_PROMPT", () => {
  it("should instruct LLM to use only provided context", () => {
    expect(RAG_SYSTEM_PROMPT).toContain("ONLY");
    expect(RAG_SYSTEM_PROMPT).toContain("provided context");
  });

  it("should require source citations", () => {
    expect(RAG_SYSTEM_PROMPT).toContain("[Source:");
  });

  it("should handle unknown answers", () => {
    expect(RAG_SYSTEM_PROMPT).toContain("don't have enough information");
  });
});
