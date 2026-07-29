"""CITE 데모 API (FastAPI).

엔드포인트:
  GET  /api/search?q=&k=   검색 트레이스(청크+벡터점수+리랭크점수). LLM 불필요.
  GET  /api/order/{id}     주문 조회. LLM 불필요.
  POST /api/ask            통합 어시스턴트(문서/주문 라우팅). LLM(Groq) 필요.
  GET  /                   데모 프론트(정적 HTML).
"""
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.search import search, RERANK_DEFAULT   # noqa: E402
from rag.orders import lookup_order              # noqa: E402

app = FastAPI(title="CITE — grounded, evaluated RAG assistant")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

STATIC = Path(__file__).resolve().parent / "static"


# 코퍼스 사람이 읽을 라벨(없으면 id 그대로). 새 코퍼스 추가 시 여기 한 줄.
CORPUS_LABELS = {"medusa": "Medusa store docs"}


@app.get("/api/corpora")
def api_corpora():
    """색인된 코퍼스 목록(드롭다운용). DB에서 실제 존재하는 것만."""
    from rag.db import connect
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("SELECT corpus, count(*) FROM chunks GROUP BY corpus ORDER BY corpus;")
        rows = cur.fetchall()
    conn.close()
    return {"corpora": [
        {"id": c, "label": CORPUS_LABELS.get(c, c), "chunks": n}
        for c, n in rows if c
    ]}


@app.get("/api/search")
def api_search(q: str, k: int = 5, corpus: str = None):
    """검색 트레이스: 어떤 청크가 어떤 점수로 뽑혔나(벡터+리랭크)."""
    hits = search(q, k=k, corpus=corpus)
    return {
        "query": q,
        "corpus": corpus,
        "reranked": RERANK_DEFAULT,
        "results": [
            {
                "rank": i,
                "score": round(h["score"], 4),               # bi-encoder 코사인
                "rerank_score": round(h["rerank_score"], 4) if "rerank_score" in h else None,
                "title": h["title"],
                "heading": h["heading"],
                "source_url": h["source_url"],
                "corpus": h.get("corpus"),
                "text": h["text"],
            }
            for i, h in enumerate(hits, 1)
        ],
    }


@app.get("/api/order/{order_id}")
def api_order(order_id: str):
    return lookup_order(order_id)


class Turn(BaseModel):
    role: str
    content: str


class AskBody(BaseModel):
    question: str
    history: list[Turn] = []   # 이전 대화(멀티턴). 프론트가 누적해서 보냄.
    corpus: str | None = None  # 문서검색 한정 코퍼스(None=전체)


@app.post("/api/ask")
def api_ask(body: AskBody):
    """통합 어시스턴트(문서 RAG + 주문조회 라우팅, 멀티턴). Groq 키 필요."""
    try:
        from rag.assistant import ask
        return ask(body.question, history=[t.model_dump() for t in body.history],
                   corpus=body.corpus)
    except Exception as e:      # Groq 미설정/rate-limit 등 → 프론트에 친절히
        return {"answer": None, "error": f"{type(e).__name__}: {e}",
                "hint": "LLM(Groq) 키 미로드거나 일일 토큰 소진. 검색/주문 탭은 정상 동작."}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
