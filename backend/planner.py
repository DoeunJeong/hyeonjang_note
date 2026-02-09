"""Deprecated: planning is handled by backend.ai_agent.run_planning_agent."""

from typing import Dict


def build_daily_plan(*args, **kwargs) -> Dict:
    return {
        "deprecated": True,
        "message": "Use backend.ai_agent.run_planning_agent instead.",
    }
