from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.ai_agent import run_planning_agent
from backend.rag import get_rag_stack_recommendation
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
    weather_summary: Optional[str] = None


def _build_rag_context(common_db: Dict, site_db: Dict, payload: DailyInput, weather_data: Dict) -> Dict:
    rag = common_db.get("rag", {})
    return {
        "workers_rag": payload.selected_workers,
        "priority_areas_rag": payload.priority_areas or site_db.get("priority_areas", []),
        "all_areas_rag": list(rag.get("areas", {}).keys()),
        "previous_progress_rag": site_db.get("progress_before_app"),
        "previous_daily_report_rag": site_db.get("previous_daily_report"),
        "inventory_rag": site_db.get("inventory", {}),
        "weather_rag": weather_data,
        "waterproof_sequences_rag": rag.get("waterproof_sequences", {}),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


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


@app.get("/api/reference/rag-stack")
def rag_stack_reference():
    return get_rag_stack_recommendation()


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
    common_db["waterproof_sequences"] = config.waterproof_sequences
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
    site_db["latitude"] = payload.latitude
    site_db["longitude"] = payload.longitude
    save_site_db(site_id, site_db)
    return {"saved": True, "site_id": site_id, "workers": len(site_db["workers"])}


@app.post("/api/usecase2/plan")
def create_plan(payload: DailyInput):
    common_db = load_common_db()
    site_db = load_site_db(payload.site_id)

    for material, qty in payload.incoming_materials.items():
        site_db["inventory"][material] = site_db["inventory"].get(material, 0) + qty

    lat = site_db.get("latitude", 37.46)
    lon = site_db.get("longitude", 126.71)
    try:
        weather_data = fetch_today_weather(latitude=lat, longitude=lon)
    except Exception:
        weather_data = {
            "provider": "open-meteo",
            "integration_status": "failed_fallback",
            "manual_weather_summary": payload.weather_summary,
        }

    rag_context = _build_rag_context(common_db=common_db, site_db=site_db, payload=payload, weather_data=weather_data)
    llm_plan = run_planning_agent(
        {
            "workers": payload.selected_workers,
            "priority_areas": rag_context["priority_areas_rag"],
            "all_areas": rag_context["all_areas_rag"],
            "previous_progress": rag_context["previous_progress_rag"],
            "previous_daily_report": rag_context["previous_daily_report_rag"],
            "inventory": rag_context["inventory_rag"],
            "weather": rag_context["weather_rag"],
            "waterproof_sequences": rag_context["waterproof_sequences_rag"],
        }
    )
    plan = {
        "date": __import__("datetime").datetime.now().strftime("%Y-%m-%d"),
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
