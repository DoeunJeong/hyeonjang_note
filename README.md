# hyeonjang_note MVP

요구사항(Usecase0~4)을 반영한 초기 프로토타입입니다.

## 실행

```bash
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

프론트엔드는 `frontend/index.html`을 브라우저로 열어 사용합니다.

## 현재 범위
- FastAPI API 뼈대
- LangChain 연동 전 스텁
- HTML/CSS/JS 타임라인 화면
- 기본 테스트

## 다음 단계
- 실제 RAG 저장/검색 구현
- 날씨 API 연동
- 엑셀 출력 기능 구현
