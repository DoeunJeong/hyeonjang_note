from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, List


def _build_time_slots(start: str = "08:00", end: str = "17:00") -> List[str]:
    slots: List[str] = []
    current = datetime.strptime(start, "%H:%M")
    end_time = datetime.strptime(end, "%H:%M")
    while current < end_time:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=30)
    return slots


def _fallback_plan(context: Dict) -> Dict:
    workers = context.get("workers", [])
    areas = context.get("priority_areas") or context.get("all_areas") or ["세대"]
    times = _build_time_slots()
    timeline = []

    for worker_idx, worker in enumerate(workers):
        for i, start in enumerate(times[:6]):
            next_time = (datetime.strptime(start, "%H:%M") + timedelta(minutes=30)).strftime("%H:%M")
            area = areas[(worker_idx + i) % len(areas)]
            timeline.append(
                {
                    "worker": worker,
                    "start": start,
                    "end": next_time,
                    "area": area,
                    "task": "RAG/날씨 반영 작업(기본안)",
                }
            )

    return {
        "scheduler_status": "llm_fallback",
        "model": "fallback",
        "timeline": timeline,
        "notes": ["GEMINI_API_KEY 미설정 또는 LLM 호출 실패로 기본안을 반환했습니다."],
    }


def run_planning_agent(context: Dict) -> Dict:
    if not os.getenv("GEMINI_API_KEY"):
        return _fallback_plan(context)

    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception:
        return _fallback_plan(context)

    workers = context.get("workers", [])
    times = _build_time_slots()

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
너는 방수 현장 작업계획 전문가다.
반드시 JSON만 출력한다.
출력 스키마:
{
  "scheduler_status": "llm_generated",
  "model": "gemini-2.0-flash",
  "timeline": [
    {"worker":"", "start":"HH:MM", "end":"HH:MM", "area":"", "task":""}
  ],
  "notes": [""]
}
규칙:
- 작업자는 입력된 workers만 사용.
- 시간은 30분 단위(08:00~17:00).
- 작업계획은 작업자별로 독립 배정.
- weather_rag, previous_progress_rag, previous_daily_report_rag, inventory_rag를 반영.
""",
            ),
            (
                "human",
                "context_json={context_json}\nallowed_workers={workers}\ntime_slots={time_slots}",
            ),
        ]
    )

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
    chain = prompt | llm
    response = chain.invoke(
        {
            "context_json": str(context),
            "workers": workers,
            "time_slots": times,
        }
    )

    text = response.content if isinstance(response.content, str) else str(response.content)
    try:
        import json

        parsed = json.loads(text)
        if not isinstance(parsed, dict) or "timeline" not in parsed:
            raise ValueError("invalid llm output")
        return parsed
    except Exception:
        return _fallback_plan(context)
