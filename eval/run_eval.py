"""RAG 파이프라인 eval 하네스.

두 축을 따로 측정한다:
  1) 검색(retrieval) 품질 — Recall@1/3/5, MRR. LLM 불필요(로컬 검색만) → 빠르고 무료, 헤드라인 수치.
  2) 정직성(no-answer) — 범위밖 질문을 실제로 거부하나 + 정상질문을 잘못 거부(over-refusal)하나. 전체 파이프라인(LLM 포함) 통과.

사용:
  (secrets.env 인라인 로드 후)
  venv\\Scripts\\python.exe eval\\run_eval.py
결과 스코어카드 출력 + eval/results.json 저장(케이스스터디용).
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.search import search, RERANK_DEFAULT    # noqa: E402
from rag.answer import answer    # noqa: E402

MODE = "reranked" if RERANK_DEFAULT else "baseline"
GOLD = Path("eval/gold_set.json")
OUT = Path(f"eval/results_{MODE}.json")   # RAG_RERANK=0 이면 baseline, 아니면 reranked
KS = (1, 3, 5)
TOP_K = 5


def rank_of(correct_doc, hits):
    """correct_doc(source_url)가 검색결과 top-k 몇 위인가. 없으면 None."""
    for i, h in enumerate(hits, 1):
        if h.get("source_url") == correct_doc:
            return i
    return None


def retrieval_eval(in_scope):
    """검색만으로 Recall@k, MRR 계산 (LLM 불필요)."""
    rows, hit_counts, rr_sum = [], {k: 0 for k in KS}, 0.0
    for q in in_scope:
        hits = search(q["question"], k=TOP_K)
        r = rank_of(q["correct_doc"], hits)
        for k in KS:
            if r is not None and r <= k:
                hit_counts[k] += 1
        rr_sum += (1.0 / r) if r else 0.0
        rows.append({
            "id": q["id"], "question": q["question"],
            "correct_doc": q["correct_doc"], "rank": r,
            "top1": hits[0]["source_url"] if hits else None,
            "top1_score": round(hits[0]["score"], 3) if hits else None,
        })
    n = len(in_scope)
    recall = {k: hit_counts[k] / n for k in KS}
    mrr = rr_sum / n
    return recall, mrr, rows


def honesty_eval(questions):
    """전체 파이프라인(LLM 포함)으로 거부/답변 판정. 범위밖 거부율 + 정상 오거부율."""
    rows = []
    for q in questions:
        res = _answer_with_retry(q["question"])
        rows.append({
            "id": q["id"], "question": q["question"],
            "out_of_scope": q["correct_doc"] is None,
            "answered": res["answered"], "status": res["status"],
            "top_score": round(res["top_score"], 3),
        })
        time.sleep(2)   # Groq 무료티어 rate limit 여유
    return rows


def _answer_with_retry(question, tries=2):
    for t in range(tries):
        try:
            return answer(question)
        except Exception as e:      # rate limit 등 → 잠깐 쉬고 1회 재시도
            if t == tries - 1:
                raise
            print(f"    (재시도: {type(e).__name__}) 20s 대기...")
            time.sleep(20)


def main():
    data = json.loads(GOLD.read_text(encoding="utf-8"))
    questions = data["questions"]
    in_scope = [q for q in questions if q["correct_doc"] is not None]
    out_scope = [q for q in questions if q["correct_doc"] is None]
    print(f"골드셋: 정상 {len(in_scope)} + 범위밖 {len(out_scope)} = {len(questions)}  [모드: {MODE}]\n")

    print("[1] 검색 품질 (retrieval) 측정 중...")
    recall, mrr, ret_rows = retrieval_eval(in_scope)

    # 정직성 eval은 LLM 호출(유료/rate-limit) → EVAL_SKIP_LLM=1 이면 검색 지표만.
    if os.getenv("EVAL_SKIP_LLM") == "1":
        print("[2] 정직성 eval 건너뜀 (EVAL_SKIP_LLM=1, 검색 지표만)")
        print("\n검색 품질 [{}]".format(MODE))
        for k in KS:
            print(f"    Recall@{k}: {recall[k]*100:5.1f}%   ({round(recall[k]*len(in_scope))}/{len(in_scope)})")
        print(f"    MRR      : {mrr:.3f}")
        ret_fail = [r for r in ret_rows if r["rank"] is None]
        if ret_fail:
            print(f"검색 실패 {len(ret_fail)}건: " + ", ".join(r["id"] for r in ret_fail))
        OUT.write_text(json.dumps({
            "mode": MODE, "recall": recall, "mrr": mrr,
            "honesty": None, "retrieval_rows": ret_rows,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n결과 저장: {OUT}")
        return

    print("[2] 정직성 (no-answer) 측정 중... (LLM 호출, 조금 걸림)")
    hon_rows = honesty_eval(questions)

    # --- 정직성 집계 ---
    oos = [r for r in hon_rows if r["out_of_scope"]]
    ins = [r for r in hon_rows if not r["out_of_scope"]]
    oos_refused = sum(1 for r in oos if not r["answered"])
    ins_answered = sum(1 for r in ins if r["answered"])
    refusal_acc = oos_refused / len(oos) if oos else 0.0
    over_refusal = 1 - (ins_answered / len(ins)) if ins else 0.0

    # --- 스코어카드 ---
    print("\n" + "=" * 52)
    print("  SCORECARD")
    print("=" * 52)
    print("  검색 품질 (정상 질문 {}개)".format(len(in_scope)))
    for k in KS:
        print(f"    Recall@{k}: {recall[k]*100:5.1f}%   ({round(recall[k]*len(in_scope))}/{len(in_scope)})")
    print(f"    MRR      : {mrr:.3f}")
    print("  정직성")
    print(f"    범위밖 거부 정확도 : {refusal_acc*100:5.1f}%   ({oos_refused}/{len(oos)})")
    print(f"    정상질문 오거부율  : {over_refusal*100:5.1f}%   (낮을수록 좋음)")
    print("=" * 52)

    # --- 실패 케이스 (에러분석 재료) ---
    ret_fail = [r for r in ret_rows if r["rank"] is None]
    if ret_fail:
        print(f"\n검색 실패 (정답 문서가 top-{TOP_K}에 없음) {len(ret_fail)}건:")
        for r in ret_fail:
            print(f"  [{r['id']}] {r['question']}")
            print(f"        정답: {r['correct_doc']}")
            print(f"        top1: {r['top1']} ({r['top1_score']})")
    oos_leak = [r for r in oos if r["answered"]]
    if oos_leak:
        print(f"\n범위밖인데 답해버린 케이스 {len(oos_leak)}건:")
        for r in oos_leak:
            print(f"  [{r['id']}] {r['question']}  (top_score={r['top_score']})")
    ins_over = [r for r in ins if not r["answered"]]
    if ins_over:
        print(f"\n정상질문인데 거부한 케이스 {len(ins_over)}건:")
        for r in ins_over:
            print(f"  [{r['id']}] {r['question']}  (top_score={r['top_score']})")

    OUT.write_text(json.dumps({
        "recall": recall, "mrr": mrr,
        "refusal_accuracy": refusal_acc, "over_refusal": over_refusal,
        "retrieval_rows": ret_rows, "honesty_rows": hon_rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n결과 저장: {OUT}")


if __name__ == "__main__":
    main()
