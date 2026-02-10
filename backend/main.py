from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    return {
        "site_id": site_id,
        "workers": site_db.get("workers", []),
        "inventory": site_db.get("inventory", {}),
        "priority_areas": site_db.get("priority_areas", []),
        "floor_area_map": site_db.get("floor_area_map", {}),
        "area_progress": site_db.get("area_progress", {}),
        "area_waterproof_methods": site_db.get("area_waterproof_methods", {}),
        "progress_before_app": site_db.get("progress_before_app"),
    }


@app.get("/api/usecase1/material-options")
def get_material_options():
    common_db = load_common_db()
    rag_materials = common_db.get("rag", {}).get("materials", [])
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
        "scheduler_status": llm_plan.get("scheduler_status", "llm_generated"),
        "model": llm_plan.get("model", "gemini-2.0-flash"),
        "timeline": llm_plan.get("timeline", []),
        "notes": llm_plan.get("notes", []),
        "rag_context": rag_context,
    }

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
