import os
import fitz  # PyMuPDF
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ── CONFIG ─────────────────────────────────────────────────────────────────────
PDF_FOLDER   = "./data"          # folder containing your 28 PDFs
CHROMA_DIR   = "./chroma_db"     # output folder — upload this to HF Spaces
COLLECTION   = "mental_health"   # name of the ChromaDB collection
# ───────────────────────────────────────────────────────────────────────────────


# ── STEP 1: Extract text from all PDFs ────────────────────────────────────────
def extract_texts(pdf_folder: str) -> list[dict]:
    documents = []
    for filename in sorted(os.listdir(pdf_folder)):
        if not filename.endswith(".pdf"):
            continue
        path = os.path.join(pdf_folder, filename)
        doc  = fitz.open(path)
        text = "".join(page.get_text() for page in doc)
        if len(text.strip()) < 100:
            print(f"  [WARN] Very little text in '{filename}' — possibly scanned, skipping.")
            continue
        documents.append({"source": filename, "text": text})
        print(f"  [OK] Extracted '{filename}' — {len(text):,} chars")
    return documents


# ── STEP 2: Chunk documents ───────────────────────────────────────────────────
def chunk_documents(documents: list[dict]) -> list[dict]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "]
    )
    all_chunks = []
    for doc in documents:
        chunks = splitter.split_text(doc["text"])
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "id":     f"{doc['source']}::chunk_{i}",
                "source": doc["source"],
                "chunk":  chunk.strip()
            })
        print(f"  [OK] '{doc['source']}' → {len(chunks)} chunks")
    return all_chunks


# ── STEP 3: Embed + store in ChromaDB ────────────────────────────────────────
def build_chroma(all_chunks: list[dict], chroma_dir: str, collection_name: str):
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    gemini_ef = SentenceTransformerEmbeddingFunction(
        model_name="google/embeddinggemma-300m"
    )

    client     = chromadb.PersistentClient(path=chroma_dir)
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=gemini_ef
    )

    # Add in batches of 50 to avoid API rate limits
    batch_size = 50
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        collection.add(
            ids        = [c["id"]     for c in batch],
            documents  = [c["chunk"]  for c in batch],
            metadatas  = [{"source": c["source"]} for c in batch]
        )
        print(f"  [OK] Stored chunks {i+1}–{min(i+batch_size, len(all_chunks))} / {len(all_chunks)}")

    print(f"\n  ChromaDB saved to '{chroma_dir}' with {collection.count()} total chunks.")


# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n=== STEP 1: Extracting PDFs ===")
    documents = extract_texts(PDF_FOLDER)
    print(f"  Total docs extracted: {len(documents)}\n")

    print("=== STEP 2: Chunking ===")
    all_chunks = chunk_documents(documents)
    print(f"  Total chunks: {len(all_chunks)}\n")

    print("=== STEP 3: Embedding + Storing in ChromaDB ===")
    build_chroma(all_chunks, CHROMA_DIR, COLLECTION)

    print("\n✅ Ingestion complete. Upload the './chroma_db' folder to HF Spaces.")