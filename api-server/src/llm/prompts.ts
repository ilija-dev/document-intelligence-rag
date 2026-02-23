/**
 * RAG-specific system prompts.
 *
 * The system prompt is critical for RAG quality. It must:
 * 1. Instruct the LLM to answer ONLY from the provided context
 * 2. Require source attribution (document name + page)
 * 3. Handle "I don't know" gracefully when context is insufficient
 * 4. Prevent hallucination by grounding answers in retrieved chunks
 */

import type { SearchChunk } from "../search/hybrid-search.js";

export const RAG_SYSTEM_PROMPT = `You are a knowledgeable document assistant that answers questions based ONLY on the provided context documents.

RULES:
1. Answer ONLY using information from the provided context. Do NOT use prior knowledge.
2. If the context doesn't contain enough information to answer, say: "I don't have enough information in the available documents to answer this question."
3. Always cite your sources using the format: [Source: document_name, Page X]
4. If multiple documents contain relevant information, synthesize them and cite all sources.
5. Be concise and direct. Use bullet points for lists.
6. If the question is ambiguous, briefly mention what you found and ask for clarification.

RESPONSE FORMAT:
- Start with a direct answer
- Follow with supporting details from the context
- End with source citations`;

/**
 * Build the user message with retrieved context chunks.
 *
 * The context is formatted as numbered blocks with clear document
 * attribution so the LLM can cite specific sources.
 */
export function buildContextPrompt(
  query: string,
  chunks: SearchChunk[]
): string {
  if (chunks.length === 0) {
    return `Question: ${query}\n\nContext: No relevant documents were found.`;
  }

  const contextBlocks = chunks
    .map(
      (chunk, i) =>
        `[${i + 1}] Document: "${chunk.docName}" | Page: ${chunk.pageNumber} | Category: ${chunk.category}
---
${chunk.text}
---`
    )
    .join("\n\n");

  return `Question: ${query}

Context Documents:
${contextBlocks}

Please answer the question using ONLY the information from the context documents above. Cite your sources.`;
}

/**
 * Build the full message array for the LLM call.
 */
export function buildMessages(
  query: string,
  chunks: SearchChunk[],
  conversationHistory: Array<{ role: string; content: string }> = []
): Array<{ role: "system" | "user" | "assistant"; content: string }> {
  const messages: Array<{
    role: "system" | "user" | "assistant";
    content: string;
  }> = [{ role: "system", content: RAG_SYSTEM_PROMPT }];

  // Add conversation history for multi-turn context
  for (const msg of conversationHistory.slice(-10)) {
    messages.push({
      role: msg.role as "user" | "assistant",
      content: msg.content,
    });
  }

  // Add the current query with context
  messages.push({
    role: "user",
    content: buildContextPrompt(query, chunks),
  });

  return messages;
}
