"""
ChromaDB vector store operations.

ChromaDB stores our document chunks as vectors with metadata. Key decisions:
- Persistent storage: data survives service restarts
- Upsert semantics: re-ingesting a document updates chunks, not duplicates
- Metadata-filtered search: enables hybrid search (vector + category/date)

Interview point: "We use ChromaDB with persistent storage and upsert semantics.
When a document is re-ingested (e.g., policy update), the deterministic chunk
IDs mean we update existing vectors instead of creating duplicates. This keeps
the index clean without manual deduplication."
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import chromadb

from .config import settings

logger = logging.getLogger(__name__)

# Singleton client
_client: chromadb.ClientAPI | None = None
_collection: chromadb.Collection | None = None


def get_client() -> chromadb.ClientAPI:
    """Get or create the ChromaDB persistent client."""
    global _client
    if _client is None:
        persist_dir = settings.chroma_persist_dir
        os.makedirs(persist_dir, exist_ok=True)
        logger.info(f"Initializing ChromaDB with persist_dir={persist_dir}")
        _client = chromadb.PersistentClient(path=persist_dir)
    return _client


def get_collection() -> chromadb.Collection:
    """Get or create the document collection."""
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            f"Collection '{settings.chroma_collection}' ready "
            f"({_collection.count()} existing chunks)"
        )
    return _collection


@dataclass
class SearchResult:
    """A single search result with score and metadata."""

    chunk_id: str
    text: str
    score: float  # Distance score (lower = more similar for cosine)
    doc_name: str
    page_number: int
    category: str
    chunk_index: int


@dataclass
class SearchResults:
    """Collection of search results."""

    query: str
    results: list[SearchResult] = field(default_factory=list)
    total_candidates: int = 0


def add_chunks(
    ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
) -> int:
    """
    Add or update chunks in the vector store.

    Uses upsert to handle re-ingestion: if a chunk ID already exists,
    it's updated rather than duplicated.
    """
    collection = get_collection()

    # ChromaDB has a batch size limit; process in chunks of 5000
    batch_size = 5000
    added = 0

    for i in range(0, len(ids), batch_size):
        batch_end = min(i + batch_size, len(ids))
        collection.upsert(
            ids=ids[i:batch_end],
            documents=texts[i:batch_end],
            embeddings=embeddings[i:batch_end],
            metadatas=metadatas[i:batch_end],
        )
        added += batch_end - i

    logger.info(f"Upserted {added} chunks to collection")
    return added


def search(
    query_embedding: list[float],
    n_results: int = 20,
    where: dict | None = None,
    where_document: dict | None = None,
) -> SearchResults:
    """
    Search the vector store with optional metadata filtering.

    The query flow:
    1. ChromaDB finds top-N nearest neighbors by cosine similarity
    2. Optional 'where' filter narrows by metadata (category, date, etc.)
    3. Results include the text, distance score, and full metadata

    We retrieve top-20 candidates here; the hybrid search layer in the
    TypeScript API re-ranks and returns top-5 to the LLM.
    """
    collection = get_collection()

    query_params: dict = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
    }

    if where:
        query_params["where"] = where
    if where_document:
        query_params["where_document"] = where_document

    raw = collection.query(**query_params)

    results: list[SearchResult] = []
    if raw["ids"] and raw["ids"][0]:
        for i, chunk_id in enumerate(raw["ids"][0]):
            metadata = raw["metadatas"][0][i] if raw["metadatas"] else {}
            distance = raw["distances"][0][i] if raw["distances"] else 1.0
            text = raw["documents"][0][i] if raw["documents"] else ""

            results.append(
                SearchResult(
                    chunk_id=chunk_id,
                    text=text,
                    score=1.0 - distance,  # Convert distance to similarity
                    doc_name=metadata.get("doc_name", ""),
                    page_number=metadata.get("page_number", 0),
                    category=metadata.get("category", ""),
                    chunk_index=metadata.get("chunk_index", 0),
                )
            )

    return SearchResults(
        query="",
        results=results,
        total_candidates=collection.count(),
    )


def delete_document(doc_name: str) -> int:
    """
    Delete all chunks belonging to a document.

    Used when a document is re-ingested or removed from the collection.
    """
    collection = get_collection()

    # Get all chunk IDs for this document
    existing = collection.get(where={"doc_name": doc_name})
    if existing["ids"]:
        collection.delete(ids=existing["ids"])
        logger.info(f"Deleted {len(existing['ids'])} chunks for {doc_name}")
        return len(existing["ids"])
    return 0


@dataclass
class CollectionStats:
    """Statistics about the current collection."""

    total_chunks: int
    total_documents: int
    documents: list[dict] = field(default_factory=list)


def get_stats() -> CollectionStats:
    """Get collection statistics for the /stats endpoint."""
    collection = get_collection()
    total_chunks = collection.count()

    # Get unique document names
    if total_chunks == 0:
        return CollectionStats(
            total_chunks=0, total_documents=0, documents=[]
        )

    # Sample metadata to get document list
    # ChromaDB doesn't have a native "distinct" — we query all metadata
    all_data = collection.get(include=["metadatas"])
    doc_map: dict[str, dict] = {}

    for meta in all_data["metadatas"] or []:
        doc_name = meta.get("doc_name", "unknown")
        if doc_name not in doc_map:
            doc_map[doc_name] = {
                "doc_name": doc_name,
                "category": meta.get("category", ""),
                "chunk_count": 0,
                "ingestion_date": meta.get("ingestion_date", ""),
            }
        doc_map[doc_name]["chunk_count"] += 1

    documents = sorted(doc_map.values(), key=lambda d: d["doc_name"])

    return CollectionStats(
        total_chunks=total_chunks,
        total_documents=len(documents),
        documents=documents,
    )
