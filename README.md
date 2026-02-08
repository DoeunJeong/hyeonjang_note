# hyeonjang_note MVP

요구사항(Usecase0~4) 기반 초기 프로토타입입니다.

## 실행

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

프론트엔드는 `frontend/index.html`을 브라우저로 열어 사용합니다.

## 이번 반영 내용
- Usecase1 화면 구체화
  - 현장 선택/생성 후 Usecase2로 이동
  - 작업인력 이름 입력 → 추가 반복
  - 우측 테이블로 작업인력/재고 현황 표시
  - 자재는 드롭다운 선택 + `직접입력` 지원
- 다중 현장 분리 저장
  - 공통: `data/common.json`
  - 현장별: `data/sites/<site_id>.json`
- 일정 생성기는 스켈레톤 상태로 유지 (`scheduler_status=skeleton`)
- 무료 날씨 API(Open-Meteo) 호출 명세 스텁
- RAG 추천 스택: Chroma + Google `models/text-embedding-004`

## 주요 API
- `GET /api/usecase1/sites` : 현장 목록
- `GET /api/usecase1/site/{site_id}` : 현장 상태(인력/재고)
- `GET /api/usecase1/material-options` : 자재 드롭다운 옵션
- `POST /api/usecase1/workers` : 인력 추가
- `POST /api/usecase1/inventory` : 자재 입고 반영
- `POST /api/usecase2/plan` : 현장별 작업 계획 생성
