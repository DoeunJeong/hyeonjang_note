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


async def run_planning_agent(context: Dict) -> Dict:
    print(" -> [4-1] 'run_planning_agent' 함수 진입")
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(" -> [!!!] API 키를 찾을 수 없어 기본(Fallback) 계획을 반환합니다.")
        return _fallback_plan(context)

    if not os.getenv("GOOGLE_API_KEY") and api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
    
    print(" -> [4-2] LangChain 및 Google AI 라이브러리 import 시도")
    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_google_genai import ChatGoogleGenerativeAI
        print(" -> [4-3] 라이브러리 import 성공")
    except Exception as e:
        print(f" -> [!!!] 라이브러리 import 실패: {e}")
        raise e

    # 변수를 먼저 정의합니다.
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
- all_areas_rag: 전체 작업 구역 (동/층 정보 포함)
- floor_area_map_rag: 층별 면적
- area_progress_rag: 어제까지의 작업 완료도 (%)
- area_waterproof_methods_rag: 구역별 방수 방법
- previous_progress_rag: 어제까지의 상세 진행도
- previous_daily_report_rag: 어제 일일 보고서 (주의사항, 이슈)
- inventory_rag: 현재 자재 재고
- weather_rag: 시간별 날씨 정보 (기온, 습도, 강수확률)
- waterproof_sequences_rag: 방수 작업 순서(RAG)
- floor_range_rag: 오늘 작업할 층수 범위 (start~end층). 아랫층부터 윗층 순서대로 작업 배정해라.
- time_slots: 08:00~17:00 30분 단위 시간 슬롯

**작업 배정 규칙:**
1. **구체적 위치 명시**: "세대" 대신 **"101동 3층"**, "101동 4층"과 같이 구체적인 위치를 배정해라. (1048세대, 101~110동 정보를 참고)
2. **동일 작업 그룹핑**: 여러 작업자가 같은 구역에서 같은 작업을 해도 된다. (예: 정고은, 정노은 -> 101동 3층 바탕면 정리)
3. **간결한 작업명**: 작업명에 코드(M01, A01 등)가 있다면 괄호 설명은 제거하고 핵심만 적어라. (예: "M01 노출 우레탄" (O), "M01(노출 우레탄...)" (X))
4. **시간 연속성**: 작업은 가능한 끊기지 않고 연속되게 배정해라.
5. **날씨 고려**: 강수확률이 높으면 실내 작업 위주로 배정해라.
6. **overview 및 guidelines**: 오늘의 전체적인 작업 전략과 안전/품질 주의사항을 구체적으로 작성해라.
7. **층수 순서 준수**: floor_range_rag에 start/end가 있으면 해당 층 범위 내에서만 작업을 배정하고, **아랫층(start)부터 윗층(end) 순서**로 작업해라. 예: 2층→3층→4층

{format_instructions}
""",
            ),
            (
                "human",
                "planning_inputs_json={planning_inputs_json}\ntime_slots={time_slots}",
            ),
        ]
    )
    
    print(" -> [4-4] LLM(AI 모델) 초기화 시도 (model='gemini-2.0-flash')")
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
        chain = prompt | llm | parser
        print(" -> [4-5] LLM 초기화 및 체인 구성 성공")
    except Exception as e:
        print(f" -> [!!!] LLM 초기화 실패: {e}")
        raise e

    try:
        print(" -> [4-6] AI 모델에 작업 계획 생성 요청 시작...")
        parsed: PlanOutput = await chain.ainvoke(
            {
                "planning_inputs_json": json.dumps(compact, ensure_ascii=False),
                "time_slots": _build_time_slots(),
                "format_instructions": parser.get_format_instructions(),
            }
        )
        print(" -> [4-7] AI 모델로부터 응답 수신 성공!")
        return parsed.model_dump()
    except Exception as e:
        print(f" -> [!!!] AI 모델 호출 실패: {e}")
        return _fallback_plan(context)
