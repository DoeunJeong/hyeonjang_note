# 🏗️ 현장노트 (Hyeonjang Note)
### AI 기반 방수 공사 관리 및 자동화 플랫폼

**현장노트**는 AI(Gemini 2.0 Flash)와 RAG(Retrieval-Augmented Generation) 기술을 활용하여 방수 공사 현장의 복잡한 작업 계획 수립을 자동화하고, 실제 작업 데이터를 기반으로 공정률 관리 및 전문적인 작업일지 생성을 지원하는 스마트 건설 관리 솔루션입니다.

---

## 🚀 주요 기능 (Key Features)

### 1. AI 지능형 작업 계획 수립
- **날씨 및 현장 분석**: 실시간 기상 데이터(Open-Meteo)와 현장 특이사항을 분석하여 최적의 작업 스케줄 제안.
- **RAG 기반 표준 공정 적용**: 표준 방수 시방서 및 공정 순서를 참고하여 전문적인 작업 할당.
- **표 형식의 직관적 출력**: 시간별, 구역별, 작업자별 계획을 한눈에 파악 가능한 표 형태로 제공.

### 2. 시각적 공정률 관리
- **가중치 기반 공정률 알고리즘**: 동별 층수 및 구역별 면적을 반영한 정교한 진척도 계산.
- **실시간 대시보드**: 전체 공정률 및 각 세부 구역별 진척도를 시각적인 프로그레스 바로 확인.

### 3. 작업 마감 및 자동 보고서 생성
- **디지털 체크리스트**: AI 계획을 기반으로 실제 수행 여부를 체크하고 추가/돌발 작업 기록.
- **자동 진척도 업데이트**: 작업 마감 시 완료된 내역에 따라 구역별 진척도 자동 갱신.
- **전문 작업일지(Excel) 출력**: 실제 현장에서 사용하는 종이 서식 포맷 그대로 엑셀 보고서 자동 생성 (출력현황, 작업내용, 자재현황 포함).

### 4. 노무 및 자재 관리
- **노무대장 자동 산출**: 작업 종료 시간에 따른 공수(1.0/1.5) 자동 계산 및 엑셀 다운로드.
- **인벤토리 관리**: 자재 입고 및 소모 내역 실시간 추적.

---

## 🛠️ 기술 스택 (Tech Stack)

- **Backend**: Python, FastAPI, LangChain, Google Gemini 2.0 Flash
- **Database/Vector Store**: SQLite, ChromaDB
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla JS)
- **Data Processing**: Pandas, Openpyxl

---

## ⚙️ 시작하기 (Getting Started)

### 1. 환경 설정
`.env` 파일을 생성하고 아래 키를 설정합니다.
```env
GEMINI_API_KEY=your_google_api_key_here
```

### 2. 백엔드 실행
```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

### 3. 프론트엔드 실행
`frontend/index.html` 파일을 브라우저에서 열거나 로컬 서버를 통해 실행합니다.

---

## 📁 프로젝트 구조 (Folder Structure)

- `backend/`: FastAPI 기반 API 서버 및 AI 에이전트 로직
- `frontend/`: 웹 UI (HTML, CSS, JS)
- `data/`: RAG 문서 및 기본 설정 데이터 (현장 상세 내역은 제외됨)
- `reindex_rag.py`: RAG 문서 인덱싱 스크립트

---

## 📄 라이선스 (License)
본 프로젝트는 교육 및 관리 효율화를 목적으로 개발되었습니다.
