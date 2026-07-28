# PLAN — CITE (docs RAG · Medusa corpus) — 작업/인수인계 문서

> 공개 레포: https://github.com/kstarmango/docs-rag-eval (PUBLIC) · 제품명 **CITE**

> 이 파일 = 프로젝트 단일 진실원. 다음 세션은 여기부터 읽고 이어간다.
> (auto-memory `project_microsaas_ideation.md`에서 이 폴더를 가리킴)

## 왜 만드나 (맥락)
- 목표 = **AI 응용 계약일**용 간판 포트폴리오. 돈+미래분야(AI엔지니어링) 동시.
- 수요 근거(2026 실측): AI 챗봇 +71%, AI통합 +178%, RAG 단가 $150~250/hr. "우리 데이터로 답하는 봇"이 수요 1위 공고와 직결.
- 차별화 원칙: 기능 카피 = "80% 똑같은 포폴" 함정. **좁고 깊게 + "어려운 층"으로** 승부.

## 무엇을 (스코프 고정)
**Medusa 상점주 user-guide**(오픈소스 e-commerce, 주문·반품·교환·상품·재고·프로모션·배송) 위에서 답하는 **지원 어시스턴트**. 딱 이 corpus 하나.
- 왜 e-commerce: 시장조사(2026) 결론 = 가장 접근 쉬운 바이어=SMB 쇼핑몰 지원봇, 도메인이 buyer-legible해야 "so what/토이" 반응 회피. Medusa=쇼핑몰 문서 중 git-clone 깨끗+MIT.
- 피치: "Medusa 상점문서로 만든 걸 당신 Shopify 헬프센터+주문데이터로 그대로."

## 어려운 층 (= 포폴 가치, 반드시 포함)
1. 인용/출처 링크 — 모든 답에 근거 문서·섹션
2. "모름" 처리 — 관련 문서 없거나 확신 낮으면 환각 대신 모른다고
3. ⭐retrieval eval 하네스 — Q&A 20~30개로 검색 정확도 수치화 (hit@k)
4. 검색 트레이스 노출 — 어떤 청크가 검색됐는지 UI에 표시
5. (여유) 청킹 전략 A/B + 근거 문서화, 피드백/에스컬레이션

## 스택
Python / FastAPI(백엔드) · pgvector(벡터DB) · **Groq `llama-3.3-70b`(무료, OpenAI호환)**(LLM) · React(프론트) · Python eval harness · Docker→Fly.io/Render(배포·라이브 URL 필수)
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
- [x] 2026-07-24: 폴더·git 생성(`side-project/shopify-support-rag`, 독립 repo), Python 3.12.4 venv, 문서 세팅, 초기 커밋 `ee729bd`
- [x] 2026-07-24: **corpus 변경 Shopify→n8n docs.** 이유=Shopify 헬프센터 Cloudflare 봇차단(403, requests 불가). n8n=문서 전부 마크다운 공개레포(`n8n-io/n8n-docs`)라 `git clone`으로 스크래핑 없이 확보. 성격(제품지원문서 RAG)·클라전환력 동일 + n8n=자동화툴이라 "AI자동화" 수요와 겹침. 교훈=RAG 목표인데 스크래핑 싸움 금지, 깨끗한 소스 우선.
- [x] 2026-07-24: **수집→청킹 완성.** `data/raw/n8n-docs` clone(depth1, gitignore). `ingest/load_and_chunk.py`: 핵심 7폴더 347문서→**청크 2,535개**(평균635자). frontmatter `url`=인용출처. 헤더기준 분할+overlap150, HTML앵커 청소. 산출=`data/chunks.json`(gitignore).
- [x] 2026-07-24: **임베딩+벡터DB 완성.** Docker pgvector(pg16) 컨테이너 `shopify-rag-pg`. ⚠️**포트 함정**: 호스트에 기존 postgres가 5433 점유 → 인증실패. **5544로 이전**(.env DB_PORT=5544). 임베딩=fastembed 로컬무료 `bge-small-en-v1.5`(384d). `ingest/embed_and_store.py`(DB선확인+임베딩 디스크캐시 `data/embeddings.npy`). **pgvector에 2,532행**(중복3 제거)+HNSW 코사인 인덱스.
- [x] 2026-07-24: **검색(retrieval) 완성**(`a660b50`). `rag/search.py`: 질문 임베딩→pgvector 코사인 top-k. 실측 양호("error handling" 질문→top score 0.83 정확 문서). ⚠️소흠: url 없는 청크(frontmatter에 url 無)는 source_url=None → 경로로 fallback 만들기(폴리싱).
- [x] 2026-07-27: **[6] 답변 생성 완성 (`5f15cad`) → 기본 루프(1주차) 완성.** `rag/answer.py`: 검색→번호매긴 컨텍스트→Groq(`llama-3.3-70b-versatile`, OpenAI호환)→인용[n]+출처URL. `openai 2.48.0` venv설치+requirements freeze. 실측: 정상질문 "error handling"→인용3개 정답(top 0.83), 범위밖 "프랑스 수도"→"모른다".
  - 🔑 키: 중앙 `~/.claude/secrets.env`의 `API_GROQ_KEY`. 코드=`os.getenv("API_GROQ_KEY")`. ⚠️현 셸이 키추가 前 시작이라 env 미로드 → 실행 시 secrets.env를 명령 안에서 인라인 로드(값 미출력)해 python에 주입. 재시작 불필요.
  - ⚠️**발견(차별화층 재료)**: 모름처리 2겹(유사도컷 `MIN_SCORE=0.35` + LLM 컨텍스트-only 프롬프트) 중 **점수컷은 사실상 무력** — bge-small은 무관 영어도 코사인 0.4~0.5대에 몰려 안 떨어짐. 실제 안전망=LLM 거부. → eval 하네스로 모름처리 정확도 수치화할 것. 흠: (b)도 `grounded=True`로 찍힘(=LLM에 보냄 뜻일뿐) → refusal 감지로 라벨 다듬기.
- [x] 2026-07-28: **GitHub 공개 정리.** 레포 `docs-rag-eval`(PUBLIC), 제품명 CITE. 웹 네이밍관행조사=포폴레포는 설명형>순수약어→"설명형 레포명+약어는 제품명" 절충. README 실제스택으로 교정.
- [x] 2026-07-28: **★corpus 교체 n8n→Medusa (시장조사 근거).** 2각도 병렬리서치 결론: ①가장 접근쉬운 바이어=SMB e-commerce 지원봇 ②"그냥 문서챗봇"=commodity화(노코드SaaS 건당과금에 밀림)→차별화는 eval·정직성·에러분석·트레이스에서(도메인은 legibility만 삼). Medusa user-guide 72문서→**청크 605개**(평균493자). ingester를 MDX용 재작성: title=`export const metadata`에서, url=파일경로(`docs.medusajs.com/user-guide/<slug>`), MDX노이즈(import/export/JSX/`{/* */}`) 제거. 노이즈잔여 0·null 0. 재임베딩 605행 저장. 실측: "반품 생성" top 0.836 정답, 범위밖 "프랑스수도" LLM거부.
- [ ] ★**다음 = 차별화 층**(eval 하네스 수치·정직성·트레이스). ⚠️사용자 지적: 여기까지는 튜토리얼과 동일, 차별화는 전적으로 이 층에서. 반드시 엄격히. **로드맵(임팩트순, 시장조사 근거)**: ①eval 골드셋 30~50개(고객질문→정답문서)→Recall@k **=헤드라인** ②모름처리+시연(없는질문 거부 증명) ③에러분석 1회+실패유형표 공개(가장 시니어스러운 한방) ④검색트레이스 UI노출 ⑤before/after 수치 케이스스터디(영어·LinkedIn) ⑥하이브리드(BM25+벡터)+리랭커 측정개선.
  - ⚠️**즉시 고칠 라벨버그**: 범위밖 질문도 `grounded=True`로 찍힘(=top_score≥0.35일뿐, 실제론 LLM이 거부). `grounded`를 "실제 답변했나"로 재정의 필요(refusal 감지). ②의 일부.
  - 데이터포인트(임계값 튜닝용): grounded질문 top≈0.79~0.84 vs 범위밖 top≈0.44~0.46 → 0.35는 너무 낮음. eval로 최적 컷 측정.

## 인프라 재현 메모 (새 세션/재부팅 후)
- 컨테이너 꺼졌으면: `docker start shopify-rag-pg` (데이터 유지됨). 없으면 재생성(포트 5544, `CREATE EXTENSION vector`) 후 `python ingest/embed_and_store.py`(임베딩 캐시 있으면 즉시).
- 스택 확정: fastembed(bge-small 384d) · pgvector(HNSW cosine) · Docker :5544.

## 학습 메모 (사용자 = RAG·FastAPI 처음)
- teach-mode: 한 덩어리씩 설명하며 진행. 용어 전제 깔지 말 것.
- venv = 이 프로젝트 전용 파이썬 패키지 격리 상자 (전역 오염 방지).
