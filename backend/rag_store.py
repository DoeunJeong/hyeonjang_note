from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

import chromadb

VECTOR_STORE_DIR = Path("data/vector_store")
WATERPROOF_COLLECTION = "waterproof_sequences"

# 절대 경로로 명확하게 지정
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DOC_PATH = BASE_DIR / "data" / "rag_docs" / "waterproof_sequences.md"


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
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"indexed": False, "reason": "missing_GEMINI_API_KEY"}

    if api_key and not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = api_key

    try:
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        path = Path(doc_path)
        if not path.is_absolute():
            # 상대 경로인 경우 프로젝트 루트 기준으로 변경 (data 폴더는 backend 상위의 data)
            base_dir = Path(__file__).resolve().parent.parent
            path = base_dir / doc_path

        text = _load_doc_text(path)
        chunks = _chunk_text(text)
        if not chunks:
            return {"indexed": False, "reason": "empty_document"}

        VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
        collection = client.get_or_create_collection(name=WATERPROOF_COLLECTION)

        emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        vectors = emb.embed_documents(chunks)

        ids = [f"{path.stem}-{i}" for i in range(len(chunks))]
        metadatas = [{"source": str(path), "chunk_index": i} for i in range(len(chunks))]

        try:
            collection.delete(ids=ids)
        except Exception:
            pass

        collection.add(ids=ids, documents=chunks, embeddings=vectors, metadatas=metadatas)
        return {"indexed": True, "collection": WATERPROOF_COLLECTION, "chunks": len(chunks), "source": str(path)}
    except Exception as e:
        import traceback

        traceback.print_exc()
        return {"indexed": False, "reason": str(e), "trace": traceback.format_exc()}


def search_waterproof_sequence(query: str, top_k: int = 3) -> Dict:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return {"items": [], "reason": "missing_GEMINI_API_KEY"}

    if api_key and not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = api_key

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    client = chromadb.PersistentClient(path=str(VECTOR_STORE_DIR))
    collection = client.get_or_create_collection(name=WATERPROOF_COLLECTION)

    emb = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
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
