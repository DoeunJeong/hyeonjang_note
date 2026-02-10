from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import chromadb

VECTOR_STORE_DIR = Path("data/vector_store")
WATERPROOF_COLLECTION = "waterproof_sequences"
DEFAULT_DOC_PATH = Path("docs/waterproof_sequence.md")


def _load_doc_text(doc_path: Path) -> str:
    if not doc_path.exists():
        raise FileNotFoundError(f"문서를 찾을 수 없습니다: {doc_path}")
    return doc_path.read_text(encoding="utf-8")


def _chunk_text(text: str, chunk_size: int = 600) -> List[str]:
    clean = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not clean:
        return []
    return [clean[i : i + chunk_size] for i in range(0, len(clean), chunk_size)]


def index_waterproof_sequence_doc(doc_path: str = str(DEFAULT_DOC_PATH)) -> Dict:
    if not os.getenv("GEMINI_API_KEY"):
        return {"indexed": False, "reason": "missing_GEMINI_API_KEY"}

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    path = Path(doc_path)
    text = _load_doc_text(path)
    chunks = _chunk_text(text)
    if not chunks:
        return {"indexed": False, "reason": "empty_document"}

    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = client.get_or_create_collection(name=WATERPROOF_COLLECTION)

    emb = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    vectors = emb.embed_documents(chunks)

    ids = [f"{path.stem}-{i}" for i in range(len(chunks))]
    metadatas = [{"source": str(path), "chunk_index": i} for i in range(len(chunks))]

    try:
        collection.delete(ids=ids)
    except Exception:
        pass

    collection.add(ids=ids, documents=chunks, embeddings=vectors, metadatas=metadatas)
    return {"indexed": True, "collection": WATERPROOF_COLLECTION, "chunks": len(chunks), "source": str(path)}


def search_waterproof_sequence(query: str, top_k: int = 3) -> Dict:
    if not os.getenv("GEMINI_API_KEY"):
        return {"items": [], "reason": "missing_GEMINI_API_KEY"}

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = client.get_or_create_collection(name=WATERPROOF_COLLECTION)

    emb = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    query_vector = emb.embed_query(query)
    res = collection.query(query_embeddings=[query_vector], n_results=top_k)

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]

    items = []
    for i, doc in enumerate(docs):
        items.append(
            {
                "content": doc,
                "metadata": metas[i] if i < len(metas) else {},
                "distance": dists[i] if i < len(dists) else None,
            }
        )
    return {"items": items, "collection": WATERPROOF_COLLECTION}
