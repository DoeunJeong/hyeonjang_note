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
                """너는 방수 현장 작업계획 전문가다.

[핵심 지시사항]
1. worker_reg에 있는 각 작업자에게 08:00~17:00까지 30분 단위로 작업 배정
2. 작업자별로 독립적인 일정 구성 (각 작업자는 전일 근무)
3. priority_areas_rag의 구역을 우선적으로 배정
4. 나머지 정보들(RAG, 날씨, 재고, 진행상황)을 모두 활용하여 최적의 계획 수립

[활용할 정보]
- 작업자 목록: {worker_reg}
- 우선순위 구역: {priority_areas_rag}
- 전체 구역: {all_areas_rag}
- 층별-구역 맵: {floor_area_map_rag}
- 구역별 진행률: {area_progress_rag}
- 구역별 방수 공법: {area_waterproof_methods_rag}
- 이전 진행 상황: {previous_progress_rag}
- 이전 일일 보고: {previous_daily_report_rag}
- 자재 재고: {inventory_rag}
- 날씨 정보: {weather_rag}
- 방수 시공 순서: {waterproof_sequences_rag}
- 가용 시간 슬롯: {time_slots}

[출력 JSON 스키마]
다음 형식으로 정확히 출력하되, JSON의 timeline 배열에 각 30분 구간을 PlanItem으로 포함:
{{
  "scheduler_status": "llm_generated",
  "model": "gemini-2.0-flash",
  "timeline": [
    {{
      "worker": "작업자명",
      "start": "HH:MM (08:00부터 16:30까지)",
      "end": "HH:MM (30분 후)",
      "area": "작업 구역명",
      "task": "구체적 작업 내용"
    }}
  ],
  "notes": ["계획 수립 시 고려사항 및 주의사항"]
}}

[계획 수립 원칙]
- 모든 작업자는 08:00 시작, 17:00 종료 (총 9시간, 18개 타임슬롯)
- 각 슬롯은 정확히 30분 단위
- 우선순위 구역부터 배정하되 골고루 배분
- 날씨가 악악하면 실내 작업 우선
- 재고 부족 시 노트에 별도 기재
- 이전 진행상황을 바탕으로 연속성 있게 배정
{format_instructions}""",
            ),
            (
                "human",
                "위의 모든 정보와 원칙을 고려하여 오늘의 방수 현장 작업계획을 수립하고 JSON 형식으로 출력해주세요.",
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
