# hyeonjang_note MVP

요구사항(Usecase0~4) 기반 초기 프로토타입입니다.

## 실행

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

프론트엔드는 `frontend/index.html`을 브라우저로 열어 사용합니다.

## 이번 반영 내용
- 다중 현장 분리 저장
  - 공통: `data/common.json`
  - 현장별: `data/sites/<site_id>.json`
- 일정 생성기는 스켈레톤 상태로 유지 (`scheduler_status=skeleton`)
- 무료 날씨 API(Open-Meteo) 호출 명세 스텁 추가
- RAG 추천 스택 추가
  - Vector DB: Chroma
  - Embedding: Google `models/text-embedding-004`
- Usecase4 엑셀 템플릿 컬럼 정의 API 추가

## 주요 API
- `POST /api/usecase0/rag` : 공통 RAG 설정 저장
- `POST /api/usecase1/setup?site_id=<id>` : 현장별 최초 설정
- `POST /api/usecase2/plan` : 현장별 작업 계획 생성
- `POST /api/usecase3/close` : 작업 후 마감
- `GET /api/reference/rag-stack` : RAG 스택 레퍼런스
- `GET /api/reference/templates` : 엑셀 템플릿 컬럼
- `GET /api/reference/weather-request` : 날씨 API 호출 명세
