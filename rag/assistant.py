"""통합 지원 어시스턴트 (M2+M3: 문서 RAG + 주문조회 tool-calling + 정직한 라우팅).

LLM에게 두 개의 툴을 주고 스스로 라우팅하게 한다:
  - search_help_docs(query): how-to/정책 질문 → 문서에서 근거+인용 답변
  - lookup_order(order_id): 특정 주문 질문("내 주문 어디") → 가짜 주문데이터 조회
어느 툴로도 못 답하면(주문번호 없이 계정정보 요구 등) → 지어내지 말고 상담원 연결 안내.

answer.py(문서 전용, eval에서 사용)와 별개. 이건 데모용 풀 어시스턴트.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.search import search          # noqa: E402
from rag.orders import lookup_order, find_orders_by_email  # noqa: E402

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_API_KEY = os.getenv("API_GROQ_KEY")
MAX_STEPS = 4          # tool-calling 왕복 상한 (무한루프 방지)
DOC_K = 5

SYSTEM_PROMPT = """You are the support assistant for a store running on Medusa.
You serve both store operators (how-to questions) and customers (questions about their orders).

Route every question with the tools:
- For how-to / policy / "how do I..." questions, call search_help_docs and answer ONLY from the
  returned passages, citing them inline with [n] markers. If the passages don't contain the answer,
  say you don't have that information in the documentation.
- For questions about a specific order (status, tracking, delivery, refund on an order), call
  lookup_order with the order id (or find_orders_by_email if given an email).
- Never invent order details, tracking numbers, policies, or steps. Only state what a tool returned.
- If a question needs account data you cannot retrieve (e.g. no order id given, or something no tool
  provides), do not guess — briefly say you'll connect them to a human agent.
Be concise and practical."""

TOOLS = [
    {"type": "function", "function": {
        "name": "search_help_docs",
        "description": "Search the store's help documentation for how-to and policy answers.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "The user's how-to/policy question."}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "lookup_order",
        "description": "Look up a single order by its order id. Use for status/tracking/delivery/refund of a specific order.",
        "parameters": {"type": "object", "properties": {
            "order_id": {"type": "string", "description": "The order id, e.g. '10432'."}},
            "required": ["order_id"]}}},
    {"type": "function", "function": {
        "name": "find_orders_by_email",
        "description": "List a customer's orders by their email address.",
        "parameters": {"type": "object", "properties": {
            "email": {"type": "string"}},
            "required": ["email"]}}},
]


def _client():
    if not LLM_API_KEY:
        raise RuntimeError("API_GROQ_KEY 없음. ~/.claude/secrets.env 로드한 셸에서 실행.")
    from openai import OpenAI
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def _run_docs(query, corpus=None):
    """문서검색 → LLM에 줄 번호매긴 컨텍스트 + 출처(hits) 반환."""
    hits = search(query, k=DOC_K, corpus=corpus)
    blocks = []
    for i, h in enumerate(hits, 1):
        loc = " > ".join(x for x in (h.get("title"), h.get("heading")) if x)
        blocks.append(f"[{i}] ({loc})\n{h['text'].strip()}")
    return "\n\n".join(blocks), hits


def _dispatch(name, args, corpus=None):
    if name == "search_help_docs":
        context, hits = _run_docs(args.get("query", ""), corpus=corpus)
        return context or "No relevant passages found.", hits
    if name == "lookup_order":
        return json.dumps(lookup_order(args.get("order_id", "")), ensure_ascii=False), None
    if name == "find_orders_by_email":
        return json.dumps(find_orders_by_email(args.get("email", "")), ensure_ascii=False), None
    return f"Unknown tool: {name}", None


def _clean_history(history):
    """프론트가 보낸 이전 대화에서 텍스트 턴(user/assistant)만 안전하게 추린다.
    tool_call 배관은 다시 안 넘김 — 이전 최종답변 텍스트만 맥락으로 충분."""
    out = []
    for m in history or []:
        role = (m.get("role") or "").strip()
        content = (m.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out[-8:]   # 최근 8턴만 (토큰·프롬프트 폭주 방지)


def ask(question: str, history=None, corpus=None):
    """질문(+이전 대화) → LLM 라우팅(tool-calling) → 최종 답변. dict 반환.

    history: [{"role": "user"|"assistant", "content": str}, ...] 이전 턴들.
    corpus: 문서검색을 특정 코퍼스로 한정(None=전체).
    후속질문("그 주문 취소는?", "그럼 20%는?")이 맥락을 이어가게 한다.
    """
    client = _client()
    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                *_clean_history(history),
                {"role": "user", "content": question}]
    tools_used, doc_sources = [], []

    for _ in range(MAX_STEPS):
        resp = client.chat.completions.create(
            model=LLM_MODEL, temperature=0, tools=TOOLS, tool_choice="auto",
            messages=messages)
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return {"answer": (msg.content or "").strip(),
                    "tools_used": tools_used, "doc_sources": doc_sources}
        messages.append(msg)   # tool_calls 담긴 assistant 메시지
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            tools_used.append({"tool": name, "args": args})
            content, hits = _dispatch(name, args, corpus=corpus)
            if hits:
                for i, h in enumerate(hits, 1):
                    doc_sources.append({"n": i, "url": h.get("source_url"),
                                        "title": h.get("title"), "heading": h.get("heading")})
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "name": name, "content": content})

    return {"answer": "I'll connect you to a human agent for this one.",
            "tools_used": tools_used, "doc_sources": doc_sources,
            "note": "max steps reached"}


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Where is my order #10432?"
    print(f"질문: {q}\n")
    r = ask(q)
    print(r["answer"])
    print(f"\n--- tools_used: {[t['tool'] for t in r['tools_used']]} ---")
    for s in r.get("doc_sources", []):
        if s["url"]:
            print(f"[{s['n']}] {s['url']}")
