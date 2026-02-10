from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import logging
from urllib.parse import quote, unquote

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 현재 파일(backend/storage.py)의 상위 폴더(backend)의 상위 폴더(root) 기준 data 폴더
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
COMMON_FILE = DATA_DIR / "common.json"
SITES_DIR = DATA_DIR / "sites"


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    SITES_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        logger.warning(f"File not found: {path}. Returning default.")
        return default
    try:
        content = path.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {path}: {e}")
        return default
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return default


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_site_ids() -> List[str]:
    _ensure_dirs()
    # 파일명(URL 인코딩됨)을 디코딩하여 ID 반환
    # 예: %EC%9D%B8%EC%B2%9C.json -> 인천
    return sorted(unquote(path.stem) for path in SITES_DIR.glob("*.json"))


def load_common_db() -> Dict[str, Any]:
    _ensure_dirs()
    return _read_json(
        COMMON_FILE,
        {
            "rag": {},
            "constraints": [],
        },
    )


def save_common_db(payload: Dict[str, Any]) -> None:
    _ensure_dirs()
    _write_json(COMMON_FILE, payload)


def load_site_db(site_id: str) -> Dict[str, Any]:
    _ensure_dirs()
    # site_id를 파일명으로 쓸 때는 인코딩 (안전하게)
    # 한글 -> %EC%...
    safe_name = quote(site_id)
    site_file = SITES_DIR / f"{safe_name}.json"
    
    # 하위 호환성: 인코딩 안 된 파일이 있다면 그것을 우선 (마이그레이션 전)
    legacy_file = SITES_DIR / f"{site_id}.json"
    if legacy_file.exists():
        return _read_json(
            legacy_file,
            {
                "site_id": site_id,
                "workers": [],
                "inventory": {},
                "priority_areas": [],
                "floor_area_map": {},
                "area_progress": {},
                "area_waterproof_methods": {},
                "progress_before_app": None,
                "previous_daily_report": None,
                "latitude": 37.46,
                "longitude": 126.71,
                "daily_logs": [],
            }
        )

    return _read_json(
        site_file,
        {
            "site_id": site_id,
            "workers": [],
            "inventory": {},
            "priority_areas": [],
            "floor_area_map": {},
            "area_progress": {},
            "area_waterproof_methods": {},
            "progress_before_app": None,
            "previous_daily_report": None,
            "latitude": 37.46,
            "longitude": 126.71,
            "daily_logs": [],
        },
    )


def save_site_db(site_id: str, payload: Dict[str, Any]) -> None:
    _ensure_dirs()
    # 저장할 때는 무조건 인코딩된 파일명 사용
    safe_name = quote(site_id)
    site_file = SITES_DIR / f"{safe_name}.json"
    
    # 만약 레거시 파일이 있다면 삭제 (중복 방지)
    legacy_file = SITES_DIR / f"{site_id}.json"
    if legacy_file.exists():
        try:
            legacy_file.unlink()
        except Exception:
            pass # 삭제 실패해도 무시
            
    print(f"DEBUG: Saving site db to {site_file} (Original ID: {site_id})")
    _write_json(site_file, payload)
