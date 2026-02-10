# hyeonjang_note MVP

## 실행

### 1. 가상환경 생성 및 활성화
```bash
# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정
- `.env` 파일을 생성하거나 환경변수를 직접 설정합니다.
```bash
# Windows PowerShell
$env:GOOGLE_API_KEY="your_key"

# Mac/Linux
export GEMINI_API_KEY="your_key"
```

### 4. 서버 실행
- **백엔드** (가상환경 변경 감지 제외 옵션 포함)
```bash
uvicorn backend.main:app --reload --reload-dir backend --reload-dir data
```
- **프론트엔드** (새 터미널에서 실행)
```bash
cd frontend
python -m http.server 5500
```

## 접속 주소
- 백엔드 API: http://localhost:8000
- 프론트엔드: http://localhost:5500

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
- `waterproof_sequence_docs_rag` (벡터 검색 결과)

## 벡터 스토어
- 문서: `docs/waterproof_sequence.md`
- 저장소: `data/vector_store`
- 컬렉션: `waterproof_sequences`
- 인덱싱 API: `POST /api/reference/waterproof-sequence/index`
- 검색 API: `GET /api/reference/waterproof-sequence/search?query=...`

## 주요 API
- `POST /api/usecase0/rag` : 공통 RAG 저장
- `POST /api/usecase1/setup?site_id=<id>` : 현장 초기 구조화 데이터 저장
- `POST /api/usecase2/plan` : 계획 생성
- `POST /api/usecase3/progress` : 구역별 진행률 업데이트
