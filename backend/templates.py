from typing import Dict, List


def get_excel_templates() -> Dict[str, List[str]]:
    """Usecase 기준 엑셀 템플릿 컬럼 정의."""
    return {
        "inventory": [
            "date",
            "material_name",
            "incoming_qty",
            "used_qty",
            "running_total",
        ],
        "work_journal": [
            "date",
            "site_name",
            "company_name",
            "weather",
            "today_summary_ai",
            "area",
            "task",
            "incoming_materials",
            "used_materials",
            "equipment_cost_notes",
        ],
        "labor_ledger": [
            "date",
            "worker_name",
            "day_or_night",
            "multiplier",
            "gongsoo",
            "notes",
        ],
        "household_progress": [
            "date",
            "building",
            "unit_or_zone",
            "waterproof_type",
            "progress_percent",
            "highlight_memo",
        ],
    }
