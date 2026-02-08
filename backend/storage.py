from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data")
COMMON_FILE = DATA_DIR / "common.json"
SITES_DIR = DATA_DIR / "sites"


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITES_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_site_ids() -> List[str]:
    _ensure_dirs()
    return sorted(path.stem for path in SITES_DIR.glob("*.json"))


def load_common_db() -> Dict[str, Any]:
    _ensure_dirs()
    return _read_json(
        COMMON_FILE,
        {
            "rag": {},
            "waterproof_sequences": {},
            "constraints": [],
        },
    )


def save_common_db(payload: Dict[str, Any]) -> None:
    _ensure_dirs()
    _write_json(COMMON_FILE, payload)


def load_site_db(site_id: str) -> Dict[str, Any]:
    _ensure_dirs()
    site_file = SITES_DIR / f"{site_id}.json"
    return _read_json(
        site_file,
        {
            "site_id": site_id,
            "workers": [],
            "inventory": {},
            "speed_profile": {},
            "progress_before_app": None,
            "daily_logs": [],
        },
    )


def save_site_db(site_id: str, payload: Dict[str, Any]) -> None:
    _ensure_dirs()
    site_file = SITES_DIR / f"{site_id}.json"
    _write_json(site_file, payload)
