"""청크를 임베딩(벡터)해서 pgvector 테이블에 저장한다.

- DB 연결을 먼저 확인(느린 임베딩 전에 빨리 실패)
- 임베딩은 디스크 캐시(data/embeddings.npy) -> 재실행 시 재계산 안 함
- 검색 속도용 HNSW(코사인) 인덱스 생성
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.db import connect  # noqa: E402
from fastembed import TextEmbedding  # noqa: E402

CHUNKS = Path("data/chunks.json")
EMB_CACHE = Path("data/embeddings.npy")
MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384

DDL = f"""
CREATE TABLE IF NOT EXISTS chunks (
    id          text PRIMARY KEY,
    text        text NOT NULL,
    title       text,
    heading     text,
    source_url  text,
    source_path text,
    embedding   vector({DIM})
);
"""


def get_embeddings(texts):
    if EMB_CACHE.exists():
        arr = np.load(EMB_CACHE)
        if arr.shape[0] == len(texts):
            print(f"    캐시 사용: {EMB_CACHE} {arr.shape}")
            return arr
        print("    캐시 크기 불일치 -> 재계산")
    print(f"    모델 로딩: {MODEL} (처음이면 다운로드)")
    model = TextEmbedding(model_name=MODEL)
    print("    임베딩 생성 중... (CPU, 몇 분)")
    arr = np.array(list(model.embed(texts)), dtype=np.float32)
    np.save(EMB_CACHE, arr)
    print(f"    캐시 저장: {EMB_CACHE} {arr.shape}")
    return arr


def main():
    print("[0] DB 연결 확인...")
    connect().close()   # 인증/포트 문제면 여기서 즉시 실패
    print("    OK")

    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    print(f"[1] 청크 {len(chunks)}개")

    print("[2] 임베딩")
    embs = get_embeddings([c["text"] for c in chunks])

    print("[3] DB 저장 중...")
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(DDL)
        cur.execute("TRUNCATE chunks;")
        for c, emb in zip(chunks, embs):
            cur.execute(
                "INSERT INTO chunks "
                "(id, text, title, heading, source_url, source_path, embedding) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (c["id"], c["text"], c["title"], c["heading"],
                 c["source_url"], c["source_path"], emb),
            )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS chunks_embedding_idx "
            "ON chunks USING hnsw (embedding vector_cosine_ops);"
        )
        conn.commit()
        cur.execute("SELECT count(*) FROM chunks;")
        n = cur.fetchone()[0]
    conn.close()
    print(f"[완료] chunks {n}행 저장 + HNSW 코사인 인덱스")


if __name__ == "__main__":
    main()
