# hyeonjang_note MVP

## 실행

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key
uvicorn backend.main:app --reload
```

## 이번 반영 내용
- Gemini + LangChain 기반 작업계획 에이전트 연결 (`backend/ai_agent.py`)
  - `GEMINI_API_KEY`가 없거나 호출 실패 시 fallback 계획 자동 생성
- Usecase2 계획 생성 시 RAG 컨텍스트를 독립 항목으로 구성
  - 인력 / 우선작업구역 / 전체구역 / 이전진행 / 이전일보 / 자재 / 날씨
- Open-Meteo 실제 호출을 통해 당일 날씨를 수집하고 weather_rag로 전달
- Material 옵션은 고정 상수 대신 RAG 문서(`usecase0/rag.materials`) 우선 반영
- 타임라인 UI를 템플릿 요구에 맞춰 변경
  - 행: 시간(30분 단위)
  - 열: 작업자(좌측 기준)
  - 각 셀에 작업계획 배치

## 주요 API
- `POST /api/usecase0/rag` : RAG 문서 저장
- `GET /api/usecase1/material-options` : RAG 기반 자재 옵션
- `POST /api/usecase2/plan` : Gemini+RAG+날씨 기반 계획 생성

- 날씨 조회 기본 위치는 37.46N, 126.71E (site 설정에서 변경 가능)
