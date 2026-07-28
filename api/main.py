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


@app.get("/api/search")
def api_search(q: str, k: int = 5):
    """검색 트레이스: 어떤 청크가 어떤 점수로 뽑혔나(벡터+리랭크)."""
    hits = search(q, k=k)
    return {
        "query": q,
        "reranked": RERANK_DEFAULT,
        "results": [
            {
                "rank": i,
                "score": round(h["score"], 4),               # bi-encoder 코사인
                "rerank_score": round(h["rerank_score"], 4) if "rerank_score" in h else None,
                "title": h["title"],
                "heading": h["heading"],
                "source_url": h["source_url"],
                "text": h["text"],
            }
            for i, h in enumerate(hits, 1)
        ],
    }


@app.get("/api/order/{order_id}")
def api_order(order_id: str):
    return lookup_order(order_id)


class AskBody(BaseModel):
    question: str


@app.post("/api/ask")
def api_ask(body: AskBody):
    """통합 어시스턴트(문서 RAG + 주문조회 라우팅). Groq 키 필요."""
    try:
        from rag.assistant import ask
        return ask(body.question)
    except Exception as e:      # Groq 미설정/rate-limit 등 → 프론트에 친절히
        return {"answer": None, "error": f"{type(e).__name__}: {e}",
                "hint": "LLM(Groq) 키 미로드거나 일일 토큰 소진. 검색/주문 탭은 정상 동작."}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/static", StaticFiles(directory=STATIC), name="static")
