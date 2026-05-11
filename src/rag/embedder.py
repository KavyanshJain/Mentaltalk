"""
Embedder module for MindEase Mental Health Chatbot
Handles text embeddings using Sentence Transformers.
"""

import os
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Model to use for embeddings
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Cached embedder instance
_embedder = None


def get_embedder() -> SentenceTransformer:
    """
    Get the SentenceTransformer embedder instance.
    Caches the model after first load.

    When called from Streamlit, use @st.cache_resource for better performance.
    For non-Streamlit usage, uses module-level caching.

    Returns:
        SentenceTransformer model instance
    """
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts.

    Args:
        texts: List of text strings to embed

    Returns:
        List of embedding vectors (each as a list of floats)
    """
    embedder = get_embedder()
    # Get embeddings as numpy array
    embeddings = embedder.encode(texts, convert_to_numpy=True)
    # Convert to list of lists (ChromaDB requires plain Python lists)
    return [embedding.tolist() for embedding in embeddings]


def embed_text(text: str) -> List[float]:
    """
    Embed a single text.

    Args:
        text: Text string to embed

    Returns:
        Embedding vector as a list of floats
    """
    return embed_texts([text])[0]
