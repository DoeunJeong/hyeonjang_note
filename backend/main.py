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
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
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


@app.get("/", include_in_schema=False)
async def serve_index():
    """Serve frontend index.html"""
    from fastapi.responses import FileResponse as FR
    return FR(BASE_DIR / "frontend" / "index.html")

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


class WorkItemInput(BaseModel):
    site_id: str
    work_items: List[dict]


class DailyInput(BaseModel):
    site_id: str = Field(default="default-site")
    selected_workers: List[str]
    incoming_materials: Dict[str, float] = Field(default_factory=dict)
    priority_areas: List[str] = Field(default_factory=list)
    floor_start: Optional[int] = None
    floor_end: Optional[int] = None


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
    print("    -> [3-1] RAG 컨텍스트 빌드 함수 진입")
    rag = common_db.get("rag", {})
    sequence_query = ", ".join(payload.priority_areas or site_db.get("priority_areas", [])) or "방수 작업 순서"
    
    print(f"    -> [3-2] RAG 문서 검색 시작 (쿼리: '{sequence_query}')")
    try:
        sequence_docs = search_waterproof_sequence(query=sequence_query, top_k=3).get("items", [])
        print("    -> [3-3] RAG 문서 검색 성공")
    except Exception as e:
        print(f"    -> [!!!] RAG 문서 검색 중 치명적 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        raise e

    return {
        "worker_reg": payload.selected_workers,
        "priority_areas_rag": payload.priority_areas or site_db.get("priority_areas", []),
        "all_areas_rag": list(rag.get("areas", {}).keys()),
        "floor_area_map_rag": site_db.get("floor_area_map", {}),
        "area_progress_rag": site_db.get("area_progress", {}),
        "area_waterproof_methods_rag": site_db.get("area_waterproof_methods", {}),
        "previous_progress_rag": site_db.get("area_progress", {}),
        "previous_daily_report_rag": site_db.get("previous_daily_report"),
        "inventory_rag": site_db.get("inventory", {}),
        "weather_rag": weather_data,
        "waterproof_sequences_rag": {"retrieved_docs": sequence_docs},
        "floor_range_rag": {"start": payload.floor_start, "end": payload.floor_end},
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



def calculate_site_progress(site_db):
    """현장의 전체 진행도를 계산합니다."""
    area_progress = site_db.get("area_progress", {})
    floor_area_map = site_db.get("floor_area_map", {})

    if not area_progress:
        return {"total_progress": 0.0, "area_details": {}}

    total_area = 0.0
    weighted_progress = 0.0
    area_details = {}

    for area, progress in area_progress.items():
        area_size = 0.0
        for floor, areas in floor_area_map.items():
            if isinstance(areas, dict) and area in areas:
                area_size = areas[area]
                break
        if area_size == 0.0:
            area_size = 100.0
        total_area += area_size
        weighted_progress += area_size * progress
        area_details[area] = {"progress": progress, "area": area_size}

    total_progress = (weighted_progress / total_area) if total_area > 0 else 0.0
    return {"total_progress": round(total_progress, 2), "area_details": area_details}


@app.get("/api/usecase1/site/{site_id}")
def get_site_status(site_id: str):
    site_db = load_site_db(site_id)
    progress_data = calculate_site_progress(site_db)

    # 최신 plan 가져오기 (daily_logs에서)
    latest_plan = None
    daily_logs = site_db.get("daily_logs", [])
    if daily_logs:
        last_log = daily_logs[-1]
        if isinstance(last_log, dict) and "plan" in last_log:
            latest_plan = last_log["plan"]

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
        "area_progress_details": progress_data["area_details"],
        "latest_plan": latest_plan
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
async def create_plan(payload: DailyInput):
    print("\n--- [1/5] 'create_plan' API 시작 ---")
    print(f"입력 데이터: site_id='{payload.site_id}', workers={len(payload.selected_workers)}")
    
    common_db = load_common_db()
    site_db = load_site_db(payload.site_id)

    for material, qty in payload.incoming_materials.items():
        site_db["inventory"][material] = site_db["inventory"].get(material, 0) + qty

    lat = site_db.get("latitude", 37.46)
    lon = site_db.get("longitude", 126.71)
    
    print("--- [2/5] 날씨 정보 조회 시작 ---")
    try:
        weather_data = fetch_today_weather(latitude=lat, longitude=lon)
        print("날씨 정보 조회 성공")
    except Exception as e:
        print(f"날씨 정보 조회 실패: {e}")
        weather_data = {"summary": "날씨 정보 없음"}

    print("--- [3/5] RAG 컨텍스트 빌드 시작 ---")
    rag_context = _build_rag_context(common_db=common_db, site_db=site_db, payload=payload, weather_data=weather_data)
    print("RAG 컨텍스트 빌드 성공")

    print("--- [4/5] AI 에이전트 호출 시작 ---")
    llm_plan = await run_planning_agent(rag_context)
    print("--- [5/5] AI 에이전트 응답 수신 및 최종 데이터 정리 ---")
    
    plan = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "weather": { "description": weather_data.get("summary", "날씨 정보 없음") },
        "scheduler_status": llm_plan.get("scheduler_status", "llm_generated"),
        "model": llm_plan.get("model", "gemini-2.0-flash"),
        "timeline": llm_plan.get("timeline", []),
        "overview": llm_plan.get("overview", "AI가 생성한 작업 개요입니다."),
        "guidelines": llm_plan.get("guidelines", ["안전 수칙을 준수하세요."]),
        "notes": llm_plan.get("notes", []),
    }

    today_str = plan["date"]
    site_db["daily_logs"] = [log for log in site_db.get("daily_logs", []) if log.get("plan", {}).get("date") != today_str]
    site_db["daily_logs"].append({"input": payload.model_dump(), "plan": plan})
    save_site_db(payload.site_id, site_db)
    
    print("--- 최종 응답 전송 완료 ---")
    return {"plan": plan}


@app.post("/api/usecase3/save-work")
def save_work_result(payload: WorkItemInput):
    """금일 작업 수행 내역 저장"""
    site_db = load_site_db(payload.site_id)
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_logs = site_db.get("daily_logs", [])
    
    # 오늘 로그 찾기
    today_log = None
    for log in daily_logs:
        if isinstance(log, dict) and log.get("plan", {}).get("date") == today_str:
            today_log = log
            break
    
    if today_log:
        today_log["work_result"] = payload.work_items
    else:
        daily_logs.append({"work_result": payload.work_items, "date": today_str})
    
    site_db["daily_logs"] = daily_logs
    save_site_db(payload.site_id, site_db)
    return {"status": "ok", "saved_items": len(payload.work_items)}


@app.get("/api/usecase3/work-report")
def download_work_report(site_id: str):
    """작업일지 Excel 다운로드 (현장 양식)"""
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    from openpyxl.utils import get_column_letter

    site_db = load_site_db(site_id)
    daily_logs = site_db.get("daily_logs", [])
    workers = site_db.get("workers", [])

    # 오늘 날짜의 로그 찾기
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_log = None
    for log in daily_logs:
        if isinstance(log, dict) and log.get("plan", {}).get("date") == today_str:
            today_log = log
            break

    # 로그가 없으면 가장 최근 로그 사용
    if not today_log and daily_logs:
        today_log = daily_logs[-1]

    # 작업 내역 수집
    work_items = []
    if today_log:
        work_items = today_log.get("work_result") or today_log.get("plan", {}).get("timeline", [])

    plan_data = today_log.get("plan", {}) if today_log else {}
    plan_date = plan_data.get("date", today_str)

    # 참여 인력 수집 (work_items에서 고유 작업자 추출)
    participating_workers = []
    seen = set()
    for item in work_items:
        w = item.get("worker", "") if isinstance(item, dict) else ""
        if w and w not in seen:
            participating_workers.append(w)
            seen.add(w)

    # 작업 내용 요약 (구역+작업 기준으로 통합, 인원수 표시)
    task_summary = {}  # {task_desc: count}
    for item in work_items:
        if isinstance(item, dict):
            area = item.get("area", "")
            task = item.get("task", "")
            desc = f"{area} {task}".strip() if area else task
            if desc:
                task_summary[desc] = task_summary.get(desc, 0) + 1

    # 작업 시작/종료 시간
    start_times = []
    end_times = []
    for item in work_items:
        if isinstance(item, dict):
            if item.get("start"): start_times.append(item["start"])
            if item.get("end"): end_times.append(item["end"])

    work_start = min(start_times) if start_times else ""
    work_end = max(end_times) if end_times else ""

    # 날씨 정보
    weather_desc = plan_data.get("weather", {}).get("description", "")

    # 자재 반입 현황
    input_data = today_log.get("input", {}) if today_log else {}
    incoming_materials = input_data.get("incoming_materials", {})

    # === Excel 생성 ===
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "작업일지"

    # 스타일 정의
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )
    header_font = Font(name="맑은 고딕", size=18, bold=True)
    sub_font = Font(name="맑은 고딕", size=10)
    bold_font = Font(name="맑은 고딕", size=10, bold=True)
    cell_font = Font(name="맑은 고딕", size=9)
    center_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left_align = Alignment(horizontal="left", vertical="center", wrap_text=True)
    header_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    # 열 너비 설정 (A~J)
    col_widths = [6, 6, 10, 5, 18, 18, 18, 18, 8, 8]
    for idx, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = w

    # --- Row 1: 제목 ---
    ws.merge_cells("A1:J1")
    title_cell = ws["A1"]
    title_cell.value = "작 업 일 지"
    title_cell.font = header_font
    title_cell.alignment = center_align
    ws.row_dimensions[1].height = 35

    # --- Row 2: 작성일, 현장명 ---
    ws.merge_cells("A2:C2")
    ws["A2"].value = f"■ 작성일: {plan_date}"
    ws["A2"].font = sub_font

    ws.merge_cells("D2:G2")
    ws["D2"].value = f"■ 현장명: {site_id}"
    ws["D2"].font = sub_font

    ws.merge_cells("H2:J2")
    ws["H2"].value = f"날씨: {weather_desc}" if weather_desc else ""
    ws["H2"].font = sub_font
    ws.row_dimensions[2].height = 22

    # --- Row 3: 출력현황 헤더 + 금일작업내용 헤더 ---
    ws.merge_cells("A3:C3")
    ws["A3"].value = "출력 현황"
    ws["A3"].font = bold_font
    ws["A3"].alignment = center_align
    ws["A3"].fill = header_fill
    ws["A3"].border = thin_border
    for c in ["B3", "C3"]:
        ws[c].border = thin_border

    ws.merge_cells("D3:J3")
    ws["D3"].value = "금일 작업 내용"
    ws["D3"].font = bold_font
    ws["D3"].alignment = center_align
    ws["D3"].fill = header_fill
    ws["D3"].border = thin_border
    for c in ["E3", "F3", "G3", "H3", "I3", "J3"]:
        ws[c].border = thin_border

    # --- Row 4: 출력현황 서브헤더 + 작업시작/종료 ---
    headers_left = ["순번", "일수", "성명"]
    for idx, h in enumerate(headers_left):
        col = get_column_letter(idx + 1)
        cell = ws[f"{col}4"]
        cell.value = h
        cell.font = bold_font
        cell.alignment = center_align
        cell.border = thin_border
        cell.fill = header_fill

    ws.merge_cells("D4:J4")
    start_h, start_m = (work_start.split(":") if ":" in work_start else ("", ""))
    end_h, end_m = (work_end.split(":") if ":" in work_end else ("", ""))
    ws["D4"].value = f"1. 작업시작: {start_h}시 {start_m}분    2. 작업종료: {end_h}시 {end_m}분"
    ws["D4"].font = sub_font
    ws["D4"].alignment = left_align
    ws["D4"].border = thin_border
    for c in ["E4", "F4", "G4", "H4", "I4", "J4"]:
        ws[c].border = thin_border

    # --- Row 5: 작업내용 라벨 ---
    ws.merge_cells("D5:J5")
    ws["D5"].value = "3. 작업내용:"
    ws["D5"].font = bold_font
    ws["D5"].alignment = left_align
    ws["D5"].border = thin_border
    for c in ["E5", "F5", "G5", "H5", "I5", "J5"]:
        ws[c].border = thin_border

    # 빈 출력현황 row 5
    for col_idx in range(1, 4):
        cell = ws.cell(row=5, column=col_idx)
        cell.border = thin_border

    # --- Rows 5+: 출력현황(작업자) & 작업내용 ---
    MAX_ROWS = 15
    tasks = list(task_summary.items())

    for row_offset in range(MAX_ROWS):
        row = 5 + row_offset
        if row_offset == 0:
            # Row 5 already has 작업내용 label, fill worker
            if participating_workers:
                ws[f"A5"].value = 1
                ws[f"A5"].font = cell_font
                ws[f"A5"].alignment = center_align
                ws[f"B5"].value = 1
                ws[f"B5"].font = cell_font
                ws[f"B5"].alignment = center_align
                ws[f"C5"].value = participating_workers[0]
                ws[f"C5"].font = cell_font
                ws[f"C5"].alignment = center_align
            continue

        row_num = 5 + row_offset + 1  # actual excel row = 6, 7, 8...
        # 출력현황 (작업자)
        worker_idx = row_offset
        for col_idx in range(1, 4):
            cell = ws.cell(row=row_num, column=col_idx)
            cell.border = thin_border
            cell.font = cell_font
            cell.alignment = center_align

        if worker_idx < len(participating_workers):
            ws.cell(row=row_num, column=1).value = worker_idx + 1
            ws.cell(row=row_num, column=2).value = 1
            ws.cell(row=row_num, column=3).value = participating_workers[worker_idx]

        # 금일 작업내용
        ws.merge_cells(start_row=row_num, start_column=4, end_row=row_num, end_column=8)
        ws.merge_cells(start_row=row_num, start_column=9, end_row=row_num, end_column=10)

        task_cell = ws.cell(row=row_num, column=4)
        count_cell = ws.cell(row=row_num, column=9)

        task_cell.border = thin_border
        count_cell.border = thin_border
        task_cell.font = cell_font
        count_cell.font = cell_font
        task_cell.alignment = left_align
        count_cell.alignment = center_align

        for c in range(5, 11):
            ws.cell(row=row_num, column=c).border = thin_border

        task_idx = row_offset - 1  # first task row starts at row_offset=1
        if task_idx >= 0 and task_idx < len(tasks):
            desc, count = tasks[task_idx]
            task_cell.value = f"  {desc}"
            count_cell.value = f"({count})"

    # --- 시공상태 점검결과 행 ---
    check_row = 5 + MAX_ROWS + 1
    for col_idx in range(1, 4):
        ws.cell(row=check_row, column=col_idx).border = thin_border

    ws.merge_cells(start_row=check_row, start_column=4, end_row=check_row, end_column=10)
    check_cell = ws.cell(row=check_row, column=4)
    check_cell.value = "4. 시공상태 점검결과: □ 양호 / □ 불량  (검사원:           )"
    check_cell.font = sub_font
    check_cell.alignment = left_align
    check_cell.border = thin_border
    for c in range(5, 11):
        ws.cell(row=check_row, column=c).border = thin_border

    # --- 자재 반입 현황 ---
    mat_header_row = check_row + 1
    ws.merge_cells(start_row=mat_header_row, start_column=1, end_row=mat_header_row, end_column=5)
    ws.merge_cells(start_row=mat_header_row, start_column=6, end_row=mat_header_row, end_column=10)

    mat_label = ws.cell(row=mat_header_row, column=1)
    mat_label.value = "금일 자재 반입 현황"
    mat_label.font = bold_font
    mat_label.alignment = center_align
    mat_label.fill = header_fill
    mat_label.border = thin_border

    equip_label = ws.cell(row=mat_header_row, column=6)
    equip_label.value = "장비 반입 / 반출 현황"
    equip_label.font = bold_font
    equip_label.alignment = center_align
    equip_label.fill = header_fill
    equip_label.border = thin_border

    for c in range(1, 11):
        ws.cell(row=mat_header_row, column=c).border = thin_border

    # 자재 반입 내역 rows
    mat_items = list(incoming_materials.items()) if incoming_materials else []
    for r_off in range(max(3, len(mat_items))):
        row = mat_header_row + 1 + r_off
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
        ws.merge_cells(start_row=row, start_column=6, end_row=row, end_column=10)
        for c in range(1, 11):
            ws.cell(row=row, column=c).border = thin_border
            ws.cell(row=row, column=c).font = cell_font

        if r_off < len(mat_items):
            name, qty = mat_items[r_off]
            ws.cell(row=row, column=1).value = f"  {name}: {qty}"
            ws.cell(row=row, column=1).alignment = left_align

    # === 파일 출력 ===
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    date_str = plan_date.replace("-", "")
    filename = quote(f"작업일지_{site_id}_{date_str}.xlsx")
    headers_resp = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
    }
    return StreamingResponse(
        output,
        headers=headers_resp,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.get("/api/usecase3/manpower-log")
def download_manpower_log(site_id: str):
    import pandas as pd
    from io import BytesIO
    from fastapi.responses import StreamingResponse
    from urllib.parse import quote

    site_db = load_site_db(site_id)
    daily_logs = site_db.get("daily_logs", [])
    
    # 데이터 수집: { 날짜: { 작업자: 공수 } }
    data = {}
    all_workers = set(site_db.get("workers", []))
    all_dates = set()

    for log in daily_logs:
        date = log.get("plan", {}).get("date")
        if not date:
            continue
        
        all_dates.add(date)
        if date not in data:
            data[date] = {}

        # 실제 작업 내역(actual_work)이 있으면 그것을 우선, 없으면 계획(plan.timeline) 사용
        work_items = log.get("actual_work") or log.get("plan", {}).get("timeline", [])
        
        # 작업자별 종료 시간 계산
        worker_end_times = {}
        for item in work_items:
            # item이 딕셔너리가 아닐 경우(Pydantic 모델 등) 처리
            if hasattr(item, "model_dump"):
                item = item.model_dump()
            
            worker_raw = item.get("worker", "")
            end_time_str = item.get("end")
            
            if not worker_raw or not end_time_str:
                continue

            # "정고은, 정노은" 같이 한 칸에 여러 명이 들어온 경우 분리
            worker_names = [w.strip() for w in worker_raw.replace("/", ",").split(",") if w.strip()]
            
            for worker in worker_names:
                all_workers.add(worker)
                
                # 시간 비교 (문자열 "17:00" 등)
                if worker not in worker_end_times:
                    worker_end_times[worker] = end_time_str
                else:
                    if end_time_str > worker_end_times[worker]:
                        worker_end_times[worker] = end_time_str
        
        # 공수 계산
        for worker, end_time in worker_end_times.items():
            # 17:00 초과면 1.5, 아니면 1.0
            man_day = 1.5 if end_time > "17:00" else 1.0
            data[date][worker] = man_day

    # DataFrame 생성
    # 행: 작업자, 열: 날짜
    sorted_dates = sorted(list(all_dates))
    sorted_workers = sorted(list(all_workers))
    
    # 0.0으로 초기화된 DataFrame
    df = pd.DataFrame(index=sorted_workers, columns=sorted_dates).fillna(0.0)
    
    for date, workers_map in data.items():
        for worker, manday in workers_map.items():
            df.at[worker, date] = manday

    # Excel 파일 생성
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="노무대장")
    
    output.seek(0)
    
    filename_base = f"manpower_log_{site_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    encoded_filename = quote(filename_base)
    
    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
    }
    
    return StreamingResponse(output, headers=headers, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


# ── 프론트엔드 정적 파일 서빙 (CSS, JS 등) ────────
app.mount("/", StaticFiles(directory=str(BASE_DIR / "frontend")), name="frontend")
