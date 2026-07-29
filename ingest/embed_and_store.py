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

MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384

# 코퍼스별 청크/임베딩 캐시 경로. medusa는 기존 파일(하위호환) 그대로 사용.
DEFAULT_CORPUS = "medusa"


def paths_for(corpus):
    if corpus == DEFAULT_CORPUS:
        return Path("data/chunks.json"), Path("data/embeddings.npy")
    return Path(f"data/chunks_{corpus}.json"), Path(f"data/embeddings_{corpus}.npy")


DDL = f"""
CREATE TABLE IF NOT EXISTS chunks (
    id          text PRIMARY KEY,
    text        text NOT NULL,
    title       text,
    heading     text,
    source_url  text,
    source_path text,
    corpus      text,
    embedding   vector({DIM})
);
"""


def get_embeddings(texts, emb_cache):
    if emb_cache.exists():
        arr = np.load(emb_cache)
        if arr.shape[0] == len(texts):
            print(f"    캐시 사용: {emb_cache} {arr.shape}")
            return arr
        print("    캐시 크기 불일치 -> 재계산")
    print(f"    모델 로딩: {MODEL} (처음이면 다운로드)")
    model = TextEmbedding(model_name=MODEL)
    print("    임베딩 생성 중... (CPU, 몇 분)")
    arr = np.array(list(model.embed(texts)), dtype=np.float32)
    np.save(emb_cache, arr)
    print(f"    캐시 저장: {emb_cache} {arr.shape}")
    return arr


def main():
    corpus = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CORPUS
    chunks_path, emb_cache = paths_for(corpus)
    print(f"[0] 코퍼스='{corpus}'  청크={chunks_path}")
    print("    DB 연결 확인...")
    connect().close()   # 인증/포트 문제면 여기서 즉시 실패
    print("    OK")

    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
    print(f"[1] 청크 {len(chunks)}개")

    print("[2] 임베딩")
    embs = get_embeddings([c["text"] for c in chunks], emb_cache)

    print("[3] DB 저장 중...")
    conn = connect()
    with conn.cursor() as cur:
        cur.execute(DDL)
        cur.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS corpus text;")
        # 전체 TRUNCATE 아님 — 이 코퍼스 행만 교체(다른 코퍼스 보존)
        cur.execute("DELETE FROM chunks WHERE corpus = %s;", (corpus,))
        for c, emb in zip(chunks, embs):
            cur.execute(
                "INSERT INTO chunks "
                "(id, text, title, heading, source_url, source_path, corpus, embedding) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                (c["id"], c["text"], c["title"], c["heading"],
                 c["source_url"], c["source_path"], corpus, emb),
            )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS chunks_embedding_idx "
            "ON chunks USING hnsw (embedding vector_cosine_ops);"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS chunks_corpus_idx ON chunks (corpus);")
        conn.commit()
        cur.execute("SELECT count(*) FROM chunks WHERE corpus = %s;", (corpus,))
        n = cur.fetchone()[0]
    conn.close()
    print(f"[완료] '{corpus}' {n}행 저장 + 인덱스")


if __name__ == "__main__":
    main()
