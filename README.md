# hyeonjang_note MVP

요구사항(Usecase0~4) 기반 초기 프로토타입입니다.

## 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 GOOGLE_API_KEY 입력

# 3. 서버 실행
uvicorn backend.main:app --reload
```

프론트엔드는 `frontend/index.html`을 브라우저로 열어 사용합니다.

## RAG (Retrieval-Augmented Generation) 설정

### 파일 구조

```
data/
├── common.json                    # 공통 설정 + RAG 메타데이터
├── sites/
│   └── <site_id>.json            # 현장별 데이터
└── rag_docs/                      # RAG 문서 저장소
    ├── waterproof_sequences.md   # 방수 시공 순서 가이드
    ├── materials_guide.md         # 자재 가이드
    └── best_practices.md          # 모범 사례 모음
```

### RAG 문서 작성 방법

**Markdown 형식 추천** (`data/rag_docs/*.md`):
- **구조화**: 헤더, 표, 리스트로 구성
- **검색성**: 태그, 키워드 포함
- **예제**: 실제 사례, 수치, 체크리스트
- **유지보수**: 평문 편은 버전 관리 용이

**RAG 메타데이터** (`data/common.json`의 `rag.documents`):
```json
{
  "id": "seq-001",
  "path": "data/rag_docs/waterproof_sequences.md",
  "title": "방수 시공 순서 가이드",
  "tags": ["sequence", "우레탄", "시공절차"]
}
```

### 임베딩 및 벡터 DB

- **Vector DB**: Chroma (저장 위치: `data/chroma_db/`)
- **Embedding**: Google `models/text-embedding-004`
- **컬렉션**: `site_<site_id>` 또는 `common`
- **자동 인덱싱**: Usecase0 RAG 설정 저장 시 트리거

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
- **RAG 문서 저장소** (`data/rag_docs/`) 구성
  - `waterproof_sequences.md`: 시공 순서 가이드
  - `materials_guide.md`: 자재 특성 및 선택 기준
  - `best_practices.md`: 실제 현장 사례 및 교훈

## 주요 API
- `POST /api/usecase0/rag` : 공통 RAG 설정 저장
- `POST /api/usecase1/setup?site_id=<id>` : 현장별 최초 설정
- `POST /api/usecase2/plan` : 현장별 작업 계획 생성
- `POST /api/usecase3/close` : 작업 후 마감
- `GET /api/reference/rag-stack` : RAG 스택 레퍼런스
- `GET /api/reference/templates` : 엑셀 템플릿 컬럼
- `GET /api/reference/weather-request` : 날씨 API 호출 명세
