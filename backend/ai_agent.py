"""LangChain agent placeholder for future integration."""

from typing import Dict


def run_planning_agent(context: Dict) -> Dict:
    """Return context as-is until LLM/RAG chain is wired."""
    return {
        "status": "stub",
        "message": "LangChain agent will be connected after model/provider decision.",
        "context": context,
    }
