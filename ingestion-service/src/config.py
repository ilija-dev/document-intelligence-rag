"""
Centralized configuration for the ingestion pipeline.

All tunable parameters live here — chunk size, overlap, embedding model,
ChromaDB settings. This makes it easy to A/B test different chunking
strategies without touching business logic.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Chunking ──────────────────────────────────────────
    # 500 tokens with 50-token overlap is the sweet spot for document Q&A.
    # Too large (1000+): chunks contain mixed topics, retrieval gets noisy.
    # Too small (100): chunks lose context, LLM can't reason over fragments.
    # Overlap prevents information loss at chunk boundaries.
    chunk_size: int = 500
    chunk_overlap: int = 50

    # ── Embedding Model ───────────────────────────────────
    # all-MiniLM-L6-v2: 384-dim vectors, fast, good quality for document Q&A.
    # Runs locally via sentence-transformers — no API costs.
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_batch_size: int = 100

    # ── ChromaDB ──────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_collection: str = "documents"
    # Use persistent storage so data survives restarts.
    chroma_persist_dir: str = "./data/chroma"

    # ── Server ────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8100

    # ── File Handling ─────────────────────────────────────
    max_file_size_mb: int = 50
    supported_extensions: list[str] = [".pdf", ".txt", ".md"]

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
