# 🏗️ 현장노트 (Hyeonjang Note)

### AI 기반 방수 공사 현장 관리 플랫폼

**현장노트**는 Google Gemini 2.0 Flash와 RAG(ChromaDB + Google Embeddings) 기술을 활용하여 방수 공사 현장의 **일일 작업 계획 자동 수립**, **공정률 관리**, **작업일지·노무대장 자동 생성**을 지원하는 스마트 건설 관리 웹 애플리케이션입니다.

---

## 🚀 주요 기능

### 1. 현장 설정 (Use Case 1)
- **다중 현장 관리**: 현장별 독립 JSON DB로 여러 현장을 동시에 관리
- **인력 등록**: 작업자 이름 등록 및 일일 투입 인력 선택
- **자재 관리**: 자재 입고 수량 등록 및 실시간 재고 추적
- **구역 구성**: 동/층별 면적, 방수 공법, 공정률을 현장별로 설정

### 2. AI 작업 계획 수립 (Use Case 2)
- **5단계 파이프라인**: 현장 데이터 로드 → 날씨 조회 → RAG 컨텍스트 구성 → AI 계획 생성 → 저장 및 반환
- **날씨 연동**: Open-Meteo API로 시간별 기온·습도·강수확률을 조회, 강우 시 실내 작업 우선 배정
- **RAG 기반 공정 참조**: ChromaDB에 저장된 방수 시방서·공정 순서를 검색하여 AI 프롬프트에 반영
- **층수 범위 지정**: 시작층~끝층을 입력하면 아랫층부터 윗층 순서로 작업을 배정
- **구체적 위치 배정**: "세대" 대신 "101동 3층", "105동 4층" 등 구체적 위치를 명시
- **30분 단위 타임라인**: 08:00~17:00 시간 슬롯으로 작업자·구역·작업 내용을 표로 출력

### 3. 작업 마감 및 보고서 (Use Case 3)
- **디지털 체크리스트**: AI 계획을 기반으로 실제 수행 여부를 체크하고, 추가/돌발 작업 기록
- **진척도 자동 갱신**: 작업 완료 내역에 따라 구역별 공정률 자동 업데이트
- **작업일지 Excel 출력**: 현장 종이 서식을 그대로 재현한 전문 양식 (출력현황, 금일 작업내용, 시공상태 점검, 자재 반입 현황)
- **노무대장 Excel 출력**: 작업자별 × 일자별 공수표 자동 산출 (17:00 초과 시 1.5공, 이하 1.0공)

### 4. 시각적 공정률 대시보드
- **가중치 기반 산출**: 동별 층수 및 구역별 면적을 반영한 정교한 전체 공정률 계산
- **프로그레스 바**: 전체 공정률 + 구역별 진척도를 시각적 바로 표시

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|------|------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **AI/LLM** | Google Gemini 2.0 Flash (`gemini-2.0-flash`), LangChain |
| **RAG** | ChromaDB, Google Generative AI Embeddings (`gemini-embedding-001`) |
| **날씨** | Open-Meteo API (무료, API 키 불필요) |
| **Frontend** | HTML5, CSS3, Vanilla JavaScript (SPA) |
| **Excel 출력** | openpyxl (작업일지), pandas + openpyxl (노무대장) |
| **데이터 저장** | 파일 기반 JSON (현장별 `data/sites/*.json`) |

---

## 📁 프로젝트 구조

```
hyeonjang_note/
├── backend/
│   ├── main.py            # FastAPI 앱, 모든 API 엔드포인트, Excel 생성 로직
│   ├── ai_agent.py        # Gemini AI 계획 생성 에이전트 (LangChain 체인)
│   ├── storage.py         # 파일 기반 JSON 저장소 (현장별 CRUD)
│   ├── weather.py         # Open-Meteo 날씨 API 클라이언트
│   ├── rag_store.py       # ChromaDB 벡터 스토어 (문서 인덱싱 / 검색)
│   └── templates.py       # Excel 템플릿 참조
├── frontend/
│   ├── index.html         # SPA 메인 페이지 (3개 뷰: 설정/계획/마감)
│   ├── app.js             # 프론트엔드 로직 (API 호출, UI 렌더링)
│   └── styles.css         # 스타일시트
├── data/
│   ├── common.json        # 공통 RAG 설정 (구역, 자재, 제약조건)
│   ├── rag_docs/
│   │   └── waterproof_sequences.md  # 방수 공정 순서 문서 (RAG 소스)
│   ├── sites/             # 현장별 JSON DB (URL인코딩 파일명)
│   └── vector_store/      # ChromaDB 영구 저장소
├── tests/
│   └── test_api.py        # API 테스트
├── requirements.txt       # Python 패키지 목록
├── reindex_rag.py         # RAG 문서 재인덱싱 스크립트
└── .env                   # API 키 설정 (GOOGLE_API_KEY)
```

---

## ⚙️ 시작하기

### 1. 환경 설정

`.env` 파일을 프로젝트 루트에 생성합니다:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

> Google AI Studio에서 Gemini API 키를 발급받을 수 있습니다: https://aistudio.google.com/

### 2. 가상환경 및 패키지 설치

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. RAG 문서 인덱싱 (최초 1회)

```bash
python reindex_rag.py
```

> `data/rag_docs/waterproof_sequences.md` 문서를 ChromaDB에 청크 단위로 임베딩합니다.

### 4. 서버 실행

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 5. 접속

브라우저에서 **http://127.0.0.1:8000** 으로 접속합니다.

> FastAPI가 프론트엔드 정적 파일을 직접 서빙합니다. 별도의 프론트엔드 서버(Live Server 등)는 불필요합니다.

---

## 📡 API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/health` | 서버 상태 확인 |
| `GET` | `/api/usecase1/sites` | 전체 현장 목록 조회 |
| `GET` | `/api/usecase1/site/{site_id}` | 현장 상태 조회 (인력, 자재, 공정률) |
| `POST` | `/api/usecase1/setup` | 현장 초기 설정 저장 |
| `POST` | `/api/usecase1/workers` | 작업자 추가 |
| `POST` | `/api/usecase1/inventory` | 자재 입고 등록 |
| `GET` | `/api/usecase1/material-options` | 자재 종류 목록 조회 |
| `POST` | `/api/usecase2/plan` | **AI 일일 작업 계획 생성** |
| `POST` | `/api/usecase3/save-work` | 실제 작업 결과 저장 |
| `POST` | `/api/usecase3/progress` | 구역별 공정률 수동 업데이트 |
| `GET` | `/api/usecase3/work-report` | 작업일지 Excel 다운로드 |
| `GET` | `/api/usecase3/manpower-log` | 노무대장 Excel 다운로드 |
| `POST` | `/api/reference/waterproof-sequence/index` | RAG 문서 인덱싱 |
| `GET` | `/api/reference/waterproof-sequence/search` | RAG 벡터 검색 |

---

## 🔄 AI 계획 생성 흐름

```
[프론트엔드]                    [백엔드]                         [외부 서비스]
                                                                
투입 인력 선택 ──┐                                               
층수 범위 입력 ──┤              ① 현장 DB 로드                   
우선 구역 입력 ──┘─── POST ──→ ② Open-Meteo 날씨 조회 ────────→ Open-Meteo API
                               ③ ChromaDB RAG 검색 ────────────→ ChromaDB
                               ④ Gemini AI 호출 ──────────────→ Google Gemini
                               ⑤ 계획 저장 & 반환                
타임라인 표시 ←──── JSON ─────                                   
```

---

## 📊 데이터 구조

### 현장 DB (`data/sites/*.json`)

```json
{
  "site_id": "인천제일검단",
  "workers": ["김방수", "이미장", "정고은"],
  "inventory": { "우레탄 중도": 100.0, "프라이머": 50.0 },
  "priority_areas": ["101동", "102동"],
  "floor_area_map": { "101동": { "3층": 120.5, "4층": 120.5 } },
  "area_progress": { "101동 3층": 30.0, "101동 4층": 0.0 },
  "area_waterproof_methods": { "세대": "M03", "지하주차장": "M01" },
  "latitude": 37.46,
  "longitude": 126.71,
  "daily_logs": []
}
```

---

## 📄 라이선스

본 프로젝트는 교육 및 건설 현장 관리 효율화를 목적으로 개발되었습니다.
