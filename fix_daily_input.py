"""Fix: move floor_start/floor_end from UserSetup to DailyInput."""
import pathlib

p = pathlib.Path(__file__).parent / "backend" / "main.py"
src = p.read_text("utf-8")

# Remove from UserSetup (wrongly placed)
src = src.replace(
    "    priority_areas: List[str] = Field(default_factory=list)\n"
    "    floor_start: Optional[int] = None\n"
    "    floor_end: Optional[int] = None\n"
    "    previous_daily_report:",
    "    priority_areas: List[str] = Field(default_factory=list)\n"
    "    previous_daily_report:",
    1
)

# Add to DailyInput
old_daily = (
    "class DailyInput(BaseModel):\n"
    "    site_id: str = Field(default=\"default-site\")\n"
    "    selected_workers: List[str]\n"
    "    incoming_materials: Dict[str, float] = Field(default_factory=dict)\n"
    "    priority_areas: List[str] = Field(default_factory=list)"
)
new_daily = (
    "class DailyInput(BaseModel):\n"
    "    site_id: str = Field(default=\"default-site\")\n"
    "    selected_workers: List[str]\n"
    "    incoming_materials: Dict[str, float] = Field(default_factory=dict)\n"
    "    priority_areas: List[str] = Field(default_factory=list)\n"
    "    floor_start: Optional[int] = None\n"
    "    floor_end: Optional[int] = None"
)
src = src.replace(old_daily, new_daily, 1)

p.write_text(src, "utf-8")
print("Fixed: floor fields moved to DailyInput")
