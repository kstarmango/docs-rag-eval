"""주문 조회 툴 (M2: 실데이터 슬라이스).

문서로는 답 못 하는 계정/주문별 질문("내 주문 #10432 어디?")을 위해
가짜 주문 데이터에서 조회한다. 실서비스에선 이 함수가 상점 주문 API/DB를 친다.
LLM tool-calling으로 노출됨 (rag/assistant.py).
"""
import json
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "mock_orders.json"
_orders = None


def _load():
    global _orders
    if _orders is None:
        _orders = json.loads(_DATA.read_text(encoding="utf-8"))
    return _orders


def lookup_order(order_id: str):
    """주문번호로 단건 조회. 없으면 {'error': ...}."""
    oid = str(order_id).strip().lstrip("#")
    for o in _load():
        if o["order_id"] == oid:
            return o
    return {"error": f"No order found with id {oid}."}


def find_orders_by_email(email: str):
    """이메일로 그 고객의 주문 목록(요약). 없으면 빈 리스트."""
    e = str(email).strip().lower()
    return [
        {"order_id": o["order_id"], "status": o["status"],
         "placed_at": o["placed_at"], "total": o["total"]}
        for o in _load() if o["customer_email"].lower() == e
    ]


if __name__ == "__main__":
    import sys
    arg = " ".join(sys.argv[1:]) or "10432"
    if "@" in arg:
        print(json.dumps(find_orders_by_email(arg), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(lookup_order(arg), indent=2, ensure_ascii=False))
