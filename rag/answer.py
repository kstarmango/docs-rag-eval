"""검색된 청크 + 질문 -> LLM -> 근거인용 답변 (RAG의 '생성' 단계).

핵심 설계 3가지:
1. 인용: 답변에 [1][2] 마커 -> 하단에 출처 URL 매핑.
2. 모름 처리: 관련 청크가 없거나(빈 검색) 유사도가 낮으면
   LLM에 넘기지 않고 곧장 "모른다"로 응답 (환각 방지).
3. model-agnostic: LLM은 OpenAI 호환 엔드포인트면 무엇이든.
   지금은 Groq 무료티어. base_url/model만 바꾸면 교체 가능.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.search import search  # noqa: E402

# --- LLM 설정 (model-agnostic) ---------------------------------------------
# Groq = OpenAI 호환. openai SDK로 base_url만 바꿔 붙인다.
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_API_KEY = os.getenv("API_GROQ_KEY")

# --- 검색/모름 처리 임계값 --------------------------------------------------
TOP_K = 5           # LLM에 넘길 청크 수
MIN_SCORE = 0.35    # 최상위 청크 유사도가 이 밑이면 "관련 문서 없음"으로 간주

REFUSAL = "I don't have information about that in the documentation."

SYSTEM_PROMPT = f"""You are a support assistant for a store running on Medusa (an e-commerce platform).
You help store operators use the Medusa Admin. Answer ONLY using the numbered context passages provided by the user.

Rules:
- Base every claim on the passages. Cite them inline with [n] markers matching the passage numbers.
- If the passages do not contain the answer, reply exactly: "{REFUSAL}"
- Do not use outside knowledge. Do not guess. Be concise and practical.
"""


def _client():
    if not LLM_API_KEY:
        raise RuntimeError(
            "API_GROQ_KEY 가 환경변수에 없습니다. "
            "~/.claude/secrets.env 를 로드한 셸에서 실행하세요."
        )
    from openai import OpenAI
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)


def _build_context(hits):
    """검색된 청크들을 번호 매긴 컨텍스트 블록으로 조립."""
    blocks = []
    for i, h in enumerate(hits, 1):
        loc = " > ".join(x for x in (h.get("title"), h.get("heading")) if x)
        blocks.append(f"[{i}] ({loc})\n{h['text'].strip()}")
    return "\n\n".join(blocks)


def answer(question: str, k: int = TOP_K):
    """질문 -> 검색 -> (관련 있으면) LLM 답변. dict 반환."""
    hits = search(question, k=k)

    # 모름 처리: 검색 결과가 없거나 최상위 유사도가 임계 미만이면 LLM 호출 안 함.
    top = hits[0]["score"] if hits else 0.0
    if not hits or top < MIN_SCORE:
        return {
            "answer": REFUSAL,
            "sources": [],
            "hits": hits,
            "grounded": False,      # 검색 임계값 통과 여부
            "answered": False,      # 실제로 답했는지 (거부 아님)
            "status": "refused_low_score",
            "top_score": top,
        }

    context = _build_context(hits)
    user_msg = f"Context passages:\n\n{context}\n\nQuestion: {question}"

    resp = _client().chat.completions.create(
        model=LLM_MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
    )
    text = resp.choices[0].message.content.strip()

    # 검색은 통과했지만 LLM이 컨텍스트에 답이 없다고 판단해 거부한 경우 구분.
    # (grounded=검색통과 ≠ answered=실제답변. 아까 라벨버그 원인)
    refused = text.rstrip(".").strip() == REFUSAL.rstrip(".").strip()

    # 출처: 검색된 청크의 URL을 번호와 함께 (LLM이 인용한 [n]과 매칭)
    sources = [
        {"n": i, "url": h.get("source_url"), "title": h.get("title"),
         "heading": h.get("heading"), "score": h["score"]}
        for i, h in enumerate(hits, 1)
    ]
    return {
        "answer": text,
        "sources": sources,
        "hits": hits,
        "grounded": True,
        "answered": not refused,
        "status": "refused_by_llm" if refused else "answered",
        "top_score": top,
    }


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "How do I create a return for a customer order?"
    print(f"질문: {q}\n")
    result = answer(q)
    print(result["answer"])
    print(f"\n--- status={result['status']} grounded={result['grounded']} "
          f"answered={result['answered']} (top_score={result['top_score']:.3f}) ---")
    for s in result["sources"]:
        if s["url"]:
            print(f"[{s['n']}] {s['url']}  (score {s['score']:.2f})")
