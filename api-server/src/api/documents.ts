/**
 * Document management endpoints.
 *
 * GET  /documents       — list all ingested documents
 * GET  /documents/stats — collection statistics
 * POST /documents/ingest — proxy file upload to ingestion service
 */

import { Router, type Request, type Response } from "express";
import { config } from "../config.js";
import { invalidateOnIngestion } from "../cache/cache-strategy.js";

export const documentsRouter = Router();

// ── Types from ingestion service ───────────────────────────

interface StatsResponse {
  total_chunks: number;
  total_documents: number;
  documents: Array<{
    doc_name: string;
    category: string;
    chunk_count: number;
    ingestion_date: string;
  }>;
}

// ── GET /documents ─────────────────────────────────────────

documentsRouter.get("/", async (_req: Request, res: Response): Promise<void> => {
  try {
    const response = await fetch(`${config.ingestion.baseUrl}/stats`);

    if (!response.ok) {
      res.status(502).json({
        error: "Ingestion service unavailable",
        status: response.status,
      });
      return;
    }

    const stats = (await response.json()) as StatsResponse;

    res.json({
      totalDocuments: stats.total_documents,
      totalChunks: stats.total_chunks,
      documents: stats.documents.map((doc) => ({
        name: doc.doc_name,
        category: doc.category,
        chunkCount: doc.chunk_count,
        ingestedAt: doc.ingestion_date,
      })),
    });
  } catch (error) {
    const errMsg = error instanceof Error ? error.message : String(error);
    console.error("[Documents] Error fetching stats:", errMsg);

    res.status(502).json({
      error: "Failed to connect to ingestion service",
      message: errMsg,
    });
  }
});

// ── GET /documents/stats ───────────────────────────────────

documentsRouter.get(
  "/stats",
  async (_req: Request, res: Response): Promise<void> => {
    try {
      const response = await fetch(`${config.ingestion.baseUrl}/stats`);

      if (!response.ok) {
        res.status(502).json({ error: "Ingestion service unavailable" });
        return;
      }

      const stats = (await response.json()) as StatsResponse;

      // Compute additional analytics
      const avgChunksPerDoc =
        stats.total_documents > 0
          ? Math.round(stats.total_chunks / stats.total_documents)
          : 0;

      const categoryCounts: Record<string, number> = {};
      for (const doc of stats.documents) {
        categoryCounts[doc.category] =
          (categoryCounts[doc.category] || 0) + 1;
      }

      res.json({
        totalDocuments: stats.total_documents,
        totalChunks: stats.total_chunks,
        avgChunksPerDoc,
        categoryCounts,
      });
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : String(error);
      res.status(502).json({
        error: "Failed to connect to ingestion service",
        message: errMsg,
      });
    }
  }
);

// ── POST /documents/invalidate-cache ───────────────────────

documentsRouter.post(
  "/invalidate-cache",
  async (_req: Request, res: Response): Promise<void> => {
    try {
      const deleted = await invalidateOnIngestion();
      res.json({
        message: "Cache invalidated",
        entriesDeleted: deleted,
      });
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : String(error);
      res.status(500).json({
        error: "Cache invalidation failed",
        message: errMsg,
      });
    }
  }
);
