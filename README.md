# hyeonjang_note MVP

## 실행

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key
uvicorn backend.main:app --reload
```

## DB 구조(현재)
- 공통 DB: `data/common.json`
  - `rag` (공통 작업지식)
- 현장 DB: `data/sites/<site_id>.json`
  - `workers`
  - `inventory`
  - `priority_areas`
  - `floor_area_map` (구역별/층별 면적)
  - `area_progress` (구역별 진행률)
  - `area_waterproof_methods` (구역별 방수 방식)
  - `previous_daily_report`, `progress_before_app`
  - `daily_logs`

## LLM 입력 컨텍스트(프롬프트 변수)
- `worker_reg`
- `priority_areas_rag`
- `all_areas_rag`
- `floor_area_map_rag`
- `area_progress_rag`
- `area_waterproof_methods_rag`
- `previous_progress_rag`
- `previous_daily_report_rag`
- `inventory_rag`
- `weather_rag` (시간별 온도/습도/강수확률/강수)
- `waterproof_sequences_rag`

## 주요 API
- `POST /api/usecase0/rag` : 공통 RAG 저장
- `POST /api/usecase1/setup?site_id=<id>` : 현장 초기 구조화 데이터 저장
- `POST /api/usecase2/plan` : 계획 생성
- `POST /api/usecase3/progress` : 구역별 진행률 업데이트
