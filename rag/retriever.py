import os
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# ── CONFIG ────────────────────────────────────────────────────────────────────
# Resolve paths relative to the project root (parent of `rag/`)
_PROJECT_ROOT   = Path(__file__).resolve().parent.parent
CHROMA_DIR      = str(_PROJECT_ROOT / "chroma_db")
COLLECTION_NAME = "mental_health"
EMBED_MODEL     = "google/embeddinggemma-300m"
TOP_K           = 5
# ──────────────────────────────────────────────────────────────────────────────


def load_collection():
    """
    Load the ChromaDB collection with its embedding function.

    Returns the collection object, or raises an exception if the
    ChromaDB directory doesn't exist or is empty.
    """
    chroma_path = Path(CHROMA_DIR)
    if not chroma_path.exists():
        raise FileNotFoundError(
            f"ChromaDB directory not found at '{CHROMA_DIR}'. "
            f"Run ingest.py first to build the vector store."
        )

<<<<<<< HEAD
=======
    # google/embeddinggemma-300m is a gated model — pass HF_TOKEN if available
>>>>>>> 960015e (minor changes)
    hf_token = os.environ.get("HF_TOKEN")
    embed_fn = SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL,
        token=hf_token,
    )
    client     = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_collection(
        name=COLLECTION_NAME,
        embedding_function=embed_fn,
    )
    count = collection.count()
    if count == 0:
        raise ValueError(
            f"ChromaDB collection '{COLLECTION_NAME}' exists but is empty. "
            f"Run ingest.py to populate it."
        )
    print(f"✅ ChromaDB loaded — {count} chunks in '{COLLECTION_NAME}'")
    return collection


def retrieve(query: str, collection, n_results: int = TOP_K) -> list[dict]:
    """
    Retrieve the top-N most relevant chunks for a query.

    Returns a list of dicts:
        [
            {"chunk": "...", "source": "filename.pdf", "distance": 0.23},
            ...
        ]
    """
    results = collection.query(query_texts=[query], n_results=n_results)

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "chunk":    doc,
            "source":   meta.get("source", "Unknown"),
            "distance": dist,
        })
    return hits


def build_context(hits: list[dict]) -> str:
    """Format retrieved chunks into a single context string for the LLM prompt."""
    parts = []
    for i, h in enumerate(hits, 1):
        parts.append(f"[{i}] (Source: {h['source']})\n{h['chunk']}")
    return "\n\n".join(parts)


# ── QUICK TEST ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    collection = load_collection()

    query = "How to manage depression?"
    print(f"\n🔍 Query: {query}\n")

    hits = retrieve(query, collection)
    for h in hits:
        print(f"  📄 {h['source']}  (dist: {h['distance']:.4f})")
        print(f"     {h['chunk'][:120]}…\n")

    print("── Full context ──")
    print(build_context(hits))
