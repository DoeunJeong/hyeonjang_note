# 반영된 결정 사항 (2026-02-06)

아래 항목은 사용자 답변을 기준으로 코드에 반영했습니다.

1. 날씨 데이터 소스
   - 무료 API로 Open-Meteo를 채택.
   - 현재는 API 호출 명세 생성 함수만 구현하고, 실제 HTTP 호출은 제외.

2. RAG 저장소
   - 벡터 DB: Chroma
   - 임베딩 모델: Google `models/text-embedding-004`

3. 일정 알고리즘
   - RAG 문서 완성 전까지 `scheduler_status=skeleton` 으로 유지.

4. 엑셀 템플릿
   - Usecase 기반 템플릿 컬럼 정의를 코드에 추가(재고/작업일지/노무대장/세대 진행도).
   - 추후 사진 기반 서식 디테일(병합셀/색상/로고) 보강 예정.

5. 다중 현장
   - 공통 DB(`data/common.json`)와 현장별 DB(`data/sites/<site_id>.json`) 분리 저장 구조 반영.
