from __future__ import annotations

import json
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


def _build_time_slots(start: str = "07:10", end: str = "16:30") -> List[str]:
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


def _compact_payload(context: Dict) -> Dict:
    return {
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
    compact = _compact_payload(context)

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
너는 방수 현장 작업계획 전문가다.

**입력 데이터:**
- worker_reg: 오늘 투입 인력
- priority_areas_rag: 우선 작업 구역
- all_areas_rag: 전체 작업 구역
- floor_area_map_rag: 층별 면적
- area_progress_rag: 어제까지의 작업 완료도 (%)
- area_waterproof_methods_rag: 구역별 방수 방법
- previous_progress_rag: 어제까지의 상세 진행도
- previous_daily_report_rag: 어제 일일 보고서 (주의사항, 이슈)
- inventory_rag: 현재 자재 재고
- weather_rag: 시간별 날씨 정보 (기온, 습도, 강수확률)
- waterproof_sequences_rag: 방수 작업 순서(RAG)
- time_slots: 07:10~16:30 30분 단위 시간 슬롯

**작업 규칙:**
1. 작업자는 worker_reg에만 있는 인력만 사용
2. 배정은 30분 단위 time_slots만 사용
3. 각 작업자는 독립적으로 배정
4. area_progress_rag를 참고하여 완료되지 않은 구역에 우선 배정
5. previous_daily_report_rag의 주의사항 반영
6. weather_rag의 강수확률 고 고려 (강수확률 >50% 시 옥외 작업 최소화)

{format_instructions}
""",
            ),
            (
                "human",
                "planning_inputs_json={planning_inputs_json}\ntime_slots={time_slots}",
            ),
        ]
    )

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
    chain = prompt | llm | parser

    try:
        parsed: PlanOutput = chain.invoke(
            {
                "planning_inputs_json": json.dumps(compact, ensure_ascii=False),
                "time_slots": _build_time_slots(),
                "format_instructions": parser.get_format_instructions(),
            }
        )
        return parsed.model_dump()
    except Exception:
        return _fallback_plan(context)
