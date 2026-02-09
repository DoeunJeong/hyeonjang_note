from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Dict, List

from pydantic import BaseModel, Field


class PlanItem(BaseModel):
    worker: str
    start: str
    end: str
    area: str
    task: str


class PlanOutput(BaseModel):
    scheduler_status: str = "llm_generated"
    model: str = "gemini-2.0-flash"
    timeline: List[PlanItem] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


def _build_time_slots(start: str = "08:00", end: str = "17:00") -> List[str]:
    slots: List[str] = []
    current = datetime.strptime(start, "%H:%M")
    end_time = datetime.strptime(end, "%H:%M")
    while current < end_time:
        slots.append(current.strftime("%H:%M"))
        current += timedelta(minutes=30)
    return slots


def _fallback_plan(context: Dict) -> Dict:
    workers = context.get("worker_reg", [])
    areas = context.get("priority_areas_rag") or context.get("all_areas_rag") or ["세대"]
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
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_google_genai import ChatGoogleGenerativeAI
    except Exception:
        return _fallback_plan(context)

    parser = PydanticOutputParser(pydantic_object=PlanOutput)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
너는 방수 현장 작업계획 전문가다.
작업자는 worker_reg 목록만 사용하고, 시간은 30분 단위(08:00~17:00)로 계획한다.
작업계획은 작업자별 독립 배정으로 작성한다.
아래 정보들을 모두 활용해 계획을 작성한다:
- worker_reg
- priority_areas_rag
- all_areas_rag
- floor_area_map_rag
- area_progress_rag
- area_waterproof_methods_rag
- previous_progress_rag
- previous_daily_report_rag
- inventory_rag
- weather_rag
- waterproof_sequences_rag
반드시 아래 포맷 지시를 지켜서 출력한다.
{format_instructions}
""",
            ),
            (
                "human",
                """
worker_reg={worker_reg}
priority_areas_rag={priority_areas_rag}
all_areas_rag={all_areas_rag}
floor_area_map_rag={floor_area_map_rag}
area_progress_rag={area_progress_rag}
area_waterproof_methods_rag={area_waterproof_methods_rag}
previous_progress_rag={previous_progress_rag}
previous_daily_report_rag={previous_daily_report_rag}
inventory_rag={inventory_rag}
weather_rag={weather_rag}
waterproof_sequences_rag={waterproof_sequences_rag}
time_slots={time_slots}
""",
            ),
        ]
    )

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
    chain = prompt | llm | parser

    try:
        parsed: PlanOutput = chain.invoke(
            {
                "worker_reg": context.get("worker_reg", []),
                "priority_areas_rag": context.get("priority_areas_rag", []),
                "all_areas_rag": context.get("all_areas_rag", []),
                "floor_area_map_rag": context.get("floor_area_map_rag", {}),
                "area_progress_rag": context.get("area_progress_rag", {}),
                "area_waterproof_methods_rag": context.get("area_waterproof_methods_rag", {}),
                "previous_progress_rag": context.get("previous_progress_rag"),
                "previous_daily_report_rag": context.get("previous_daily_report_rag"),
                "inventory_rag": context.get("inventory_rag", {}),
                "weather_rag": context.get("weather_rag", {}),
                "waterproof_sequences_rag": context.get("waterproof_sequences_rag", {}),
                "time_slots": _build_time_slots(),
                "format_instructions": parser.get_format_instructions(),
            }
        )
        return parsed.model_dump()
    except Exception:
        return _fallback_plan(context)
