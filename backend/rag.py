from typing import Dict


RAG_RECOMMENDATION = {
    "vector_db": "chroma",
    "embedding_provider": "google_genai",
    "embedding_model": "models/text-embedding-004",
    "notes": "로컬/서버 모두 운영이 쉬워 다중 현장 분리 컬렉션에 적합",
}


def get_rag_stack_recommendation() -> Dict:
    return RAG_RECOMMENDATION
