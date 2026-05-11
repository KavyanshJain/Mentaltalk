"""
Retriever module for MentalTalk Mental Health Chatbot
Handles context retrieval from ChromaDB.
"""

from typing import List, Optional
import chromadb

from src.rag.embedder import embed_texts
from src.rag.ingestion import get_collection


def retrieve_context(query: str, n_results: int = 4) -> str:
    try:
        collection = get_collection()

        # Embed the query
        query_embedding = embed_texts([query])

        # Query ChromaDB
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )

        # Extract documents from results
        documents = results['documents'][0]

        if not documents:
            return ""

        # Join documents into a single context string
        context = "\n---\n".join(documents)
        return context

    except Exception as e:
        print(f"Error retrieving context: {e}")
        return ""


def get_collection_info() -> dict:
    try:
        collection = get_collection()
        result = collection.get()
        return {
            "num_documents": len(result['ids']),
            "collection_name": collection.name
        }
    except Exception as e:
        return {"error": str(e)}
