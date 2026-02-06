from typing import Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.planner import build_daily_plan
from backend.rag import get_rag_stack_recommendation
from backend.storage import load_common_db, load_site_db, save_common_db, save_site_db
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


class RAGConfig(BaseModel):
    areas: Dict[str, float] = Field(default_factory=dict)
    floors: Dict[str, List[str]] = Field(default_factory=dict)
    waterproof_sequences: Dict[str, List[str]] = Field(default_factory=dict)
    materials: List[str] = Field(default_factory=list)
    unit_productivity: Dict[str, float] = Field(default_factory=dict)
    env_factors: List[str] = Field(default_factory=list)


class UserSetup(BaseModel):
    workers: List[str]
    inventory: Dict[str, float]
    speed_profile: Dict[str, float] = Field(default_factory=dict)
    progress_before_app: Optional[str] = None


class DailyInput(BaseModel):
    site_id: str = Field(default="default-site")
    selected_workers: List[str]
    incoming_materials: Dict[str, float] = Field(default_factory=dict)
    priority_areas: List[str] = Field(default_factory=list)
    weather_summary: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


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
    site_db["speed_profile"] = payload.speed_profile
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
