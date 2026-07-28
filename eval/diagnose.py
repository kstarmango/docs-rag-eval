"""검색 실패 케이스 진단: 어떤 청크가 왜 이겼나 + 정답 문서의 관련 청크는 어디 있나.

원인 구분:
- 정답 문서 청크가 top에 있는데 LLM이 거부 → 청크 내용/세밀도 문제
- 정답 청크 점수 자체가 낮음 → 임베딩이 이 질문-청크를 안 가깝게 봄
- 엉뚱한 문서가 더 높음 → 리랭킹/하이브리드 필요(단어 충돌 등)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.search import _embed  # noqa: E402
from rag.db import connect     # noqa: E402


def top_hits(query, k=8):
    vec = _embed(query)
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT source_url, heading, 1-(embedding <=> %s) AS score, left(text, 90) "
            "FROM chunks ORDER BY embedding <=> %s LIMIT %s", (vec, vec, k))
        rows = cur.fetchall()
    conn.close()
    return rows


def best_in_doc(query, doc_url, k=3):
    """정답 문서 안에서 이 질문과 가장 가까운 청크 top-k (전체 순위 무시하고)."""
    vec = _embed(query)
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT heading, 1-(embedding <=> %s) AS score, left(text, 90) "
            "FROM chunks WHERE source_url = %s ORDER BY embedding <=> %s LIMIT %s",
            (vec, doc_url, vec, k))
        rows = cur.fetchall()
    conn.close()
    return rows


CASES = [
    ("q11", "A customer wants to order over the phone. How do I create an order for them manually?",
     "https://docs.medusajs.com/user-guide/orders/draft-orders/create"),
    ("q16", "I have hundreds of products in a spreadsheet. How do I bulk import them?",
     "https://docs.medusajs.com/user-guide/products/import"),
    ("q28", "How do I manually add a new customer to my store?",
     "https://docs.medusajs.com/user-guide/customers/manage"),
]

for qid, q, correct in CASES:
    print("\n" + "=" * 90)
    print(f"[{qid}] {q}")
    print(f"정답 문서: {correct}")
    print("-" * 90)
    print("검색 top-8:")
    for i, (url, head, score, snip) in enumerate(top_hits(q), 1):
        mark = "  <== 정답문서" if url == correct else ""
        short = url.replace("https://docs.medusajs.com/user-guide/", "")
        print(f"  {i}. {score:.3f}  {short} > {head}{mark}")
    print("정답 문서 내부에서 가장 가까운 청크:")
    for head, score, snip in best_in_doc(q, correct):
        print(f"     {score:.3f}  > {head}")
        print(f"            {snip.strip()}...")
