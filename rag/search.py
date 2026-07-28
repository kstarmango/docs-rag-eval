"""질문으로 관련 청크를 의미검색(semantic search)한다.

2단계 검색:
  1) bi-encoder(bge-small) 임베딩 코사인으로 후보 top-N을 빠르게 뽑고
  2) cross-encoder 리랭커로 질문+청크를 '같이 읽어' 재순위 → 상위 k 반환.

리랭킹은 `RAG_RERANK` 환경변수로 on/off (before/after 비교용). 기본 on.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.db import connect  # noqa: E402
from fastembed import TextEmbedding  # noqa: E402

MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
RERANK_DEFAULT = os.getenv("RAG_RERANK", "1") != "0"   # 0이면 리랭킹 끔(baseline)
CANDIDATES = int(os.getenv("RAG_CANDIDATES", "20"))    # 리랭커에 넘길 1차 후보 수

_model = None
_reranker = None


def _embed(query: str):
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=MODEL)
    return next(_model.embed([query]))


def _rerank(query, rows, k):
    """cross-encoder로 (질문, 청크) 쌍을 재채점하고 상위 k만."""
    global _reranker
    if _reranker is None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder
        _reranker = TextCrossEncoder(model_name=RERANK_MODEL)
    scores = list(_reranker.rerank(query, [r["text"] for r in rows]))
    for r, s in zip(rows, scores):
        r["rerank_score"] = float(s)
    rows.sort(key=lambda r: r["rerank_score"], reverse=True)
    return rows[:k]


def search(query: str, k: int = 5, rerank: bool = None):
    rerank = RERANK_DEFAULT if rerank is None else rerank
    n = max(k, CANDIDATES) if rerank else k   # 리랭크 시 후보를 넉넉히 뽑는다
    vec = _embed(query)
    conn = connect()
    with conn.cursor() as cur:
        # <=> = 코사인 거리. score = 1 - 거리 = 코사인 유사도(높을수록 가까움)
        cur.execute(
            "SELECT id, text, title, heading, source_url, "
            "       1 - (embedding <=> %s) AS score "
            "FROM chunks "
            "ORDER BY embedding <=> %s "
            "LIMIT %s",
            (vec, vec, n),
        )
        rows = cur.fetchall()
    conn.close()
    hits = [
        {"id": r[0], "text": r[1], "title": r[2], "heading": r[3],
         "source_url": r[4], "score": float(r[5])}
        for r in rows
    ]
    if rerank and hits:
        return _rerank(query, hits, k)
    return hits[:k]


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How do I create a return for a customer order?"
    print(f"질문: {q}  (rerank={RERANK_DEFAULT})\n")
    for i, r in enumerate(search(q), 1):
        rr = f" rerank={r['rerank_score']:.2f}" if "rerank_score" in r else ""
        print(f"[{i}] score={r['score']:.3f}{rr}  {r['title']} > {r['heading']}")
        print(f"    {r['source_url']}")
        print(f"    {r['text'][:160].strip()}...\n")
