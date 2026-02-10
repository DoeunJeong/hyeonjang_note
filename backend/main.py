import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv

# .env 파일 명시적 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# 디버깅: API 키 로드 확인
print(f"DEBUG: GEMINI_API_KEY loaded? {bool(os.getenv('GEMINI_API_KEY'))}")
print(f"DEBUG: GOOGLE_API_KEY loaded? {bool(os.getenv('GOOGLE_API_KEY'))}")

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.ai_agent import run_planning_agent
from backend.rag_store import index_waterproof_sequence_doc, search_waterproof_sequence
from backend.storage import (
    list_site_ids,
    load_common_db,
    load_site_db,
    save_common_db,
    save_site_db,
)
from backend.templates import get_excel_templates
from backend.weather import build_weather_request, fetch_today_weather

app = FastAPI(title="Waterproof Work Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/")
def read_root():
    return {"message": "Waterproof Work Planner API is running. Visit /docs for API documentation."}

DEFAULT_MATERIAL_OPTIONS = [
    "우레탄방수재",
    "우레탄 하도(프라이머)",
    "우레탄 중도",
    "우레탄 상도",
    "복합방수 시트",
    "시멘트계 방수재 1종",
    "시멘트계 방수재 2종",
    "실란트",
]


class RAGConfig(BaseModel):
    areas: Dict[str, float] = Field(default_factory=dict)
    floors: Dict[str, List[str]] = Field(default_factory=dict)
    waterproof_sequences: Dict[str, List[str]] = Field(default_factory=dict)
    materials: List[str] = Field(default_factory=list)
    unit_productivity: Dict[str, float] = Field(default_factory=dict)
    env_factors: List[str] = Field(default_factory=list)


class UserSetup(BaseModel):
    workers: List[str] = Field(default_factory=list)
    inventory: Dict[str, float] = Field(default_factory=dict)
    progress_before_app: Optional[str] = None
    priority_areas: List[str] = Field(default_factory=list)
    previous_daily_report: Optional[str] = None
    floor_area_map: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    area_progress: Dict[str, float] = Field(default_factory=dict)
    area_waterproof_methods: Dict[str, str] = Field(default_factory=dict)
    latitude: Optional[float] = 37.46
    longitude: Optional[float] = 126.71


class WorkerAddRequest(BaseModel):
    site_id: str
    worker_name: str


class InventoryAddRequest(BaseModel):
    site_id: str
    material_name: str
    quantity: float


class DailyInput(BaseModel):
    site_id: str = Field(default="default-site")
    selected_workers: List[str]
    incoming_materials: Dict[str, float] = Field(default_factory=dict)
    priority_areas: List[str] = Field(default_factory=list)


class ProgressUpdateRequest(BaseModel):
    site_id: str
    area_progress: Dict[str, float]


class WorkItem(BaseModel):
    worker: str
    start: str
    end: str
    area: str
    task: str
    completed: bool = False
    note: Optional[str] = None

class DailyWorkResult(BaseModel):
    site_id: str
    date: str
    actual_work: List[WorkItem]  # 완료 및 추가된 실제 작업 내역


def _build_rag_context(common_db: Dict, site_db: Dict, payload: DailyInput, weather_data: Dict) -> Dict:
    rag = common_db.get("rag", {})
    sequence_query = ", ".join(payload.priority_areas or site_db.get("priority_areas", [])) or "방수 작업 순서"
    sequence_docs = search_waterproof_sequence(query=sequence_query, top_k=3).get("items", [])
    return {
        "worker_reg": payload.selected_workers,
        "priority_areas_rag": payload.priority_areas or site_db.get("priority_areas", []),
        "all_areas_rag": list(rag.get("areas", {}).keys()),
        "floor_area_map_rag": site_db.get("floor_area_map", {}),
        "area_progress_rag": site_db.get("area_progress", {}),
        "area_waterproof_methods_rag": site_db.get("area_waterproof_methods", {}),
        "previous_progress_rag": site_db.get("area_progress", {}),  # 어제까지의 진행도 (이전 area_progress)
        "previous_daily_report_rag": site_db.get("previous_daily_report"),
        "inventory_rag": site_db.get("inventory", {}),
        "weather_rag": weather_data,
        "waterproof_sequences_rag": {"retrieved_docs": sequence_docs},
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/reference/waterproof-sequence/index")
def index_waterproof_sequence(doc_path: str = "docs/waterproof_sequence.md"):
    return index_waterproof_sequence_doc(doc_path=doc_path)


@app.get("/api/reference/waterproof-sequence/search")
def search_waterproof_sequence_docs(query: str, top_k: int = 3):
    return search_waterproof_sequence(query=query, top_k=top_k)


@app.get("/api/usecase1/sites")
def get_sites():
    return {"sites": list_site_ids()}


@app.get("/api/usecase1/site/{site_id}")
def get_site_status(site_id: str):
    site_db = load_site_db(site_id)
    progress_data = calculate_site_progress(site_db)
    return {
        "site_id": site_id,
        "workers": site_db.get("workers", []),
        "inventory": site_db.get("inventory", {}),
        "priority_areas": site_db.get("priority_areas", []),
        "floor_area_map": site_db.get("floor_area_map", {}),
        "area_progress": site_db.get("area_progress", {}),
        "area_waterproof_methods": site_db.get("area_waterproof_methods", {}),
        "progress_before_app": site_db.get("progress_before_app"),
        "overall_progress": progress_data["total_progress"],
        "area_progress_details": progress_data["area_details"]
    }


@app.get("/api/usecase1/material-options")
def get_material_options():
    common_db = load_common_db()
    rag_materials = common_db.get("rag", {}).get("materials", [])
    
    # materials가 객체 리스트인 경우 name 속성만 추출
    if rag_materials and isinstance(rag_materials[0], dict):
        rag_materials = [m.get("name", "Unknown") for m in rag_materials]

    return {"materials": rag_materials or DEFAULT_MATERIAL_OPTIONS}


@app.post("/api/usecase1/workers")
def add_worker(payload: WorkerAddRequest):
    site_db = load_site_db(payload.site_id)
    workers = site_db.get("workers", [])
    if payload.worker_name not in workers:
        workers.append(payload.worker_name)
    site_db["workers"] = workers
    save_site_db(payload.site_id, site_db)
    return {"site_id": payload.site_id, "workers": workers}


@app.post("/api/usecase1/inventory")
def add_inventory(payload: InventoryAddRequest):
    site_db = load_site_db(payload.site_id)
    inventory = site_db.get("inventory", {})
    inventory[payload.material_name] = inventory.get(payload.material_name, 0) + payload.quantity
    site_db["inventory"] = inventory
    save_site_db(payload.site_id, site_db)
    return {"site_id": payload.site_id, "inventory": inventory}


@app.post("/api/usecase3/progress")
def update_area_progress(payload: ProgressUpdateRequest):
    site_db = load_site_db(payload.site_id)
    current = site_db.get("area_progress", {})
    current.update(payload.area_progress)
    site_db["area_progress"] = current
    save_site_db(payload.site_id, site_db)
    return {"site_id": payload.site_id, "area_progress": current}


@app.get("/api/reference/templates")
def template_reference():
    return get_excel_templates()


@app.get("/api/reference/weather-request")
def weather_request_preview(latitude: float, longitude: float):
    return build_weather_request(latitude=latitude, longitude=longitude)


@app.post("/api/usecase0/rag")
def save_rag(config: RAGConfig):
    common_db = load_common_db()
    common_db["rag"] = config.model_dump()
    save_common_db(common_db)
    return {"saved": True, "rag_keys": list(common_db["rag"].keys())}


@app.post("/api/usecase1/setup")
def initial_setup(payload: UserSetup, site_id: str = "default-site"):
    site_db = load_site_db(site_id)
    site_db["workers"] = payload.workers
    site_db["inventory"] = payload.inventory
    site_db["progress_before_app"] = payload.progress_before_app
    site_db["priority_areas"] = payload.priority_areas
    site_db["previous_daily_report"] = payload.previous_daily_report
    site_db["floor_area_map"] = payload.floor_area_map
    site_db["area_progress"] = payload.area_progress  # 초기 진행도 설정
    site_db["area_waterproof_methods"] = payload.area_waterproof_methods
    site_db["latitude"] = payload.latitude
    site_db["longitude"] = payload.longitude
    save_site_db(site_id, site_db)
    return {"saved": True, "site_id": site_id, "workers": len(site_db["workers"])}


@app.post("/api/usecase2/plan")
def create_plan(payload: DailyInput):
    print(f"DEBUG: create_plan called with site_id='{payload.site_id}'")
    common_db = load_common_db()
    site_db = load_site_db(payload.site_id)
    # site_db["area_progress"]는 이미 이전 작업 결과가 로드됨
    # (초기값: progress_before_app → update_area_progress로 지속 업데이트)

    for material, qty in payload.incoming_materials.items():
        site_db["inventory"][material] = site_db["inventory"].get(material, 0) + qty

    lat = site_db.get("latitude", 37.46)
    lon = site_db.get("longitude", 126.71)
    try:
        weather_data = fetch_today_weather(latitude=lat, longitude=lon)
    except Exception:
        weather_data = {
            "provider": "open-meteo",
            "location": {"latitude": lat, "longitude": lon},
            "hourly_weather": [],
            "summary": "날씨 정보 없음",
            "integration_status": "failed_fallback",
        }

    rag_context = _build_rag_context(common_db=common_db, site_db=site_db, payload=payload, weather_data=weather_data)
    llm_plan = run_planning_agent(rag_context)
    plan = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "weather": {
            "description": weather_data.get("summary", "날씨 정보 없음"),
            "temp_min": "-",
            "temp_max": "-",
            "humidity": "-",
            "precipitation_prob": "-"
        },
        "scheduler_status": llm_plan.get("scheduler_status", "llm_generated"),
        "model": llm_plan.get("model", "gemini-2.0-flash"),
        "timeline": llm_plan.get("timeline", []),
        "overview": llm_plan.get("overview", "AI가 생성한 작업 개요입니다."),
        "guidelines": llm_plan.get("guidelines", ["안전 수칙을 준수하세요."]),
        "notes": llm_plan.get("notes", []),
        "rag_context": rag_context,
    }

    # 같은 날짜의 기존 로그가 있다면 제거 (덮어쓰기)
    today_str = plan["date"]
    site_db["daily_logs"] = [log for log in site_db.get("daily_logs", []) if log.get("plan", {}).get("date") != today_str]
    
    site_db["daily_logs"].append({"input": payload.model_dump(), "plan": plan})
    save_site_db(payload.site_id, site_db)
    return {"site_id": payload.site_id, "plan": plan, "inventory": site_db["inventory"]}


@app.post("/api/usecase3/close")
def close_workday(completed: bool, note: Optional[str] = None):
    return {
        "completed": completed,
        "next_action": "edit_log" if not completed else "review_material_usage",
        "note": note,
    }

@app.post("/api/usecase3/work-result")
def save_daily_work_result(payload: DailyWorkResult):
    site_db = load_site_db(payload.site_id)
    common_db = load_common_db()
    
    # 1. 해당 날짜의 로그 찾기 또는 생성
    target_log = None
    for log in site_db.get("daily_logs", []):
        if log.get("plan", {}).get("date") == payload.date:
            target_log = log
            break
    
    if not target_log:
        target_log = {"plan": {"date": payload.date}}
        site_db["daily_logs"].append(target_log)
    
    # 2. 실제 작업 내역 저장
    target_log["actual_work"] = [item.model_dump() for item in payload.actual_work]
    
    # 3. area_progress 자동 업데이트 알고리즘
    current_progress = site_db.get("area_progress", {})
    rag_areas = common_db.get("rag", {}).get("areas", {})
    
    for item in payload.actual_work:
        if not item.completed:
            continue
            
        # 작업 구역 매칭 (예: "101동 3층" -> "101동")
        matched_area = None
        for area_key in current_progress.keys():
            if area_key in item.area:
                matched_area = area_key
                break
        
        if matched_area:
            # 진척도 증가량 계산
            increment = 2.0 # 기본 증가량 2%
            
            # 아파트 동인 경우 (층수 기반 계산)
            if matched_area.endswith("동"):
                # common.json에서 층수 정보 찾기
                buildings = rag_areas.get("세대", {}).get("buildings", [])
                floors = 26 # 기본값
                for b in buildings:
                    if b["name"] == matched_area:
                        floors = b.get("floors", 26)
                        break
                # 한 층 작업 완료 시 약 1/floors 만큼 증가 (100 / floors)
                increment = round(100 / floors, 1)
            
            elif matched_area == "지하주차장":
                # 존(Zone) 기반 (총 10개 존 가정)
                increment = 10.0
            
            elif matched_area == "상가":
                increment = 5.0

            # 진척도 업데이트 (최대 100%)
            new_val = current_progress.get(matched_area, 0) + increment
            current_progress[matched_area] = min(100.0, round(new_val, 1))

    site_db["area_progress"] = current_progress
    save_site_db(payload.site_id, site_db)
    
    return {
        "saved": True, 
        "date": payload.date, 
        "work_count": len(payload.actual_work),
        "updated_progress": current_progress
    }


@app.get("/api/usecase3/daily-report")
def download_daily_report(site_id: str, date: str):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, Side
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote

    site_db = load_site_db(site_id)
    target_log = None
    for log in site_db.get("daily_logs", []):
        if log.get("plan", {}).get("date") == date:
            target_log = log
            break
    
    if not target_log:
        return {"error": "해당 날짜의 로그를 찾을 수 없습니다."}

    wb = Workbook()
    ws = wb.active
    ws.title = "작업일지"

    # 기본 설정
    thin_side = Side(style='thin')
    border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)
    center_align = Alignment(horizontal='center', vertical='center', wrap_text=True)
    header_font = Font(size=14, bold=True)
    title_font = Font(size=20, bold=True)

    # 1. 제목 (작 업 일 지)
    ws.merge_cells('A1:L2')
    ws['A1'] = "작 업 일 지"
    ws['A1'].font = title_font
    ws['A1'].alignment = center_align
    for row in ws['A1:L2']:
        for cell in row:
            cell.border = border

    # 2. 기본 정보 영역
    # 작성일, 반장명, 현장명
    y, m, d = date.split('-')
    ws.merge_cells('A3:F3')
    ws['A3'] = f"■ 작성일 : 20{y[2:]}년 {m}월 {d}일"
    ws['A3'].alignment = Alignment(horizontal='left')
    
    # 반장명 (무조건 정도은)
    ws.merge_cells('A4:F4')
    ws['A4'] = f"■ 반장명 : 정도은"
    
    ws.merge_cells('A5:F5')
    ws['A5'] = f"■ 현장명 : {site_id}"

    # 결재란 (우측 상단)
    ws.merge_cells('G3:G5')
    ws['G3'] = "결\n재"
    ws['G3'].alignment = center_align
    ws['G3'].border = border

    ws.merge_cells('H3:I3')
    ws['H3'] = "반 장"
    ws.merge_cells('J3:K3')
    ws['J3'] = "팀 장"
    ws['L3'] = "소 장"
    
    for row in range(3, 6):
        for col in range(7, 13):
            ws.cell(row=row, column=col).border = border
            ws.cell(row=row, column=col).alignment = center_align

    # 3. 메인 테이블 헤더
    ws.merge_cells('A6:C6')
    ws['A6'] = "출 력 현 황"
    ws.merge_cells('D6:L6')
    ws['D6'] = "금 일 작 업 내 용"
    
    for col in range(1, 13):
        ws.cell(row=6, column=col).border = border
        ws.cell(row=6, column=col).alignment = center_align
        ws.cell(row=6, column=col).font = Font(bold=True)

    # 4. 좌측: 출력 현황 데이터
    ws['A7'] = "순번"
    ws.merge_cells('B7:C7')
    ws['B7'] = "성 명"
    
    actual_work = target_log.get("actual_work", [])
    
    # 작업자 명단 추출 (쉼표로 구분된 경우 분리하여 개별 인원 파악)
    raw_workers = []
    for w in actual_work:
        worker_str = w.get("worker", "")
        if worker_str:
            # "정고은, 정노은" 형태를 ["정고은", "정노은"]으로 분리
            split_workers = [name.strip() for name in worker_str.split(",") if name.strip()]
            raw_workers.extend(split_workers)
            
    # 중복 제거 및 정렬
    attending_workers = sorted(list(set(raw_workers)))
    
    for i in range(15): # 최대 15명 표시
        row_idx = 8 + i
        ws[f'A{row_idx}'] = i + 1
        ws.merge_cells(f'B{row_idx}:C{row_idx}')
        if i < len(attending_workers):
            ws[f'B{row_idx}'] = attending_workers[i]
        
        for col in range(1, 4):
            ws.cell(row=row_idx, column=col).border = border
            ws.cell(row=row_idx, column=col).alignment = center_align
    
    # 5. 우측: 작업 내용
    ws.merge_cells('D7:L15')
    
    # 작업 내용 상세 리스트 (구역별로 그룹화하여 더 깔끔하게)
    area_tasks = {}
    for w in actual_work:
        area = w.get('area', '공통')
        task = w.get('task', '미지정 작업')
        if area not in area_tasks:
            area_tasks[area] = []
        if task not in area_tasks[area]:
            area_tasks[area].append(task)
    
    work_lines = []
    for area, tasks in area_tasks.items():
        work_lines.append(f"[{area}] {', '.join(tasks)}")
    
    start_time = min([w.get('start', '08:00') for w in actual_work]) if actual_work else "08:00"
    end_time = max([w.get('end', '17:00') for w in actual_work]) if actual_work else "17:00"
    
    content_text = f"1. 작업시작: {start_time}\n2. 작업종료: {end_time}\n3. 작업내용:\n" + "\n".join(work_lines)
    ws['D7'] = content_text
    ws['D7'].alignment = Alignment(wrap_text=True, vertical='top')
    for row in range(7, 16):
        for col in range(4, 13):
            ws.cell(row=row, column=col).border = border

    # 6. 자재 및 장비 현황
    ws.merge_cells('D16:H16')
    ws['D16'] = "금일 자재 반입 현황"
    ws.merge_cells('I16:L16')
    ws['I16'] = "장비 반입/반출 현황"
    
    ws.merge_cells('D17:H22')
    incoming = target_log.get("input", {}).get("incoming_materials", {})
    mat_text = "\n".join([f"- {m}: {q}" for m, q in incoming.items()])
    ws['D17'] = mat_text
    ws['D17'].alignment = Alignment(wrap_text=True, vertical='top')
    
    ws.merge_cells('I17:L22')
    # 장비 정보는 현재 없으므로 빈칸
    
    for row in range(16, 23):
        for col in range(4, 13):
            ws.cell(row=row, column=col).border = border
            ws.cell(row=row, column=col).alignment = center_align

    # 컬럼 너비 조정
    for col in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L']:
        ws.column_dimensions[col].width = 10

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    filename = f"daily_report_{site_id}_{date}.xlsx"
    encoded_filename = quote(filename)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"}
    
    return StreamingResponse(output, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


def calculate_site_progress(site_db: Dict) -> Dict:
    """현장의 전체 진척률을 계산하는 알고리즘"""
    area_progress = site_db.get("area_progress", {})
    floor_area_map = site_db.get("floor_area_map", {})
    
    if not area_progress:
        return {"total_progress": 0, "area_details": {}}
    
    total_weighted_progress = 0
    total_weight = 0
    area_details = []

    # 1. 면적 정보가 있는 경우 가중치 적용
    # 2. 면적 정보가 없는 경우 균등 가중치 적용
    for area_name, progress in area_progress.items():
        # 면적 합산 (floor_area_map: {floor: {area: size}})
        area_size = 0
        for floor_data in floor_area_map.values():
            if area_name in floor_data:
                area_size += floor_data[area_name]
        
        # 면적 정보가 없으면 기본값 1 적용
        weight = area_size if area_size > 0 else 1
        
        total_weighted_progress += progress * weight
        total_weight += weight
        
        area_details.append({
            "name": area_name,
            "progress": progress,
            "weight": weight
        })

    total_progress = round(total_weighted_progress / total_weight, 1) if total_weight > 0 else 0
    
    return {
        "total_progress": total_progress,
        "area_details": sorted(area_details, key=lambda x: x["name"])
    }
