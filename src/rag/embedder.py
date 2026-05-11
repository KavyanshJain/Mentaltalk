"""
Embedder module for MentalTalk Mental Health Chatbot
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
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDING_MODEL)
    return _embedder


def embed_texts(texts: List[str]) -> List[List[float]]:
    embedder = get_embedder()
    # Get embeddings as numpy array
    embeddings = embedder.encode(texts, convert_to_numpy=True)
    # Convert to list of lists (ChromaDB requires plain Python lists)
    return [embedding.tolist() for embedding in embeddings]


def embed_text(text: str) -> List[float]:
    return embed_texts([text])[0]
