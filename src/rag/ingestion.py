"""
Ingestion module for MindEase Mental Health Chatbot
Handles PDF loading, chunking, embedding, and ChromaDB upsert.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional, List
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

from src.rag.embedder import embed_texts

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

CHROMA_PERSIST_PATH = os.getenv("CHROMA_PERSIST_PATH", "./chroma_db")

# ChromaDB collection
_collection = None


def _get_client() -> chromadb.PersistentClient:
    """
    Get or create the ChromaDB PersistentClient.

    Returns:
        ChromaDB PersistentClient instance
    """
    # Ensure the directory exists
    Path(CHROMA_PERSIST_PATH).parent.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=CHROMA_PERSIST_PATH)


def get_collection():
    """
    Get or create the ChromaDB collection for mental health documents.

    Returns:
        ChromaDB Collection instance
    """
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(name="mental_health_docs")
    return _collection


def _generate_chunk_id(text: str) -> str:
    """
    Generate a unique ID for a text chunk.

    Args:
        text: The text chunk

    Returns:
        Unique ID string
    """
    text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    return f"chunk_{text_hash}"


def _load_pdf_text(pdf_path: str) -> str:
    """
    Load text from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text from the PDF
    """
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error loading PDF {pdf_path}: {e}")
    return text


def _chunk_text(text: str, chunk_size: int = 800, chunk_overlap: int = 100) -> List[str]:
    """
    Split text into chunks using RecursiveCharacterTextSplitter.

    Args:
        text: Text to split
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters

    Returns:
        List of text chunks
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_text(text)
    return chunks


def ingest_pdfs(pdf_dir: str) -> int:
    """
    Ingest all PDFs from a directory into ChromaDB.

    Args:
        pdf_dir: Directory containing PDF files

    Returns:
        Number of chunks ingested
    """
    pdf_path = Path(pdf_dir)
    if not pdf_path.exists():
        print(f"PDF directory {pdf_dir} does not exist.")
        return 0

    # Get or create the collection
    collection = get_collection()

    # Get existing IDs to avoid duplicates
    existing_results = collection.get()
    existing_ids = set(existing_results['ids'])

    # Process each PDF
    total_chunks = 0
    pdf_files = list(pdf_path.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {pdf_dir}.")
        return 0

    print(f"Found {len(pdf_files)} PDF files to process.")

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        # Load text from PDF
        text = _load_pdf_text(str(pdf_file))
        if not text.strip():
            print(f"  Skipping {pdf_file.name} - no text extracted.")
            continue

        # Split into chunks
        chunks = _chunk_text(text)
        print(f"  Split into {len(chunks)} chunks.")

        # Embed chunks and upsert to ChromaDB
        for chunk in chunks:
            chunk_id = _generate_chunk_id(chunk)
            if chunk_id in existing_ids:
                continue

            # Embed the chunk
            embedding = embed_texts([chunk])[0]

            # Upsert to ChromaDB
            collection.upsert(
                ids=[chunk_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"source": pdf_file.name}]
            )
            existing_ids.add(chunk_id)
            total_chunks += 1

    print(f"Ingested {total_chunks} chunks from {len(pdf_files)} PDF files.")
    return total_chunks


def is_collection_empty() -> bool:
    """
    Check if the ChromaDB collection is empty.

    Returns:
        True if the collection has no documents, False otherwise
    """
    try:
        collection = get_collection()
        result = collection.get()
        return len(result['ids']) == 0
    except Exception:
        return True
