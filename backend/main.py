from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.planner import build_daily_plan
from backend.rag import get_rag_stack_recommendation
from backend.storage import (
    list_site_ids,
    load_common_db,
    load_site_db,
    save_common_db,
    save_site_db,
)
from backend.templates import get_excel_templates
from backend.weather import build_weather_request

app = FastAPI(title="Waterproof Work Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MATERIAL_OPTIONS = [
    "우레탄",
    "프라이머",
    "복합방수재",
    "시멘트계 방수재",
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
        "progress_before_app": site_db.get("progress_before_app"),
    }


@app.get("/api/usecase1/material-options")
def get_material_options():
    return {"materials": MATERIAL_OPTIONS}


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
    save_site_db(site_id, site_db)
    return {"saved": True, "site_id": site_id, "workers": len(site_db["workers"])}


@app.post("/api/usecase2/plan")
def create_plan(payload: DailyInput):
    common_db = load_common_db()
    site_db = load_site_db(payload.site_id)

    for material, qty in payload.incoming_materials.items():
        site_db["inventory"][material] = site_db["inventory"].get(material, 0) + qty

    plan = build_daily_plan(
        rag=common_db.get("rag", {}),
        workers=payload.selected_workers,
        priority_areas=payload.priority_areas,
        weather_summary=payload.weather_summary,
    )
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
