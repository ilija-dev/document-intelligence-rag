/**
 * POST /chat — the main query endpoint.
 *
 * Accepts a user query with optional filters and session info,
 * routes through the full RAG pipeline (cache → search → generate → cache),
 * and returns the answer with source attribution.
 */

import { Router, type Request, type Response } from "express";
import { z } from "zod";
import { processQuery } from "../search/query-router.js";
import { getCacheMetrics } from "../cache/cache-strategy.js";

export const chatRouter = Router();

// ── Request validation ─────────────────────────────────────

const chatRequestSchema = z.object({
  query: z.string().min(1).max(1000),
  userId: z.string().optional().default("anonymous"),
  sessionId: z.string().optional().default("default"),
  filters: z
    .object({
      category: z.string().optional(),
      docName: z.string().optional(),
    })
    .optional(),
});

// ── POST /chat ─────────────────────────────────────────────

chatRouter.post("/", async (req: Request, res: Response): Promise<void> => {
  const start = Date.now();

  // Validate request
  const parsed = chatRequestSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({
      error: "Invalid request",
      details: parsed.error.format(),
    });
    return;
  }

  const { query, userId, sessionId, filters } = parsed.data;

  try {
    const result = await processQuery({
      query,
      userId,
      sessionId,
      filters,
    });

    res.json({
      answer: result.answer,
      sources: result.sources,
      metadata: {
        cached: result.cached,
        searchTimeMs: result.searchTimeMs,
        generationTimeMs: result.generationTimeMs,
        totalTimeMs: result.totalTimeMs,
      },
    });
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : String(error);
    console.error("[Chat] Error processing query:", errMsg);

    res.status(500).json({
      error: "Failed to process query",
      message: errMsg,
    });
  }
});

// ── GET /chat/metrics — cache performance metrics ──────────

chatRouter.get("/metrics", (_req: Request, res: Response) => {
  res.json(getCacheMetrics());
});
