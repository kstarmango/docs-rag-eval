# PLAN — Shopify Support RAG (작업/인수인계 문서)

> 이 파일 = 프로젝트 단일 진실원. 다음 세션은 여기부터 읽고 이어간다.
> (auto-memory `project_microsaas_ideation.md`에서 이 폴더를 가리킴)

## 왜 만드나 (맥락)
- 목표 = **AI 응용 계약일**용 간판 포트폴리오. 돈+미래분야(AI엔지니어링) 동시.
- 수요 근거(2026 실측): AI 챗봇 +71%, AI통합 +178%, RAG 단가 $150~250/hr. "우리 데이터로 답하는 봇"이 수요 1위 공고와 직결.
- 차별화 원칙: 기능 카피 = "80% 똑같은 포폴" 함정. **좁고 깊게 + "어려운 층"으로** 승부.

## 무엇을 (스코프 고정)
Shopify 공개 헬프센터(help.shopify.com) 위에서 답하는 **지원 어시스턴트**. 딱 이 corpus 하나.

## 어려운 층 (= 포폴 가치, 반드시 포함)
1. 인용/출처 링크 — 모든 답에 근거 문서·섹션
2. "모름" 처리 — 관련 문서 없거나 확신 낮으면 환각 대신 모른다고
3. ⭐retrieval eval 하네스 — Q&A 20~30개로 검색 정확도 수치화 (hit@k)
4. 검색 트레이스 노출 — 어떤 청크가 검색됐는지 UI에 표시
5. (여유) 청킹 전략 A/B + 근거 문서화, 피드백/에스컬레이션

## 스택
Python / FastAPI(백엔드) · pgvector(벡터DB) · Claude API(LLM) · React(프론트) · Python eval harness · Docker→Fly.io/Render(배포·라이브 URL 필수)
- ⚠️ LangChain/LlamaIndex는 배관에만. retrieval·eval은 직접 튜닝(블랙박스 클론 금지).

## 데이터 접근 (확인 완료 2026-07-24)
- robots.txt: 본문 문서 크롤링 허용(추적파라미터·검색·로그인·CSV만 차단). sitemap: `help.shopify.com/sitemap.xml`
- 본문 완전 정적 추출 가능(JS 렌더링 불필요). crawl-delay 1s 준수. 포폴 데모용(상업재배포X).

## 4주 계획
- **1주**: 기본 파이프라인 (sitemap 수집→청킹→임베딩→pgvector→검색→Claude 답변) 로컬 작동
- **2주**: 어려운 층 (인용·모름처리·eval 하네스·검색 트레이스)
- **3주**: React UI + 배포(라이브) + eval 보며 검색품질 개선
- **4주**(버퍼): 케이스스터디 글·README·데모 영상

## 현재 상태 (진행 로그)
- [x] 2026-07-24: 폴더·git 생성(`side-project/shopify-support-rag`, 독립 repo), Python 3.12.4 venv, 문서 세팅(README/PLAN/.gitignore), 초기 커밋
- [ ] 1주차: 수집 스크립트부터 (다음 착수 지점)

## 학습 메모 (사용자 = RAG·FastAPI 처음)
- teach-mode: 한 덩어리씩 설명하며 진행. 용어 전제 깔지 말 것.
- venv = 이 프로젝트 전용 파이썬 패키지 격리 상자 (전역 오염 방지).
