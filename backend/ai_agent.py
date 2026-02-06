"""LangChain agent placeholder for future integration."""

from typing import Dict


def run_planning_agent(context: Dict) -> Dict:
    """Return integration contract for future wiring."""
    return {
        "status": "stub",
        "message": "Use Chroma + Google text-embedding-004 after RAG docs are finalized.",
        "context": context,
    }
