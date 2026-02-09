"""Deprecated: vector store operations moved to backend.rag_store."""

from typing import Dict


def get_rag_stack_recommendation() -> Dict:
    return {
        "deprecated": True,
        "message": "Use backend.rag_store for indexing/search operations.",
    }
