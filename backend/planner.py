from datetime import datetime, timedelta
from typing import Dict, List, Optional


def build_daily_plan(
    rag: Dict,
    workers: List[str],
    priority_areas: List[str],
    weather_summary: Optional[str] = None,
):
    start = datetime.strptime("08:00", "%H:%M")
    end = datetime.strptime("17:00", "%H:%M")
    slot = timedelta(minutes=30)

    sequences = rag.get("waterproof_sequences", {})
    default_sequence = ["바탕 정리", "프라이머", "방수층 시공", "건조 확인"]

    timeline = []
    current = start
    area_cycle = priority_areas or ["세대", "상가", "지하"]

    idx = 0
    while current < end:
        next_time = current + slot
        for worker in workers:
            area = area_cycle[idx % len(area_cycle)]
            seq = sequences.get("우레탄방수(노출/비노출)", default_sequence)
            task = seq[idx % len(seq)]
            timeline.append(
                {
                    "worker": worker,
                    "start": current.strftime("%H:%M"),
                    "end": next_time.strftime("%H:%M"),
                    "area": area,
                    "task": task,
                    "weather_note": weather_summary or "weather api 연동 전",
                }
            )
            idx += 1
        current = next_time

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timeline": timeline,
        "notes": [
            "환기 상태와 날씨에 따라 건조 시간 재조정 필요",
            "비 예보 시 옥외 노출 작업 재배치",
        ],
    }
