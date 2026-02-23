/**
 * LLM answer generation with retrieved context.
 *
 * Uses the OpenAI-compatible API (works with both Ollama and Groq).
 * The key design choice: we inject retrieved chunks as structured context
 * in the user message, not as system prompt content. This keeps the system
 * prompt focused on behavior instructions while the user message carries
 * the variable context.
 */

import OpenAI from "openai";
import { config } from "../config.js";
import { buildMessages } from "./prompts.js";
import type { SearchChunk } from "../search/hybrid-search.js";

let client: OpenAI | null = null;

function getClient(): OpenAI {
  if (!client) {
    client = new OpenAI({
      baseURL: config.llm.baseUrl,
      apiKey: config.llm.apiKey,
    });
  }
  return client;
}

/**
 * Generate an answer using the LLM with retrieved chunks as context.
 *
 * Returns the generated text. If the LLM call fails, returns a
 * graceful error message rather than throwing.
 */
export async function generateAnswer(
  query: string,
  chunks: SearchChunk[],
  conversationHistory: Array<{ role: string; content: string }> = []
): Promise<string> {
  const messages = buildMessages(query, chunks, conversationHistory);

  try {
    const openai = getClient();
    const response = await openai.chat.completions.create({
      model: config.llm.model,
      messages,
      temperature: 0.3, // Low temperature for factual RAG responses
      max_tokens: 1024,
    });

    const content = response.choices[0]?.message?.content;
    if (!content) {
      return "I was unable to generate a response. Please try again.";
    }

    return content;
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : String(error);
    console.error("[Generator] LLM call failed:", errMsg);

    // Graceful degradation: return the raw context if LLM is unavailable
    if (chunks.length > 0) {
      const fallback = chunks
        .slice(0, 3)
        .map(
          (c) =>
            `From "${c.docName}" (Page ${c.pageNumber}):\n${c.text.slice(0, 300)}`
        )
        .join("\n\n---\n\n");

      return `I'm unable to process your question through the AI model right now, but here are the most relevant document excerpts:\n\n${fallback}\n\n(LLM error: ${errMsg})`;
    }

    return `I'm unable to process your question right now. Error: ${errMsg}`;
  }
}
