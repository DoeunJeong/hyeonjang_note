from datetime import datetime
from typing import Dict, List, Optional


SCHEDULER_STATUS = "skeleton"


def build_daily_plan(
    rag: Dict,
    workers: List[str],
    priority_areas: List[str],
    weather_summary: Optional[str] = None,
):
    """일정 알고리즘 확정 전 스켈레톤 응답.

    추후 RAG 문서 완성 후 우선순위/건조시간/날씨 제약 기반 최적화 로직으로 교체.
    """
    area_cycle = priority_areas or ["세대", "상가", "지하"]
    timeline = []

    for worker in workers:
        for area in area_cycle:
            timeline.append(
                {
                    "worker": worker,
                    "start": "08:00",
                    "end": "08:30",
                    "area": area,
                    "task": "[스켈레톤] 작업 순서 알고리즘 확정 후 자동 생성",
                    "weather_note": weather_summary or "날씨 연동 전",
                }
            )
            break

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "scheduler_status": SCHEDULER_STATUS,
        "timeline": timeline,
        "notes": [
            "RAG 문서 완성 후 실제 배정 알고리즘을 연결합니다.",
            "현재는 UI/입력 흐름 확인용 임시 결과입니다.",
        ],
    }
