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
### ★전략 결정 (2026-07-28) — 목표=계약(취업 아님)이라 시퀀스 확정
목적 재확인: **AI 응용 "계약일"**(돈+미래), 바이어=SMB e-commerce. 포폴 볼 사람=계약 클라(≠채용담당).
- 지원질문 2종: **A=문서로 답**(정책·how-to, "환불 어떻게") / **B=실데이터 필요**("내 주문 #1234 어디"). 쇼핑몰 문의 다수가 B.
- 순수 docs-eval은 사실 *취업트랙* 최적화. 계약 클라가 사는 건 Recall@k 표가 아니라 "내 고객 질문 답하네"(=B). **그래서 B를 "막연한 나중"→명시적 2번 마일스톤으로 승격.**
- 단 B부터 가면 "토이 아님" 숫자가 없음 + A eval은 지금 바로 가능(코퍼스 완성), B는 새 인프라 필요. → **택일 아니라 순서.**
- ⚠️corpus 성격: Medusa user-guide=**상점운영자(admin) how-to**. 즉 우리 봇=1차로 "머천트 지원봇"(문서 A) + 2차로 주문조회(B, 고객대면). 케이스스터디에서 이 조합 강조.

### 다음 = 차별화 층 (3 마일스톤, 각각 shippable)
- [x] **M1. eval 헤드라인 완성** (`2e29f94`, 2026-07-28). `eval/gold_set.json`(정상39+범위밖7) + `eval/run_eval.py`(검색eval=LLM분리, 정직성eval). **첫 스코어카드: Recall@1 69.2%·@3 94.9%·@5 94.9%·MRR 0.816·범위밖거부 100%(7/7)·오거부 5.1%.** answer.py 버그 2개 수정(시스템프롬프트 n8n→Medusa, grounded[검색통과]≠answered[거부아님] 라벨 분리).
- [x] **에러분석 → 리랭커 → 재측정 완성** (`5d124bc`, 2026-07-28). 진단(`eval/diagnose.py`): 실패 3건 다 **ranking 문제**(정답 청크가 top-8엔 있으나 표면 단어충돌에 밀림, import↔export 임베딩 혼동 등). 해결=**cross-encoder 리랭커**(`ms-marco-MiniLM-L-6-v2`, top-20 후보 재채점), `RAG_RERANK` env 토글. **Before→After: Recall@1 69.2→76.9·@3 94.9→97.4·@5 94.9→100·MRR .816→.861·오거부 5.1→2.6·검색실패 2→0.** 아티팩트 `eval/results_baseline.json`·`results_reranked.json`, README에 before/after 표+한계 기록.
  - ⚠️남긴 실패 q28(고의): "add a new customer" vs 문서 "create a customer"=어휘갭. 정답문서 top-5엔 오나 create섹션 청크 미검색→**환각 대신 정직한 거부**(안전한 실패). 오버피팅 안 하고 한계로 문서화. 다음후보=쿼리확장/청크수준 스코어링.
  - ⚠️Groq 무료 **일일 10만 토큰(TPD)** 한도: eval 풀런(LLM 46콜)이 ~11만 토큰이라 하루 1~2회가 한계. 검색지표는 `EVAL_SKIP_LLM=1`로 무료 재생성. 정직성 수치는 트랜스크립트/README에 기록됨(내일 리셋 후 full JSON 재생성 가능).
- [x] **M2. 얇은 B 슬라이스 + M3 라우팅 골격 완성** (`860128e`, 2026-07-28). `rag/mock_orders.json`(12건, 상태 다양) + `rag/orders.py`(lookup_order/find_orders_by_email, 결정론적 테스트 완료) + `rag/assistant.py`(LLM에 search_help_docs·lookup_order 툴 노출, tool-calling으로 라우팅, 환각 대신 에스컬레이션). **8b로 plumbing 검증**: 주문질문→lookup_order 정확답변("10432 배송중/송장/ETA"), how-to→search_help_docs 라우팅, 환각0. ⚠️**70b 최종 검증 미완**(오늘 Groq TPD 소진)=문서합성 답변품질·깔끔한 에스컬레이션 문구는 내일 리셋 후 확인. answer.py(문서전용, eval용)와 별개 파일.
- [x] **웹 데모(FastAPI + 프론트) 착수** (`8c4ffc2`, 2026-07-28, LLM-free 부분). `api/main.py`: `/api/search`(검색 트레이스=청크+벡터점수+**리랭크점수**, LLM 불필요)·`/api/order/{id}`·`/api/ask`(어시스턴트, LLM)·정적 프론트 서빙. `api/static/index.html`: 단일페이지 데모, 질문→**리랭커가 벡터순위를 어떻게 재정렬하는지 눈으로 보이는 트레이스**+Ask박스. 검색/주문/트레이스 **오늘 검증 완료**(리랭커 시각화 잘 나옴: bulk-editor 벡터1위지만 리랭크가 products/import로 교체). `/ask`는 Groq 미로드/토큰소진시 친절한 에러. fastapi+uvicorn 설치, requirements 갱신. ⚠️서버 기동=`venv\Scripts\python.exe -m uvicorn api.main:app --port 8000`(⚠️/ask 쓰려면 secrets.env 로드한 셸에서).
- [x] **완성도 갭 메우기: 멀티턴 + 멀티코퍼스 인프라** (2026-07-29, 미커밋). peer 포폴 비교(AlaGrine/worldbank 등 실제 README 확인) 결론=우리는 rigor(eval·리랭커·정직성)는 앞서나 "경험(내 데이터로 되나·멀티턴)"이 뒤짐. 둘 다 완성도의 일부라 판단.
  - **멀티턴**: `ask(question, history)`로 이전 대화 주입(`_clean_history`=user/assistant 텍스트턴만, 최근 8턴 컷). API `/api/ask`가 history 받고, 프론트=단일답변→대화 스레드(you/assistant 말풍선·New chat·Enter전송). 배관 검증(토큰0). ⚠️LLM 맥락유지 실검증은 Groq 필요.
  - **멀티코퍼스**: `chunks`에 `corpus` 컬럼 추가(`migrate_add_corpus.py`, 605행 medusa 백필). `search(q,k,corpus=)` 필터, 인제스트 corpus 태그+**해당 코퍼스만 교체**(전체 TRUNCATE 폐기), `embed_and_store.py <corpus>` 인자화. API `/api/corpora`(드롭다운용)+corpus 파라미터, 프론트 KB 셀렉터. **검증완료**(토큰0): corpus 필터·전체·빈결과·엔드포인트 다 정상.
  - **결정(2026-07-29)**: 2번째 코퍼스는 **추후 추가 예정**으로 보류(medusa 1개 유지). 이유=골드셋 없이 코퍼스만 늘리면 commodity 회귀 위험. 인프라는 완성돼 코퍼스만 붙이면 바로 살아남. UI에 "+ more coming soon" 표시.
- [x] **README 첫인상 자산: Mermaid 아키텍처 다이어그램 + 트레이스 데모 GIF** (`baaebda`~`24c9da6`, 2026-07-29, 푸시·GitHub 렌더확인). peer 포폴 대비 유일 약점=겉포장(첫 5초). 다이어그램=이미지파일 아닌 Mermaid(안 썩음), 툴라우터→2단검색/주문/escalate+ingestion·eval 서브그래프. GIF=`docs/cite-retrieval-trace.gif`(6프레임, bulk import→**Bulk Editor가 vector 최고인데 리랭커가 강등, Import Products 승격**=우리 차별점 시각화), gif_creator 녹화(워터마크off), Groq 0. ⚠️Stack 표 부정확 발견·정정: Frontend "React"→실제 **바닐라 HTML/JS**, Backend/Frontend "(in progress)"→완료(공개레포 신뢰).
- [ ] **M3 마무리 + /ask 검증**(Groq 리셋 후): secrets 로드한 셸에서 서버 띄우고 라우팅 3케이스 품질 확인(문서 인용답변/주문조회/상담원연결) + **멀티턴 맥락유지** 확인 + 답변/멀티턴 GIF. 필요시 프롬프트 튜닝.
- [ ] 이후: 라이브 배포(Fly.io/Render, 라이브 URL) + 영어 케이스스터디(before/after 수치·실패→개선) + DECISIONS.md.
- 이후: 에러분석 1회+실패유형표, 검색트레이스 UI노출, before/after 케이스스터디(영어·LinkedIn), 하이브리드+리랭커 측정개선.
  - ⚠️**즉시 고칠 라벨버그**: 범위밖 질문도 `grounded=True`로 찍힘(=top_score≥0.35일뿐, 실제론 LLM이 거부). `grounded`를 "실제 답변했나"로 재정의 필요(refusal 감지). ②의 일부.
  - 데이터포인트(임계값 튜닝용): grounded질문 top≈0.79~0.84 vs 범위밖 top≈0.44~0.46 → 0.35는 너무 낮음. eval로 최적 컷 측정.

## 인프라 재현 메모 (새 세션/재부팅 후)
- 컨테이너 꺼졌으면: `docker start shopify-rag-pg` (데이터 유지됨). 없으면 재생성(포트 5544, `CREATE EXTENSION vector`) 후 `python ingest/embed_and_store.py`(임베딩 캐시 있으면 즉시).
- 스택 확정: fastembed(bge-small 384d) · pgvector(HNSW cosine) · Docker :5544.

## 학습 메모 (사용자 = RAG·FastAPI 처음)
- teach-mode: 한 덩어리씩 설명하며 진행. 용어 전제 깔지 말 것.
- venv = 이 프로젝트 전용 파이썬 패키지 격리 상자 (전역 오염 방지).
