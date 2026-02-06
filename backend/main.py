from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

from backend.planner import build_daily_plan

app = FastAPI(title="Waterproof Work Planner")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB: Dict[str, dict] = {
    "rag": {},
    "workers": [],
    "inventory": {},
    "daily_logs": [],
}


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
    selected_workers: List[str]
    incoming_materials: Dict[str, float] = Field(default_factory=dict)
    priority_areas: List[str] = Field(default_factory=list)
    weather_summary: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/usecase0/rag")
def save_rag(config: RAGConfig):
    DB["rag"] = config.model_dump()
    return {"saved": True, "rag_keys": list(DB["rag"].keys())}


@app.post("/api/usecase1/setup")
def initial_setup(payload: UserSetup):
    DB["workers"] = payload.workers
    DB["inventory"] = payload.inventory
    DB["speed_profile"] = payload.speed_profile
    DB["progress_before_app"] = payload.progress_before_app
    return {"saved": True, "workers": len(DB["workers"])}


@app.post("/api/usecase2/plan")
def create_plan(payload: DailyInput):
    for material, qty in payload.incoming_materials.items():
        DB["inventory"][material] = DB["inventory"].get(material, 0) + qty

    plan = build_daily_plan(
        rag=DB.get("rag", {}),
        workers=payload.selected_workers,
        priority_areas=payload.priority_areas,
        weather_summary=payload.weather_summary,
    )
    DB["daily_logs"].append({"input": payload.model_dump(), "plan": plan})
    return {"plan": plan, "inventory": DB["inventory"]}


@app.post("/api/usecase3/close")
def close_workday(completed: bool, note: Optional[str] = None):
    return {
        "completed": completed,
        "next_action": "edit_log" if not completed else "review_material_usage",
        "note": note,
    }
