# RAG module
# Re-export all public functions from submodules

from .embedder import (
    get_embedder,
    embed_texts,
    embed_text,
)

from .ingestion import (
    ingest_pdfs,
    get_collection,
    is_collection_empty,
)

from .retriever import (
    retrieve_context,
    get_collection_info,
)

__all__ = [
    "get_embedder",
    "embed_texts",
    "embed_text",
    "ingest_pdfs",
    "get_collection",
    "is_collection_empty",
    "retrieve_context",
    "get_collection_info",
]
