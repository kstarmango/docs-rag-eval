"""질문으로 관련 청크를 의미검색(semantic search)한다.

질문을 (청크와 같은 모델로) 임베딩 -> pgvector 코사인 유사도 top-k.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.db import connect  # noqa: E402
from fastembed import TextEmbedding  # noqa: E402

MODEL = "BAAI/bge-small-en-v1.5"
_model = None


def _embed(query: str):
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=MODEL)
    return next(_model.embed([query]))


def search(query: str, k: int = 5):
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
            (vec, vec, k),
        )
        rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "text": r[1], "title": r[2], "heading": r[3],
         "source_url": r[4], "score": float(r[5])}
        for r in rows
    ]


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How do I create my first workflow?"
    print(f"질문: {q}\n")
    for i, r in enumerate(search(q), 1):
        print(f"[{i}] score={r['score']:.3f}  {r['title']} > {r['heading']}")
        print(f"    {r['source_url']}")
        print(f"    {r['text'][:160].strip()}...\n")
