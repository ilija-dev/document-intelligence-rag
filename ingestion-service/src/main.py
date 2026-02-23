"""
FastAPI ingestion service — the Python side of the RAG system.

Endpoints:
  POST /ingest  — accept a file, extract text, chunk, embed, store in ChromaDB
  POST /search  — vector search with optional metadata filters
  GET  /stats   — collection size, document count, per-doc chunk counts
  GET  /health  — liveness check

The TypeScript API server calls /search for retrieval; /ingest is called
during document onboarding (batch or via API).
"""

import logging
import os
import tempfile
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .chunker import chunk_document
from .config import settings
from .embedder import embed_single, embed_texts, get_model
from .extract import extract_document
from .metadata import build_metadata
from .store import add_chunks, get_collection, get_stats, search

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load embedding model and initialize ChromaDB on startup."""
    logger.info("Starting ingestion service...")
    # Warm up the embedding model (loads it into memory)
    get_model()
    # Initialize ChromaDB collection
    get_collection()
    logger.info("Ingestion service ready")
    yield
    logger.info("Shutting down ingestion service")


app = FastAPI(
    title="Document Intelligence — Ingestion Service",
    description="Extract, chunk, embed, and store documents for RAG retrieval",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Request/Response Models ───────────────────────────────


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    n_results: int = Field(default=20, ge=1, le=100)
    category: str | None = Field(default=None, description="Filter by category")
    doc_name: str | None = Field(default=None, description="Filter by document name")


class SearchResultItem(BaseModel):
    chunk_id: str
    text: str
    score: float
    doc_name: str
    page_number: int
    category: str
    chunk_index: int


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total_candidates: int
    search_time_ms: float


class IngestResponse(BaseModel):
    doc_name: str
    pages_extracted: int
    chunks_created: int
    category: str
    ingestion_time_seconds: float


class StatsResponse(BaseModel):
    total_chunks: int
    total_documents: int
    documents: list[dict]


# ── Endpoints ─────────────────────────────────────────────


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "ingestion"}


@app.post("/ingest", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    category: str | None = Form(default=None),
):
    """
    Ingest a document: extract text → chunk → embed → store in ChromaDB.

    This is the full ingestion pipeline in one endpoint. For batch ingestion,
    call this endpoint per file (or use the CLI batch script).
    """
    start = time.time()

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in settings.supported_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix}. Supported: {settings.supported_extensions}",
        )

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()

        # Check file size
        if len(content) > settings.max_file_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max: {settings.max_file_size_mb}MB",
            )

        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Step 1: Extract text
        extraction = extract_document(tmp_path)
        # Override file_path with original name for display
        extraction.file_name = file.filename
        extraction.file_path = file.filename

        if not extraction.pages:
            raise HTTPException(
                status_code=400,
                detail=f"No text could be extracted from {file.filename}",
            )

        # Step 2: Chunk
        chunking = chunk_document(extraction)

        if not chunking.chunks:
            raise HTTPException(
                status_code=400,
                detail=f"No chunks produced from {file.filename}",
            )

        # Step 3: Build metadata
        sample_text = extraction.pages[0].text if extraction.pages else ""
        metadata = build_metadata(
            file_name=file.filename,
            file_path=file.filename,
            page_count=extraction.total_pages,
            chunk_count=chunking.total_chunks,
            sample_text=sample_text,
            file_size_bytes=len(content),
        )
        # Override category if explicitly provided
        if category:
            metadata.category = category

        # Step 4: Embed all chunks
        texts = [c.text for c in chunking.chunks]
        embedding_result = embed_texts(texts)

        # Step 5: Store in ChromaDB
        ids = [c.chunk_id for c in chunking.chunks]
        metadatas = [
            metadata.to_chroma_metadata(c.page_number, c.chunk_index)
            for c in chunking.chunks
        ]
        add_chunks(ids, texts, embedding_result.embeddings, metadatas)

        elapsed = time.time() - start
        logger.info(
            f"Ingested {file.filename}: {chunking.total_chunks} chunks "
            f"in {elapsed:.2f}s"
        )

        return IngestResponse(
            doc_name=file.filename,
            pages_extracted=extraction.non_empty_pages,
            chunks_created=chunking.total_chunks,
            category=metadata.category,
            ingestion_time_seconds=round(elapsed, 2),
        )

    finally:
        # Clean up temp file
        os.unlink(tmp_path)


@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search the vector store with optional metadata filtering.

    This endpoint is called by the TypeScript API server's hybrid search
    layer. It returns top-N candidates ranked by cosine similarity,
    optionally filtered by category or document name.
    """
    start = time.time()

    # Embed the query
    query_embedding = embed_single(request.query)

    # Build metadata filter
    where: dict | None = None
    conditions = []

    if request.category:
        conditions.append({"category": request.category})
    if request.doc_name:
        conditions.append({"doc_name": request.doc_name})

    if len(conditions) == 1:
        where = conditions[0]
    elif len(conditions) > 1:
        where = {"$and": conditions}

    # Search
    results = search(
        query_embedding=query_embedding,
        n_results=request.n_results,
        where=where,
    )

    elapsed = (time.time() - start) * 1000  # Convert to ms

    return SearchResponse(
        query=request.query,
        results=[
            SearchResultItem(
                chunk_id=r.chunk_id,
                text=r.text,
                score=round(r.score, 4),
                doc_name=r.doc_name,
                page_number=r.page_number,
                category=r.category,
                chunk_index=r.chunk_index,
            )
            for r in results.results
        ],
        total_candidates=results.total_candidates,
        search_time_ms=round(elapsed, 2),
    )


@app.get("/stats", response_model=StatsResponse)
async def collection_stats():
    """
    Get collection statistics.

    Returns total chunks, unique document count, and per-document
    chunk counts. Useful for monitoring ingestion progress and
    identifying documents that produce unusually many/few chunks.
    """
    stats = get_stats()
    return StatsResponse(
        total_chunks=stats.total_chunks,
        total_documents=stats.total_documents,
        documents=stats.documents,
    )
