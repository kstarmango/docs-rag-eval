"""기존 chunks 테이블에 corpus 차원을 추가한다 (멀티 코퍼스 지원).

- corpus 컬럼(text) 추가 (없으면)
- 기존 행(코퍼스 미지정) → 'medusa' 백필
- corpus별 필터 검색 속도용 인덱스

멱등: 여러 번 돌려도 안전. Docker(pgvector) 떠 있어야 함.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.db import connect  # noqa: E402

DEFAULT_CORPUS = "medusa"


def main():
    conn = connect()
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS corpus text;")
        cur.execute("UPDATE chunks SET corpus = %s WHERE corpus IS NULL;", (DEFAULT_CORPUS,))
        backfilled = cur.rowcount
        cur.execute("CREATE INDEX IF NOT EXISTS chunks_corpus_idx ON chunks (corpus);")
        conn.commit()
        cur.execute("SELECT corpus, count(*) FROM chunks GROUP BY corpus ORDER BY corpus;")
        rows = cur.fetchall()
    conn.close()
    print(f"[완료] corpus 컬럼 확보, {backfilled}행 '{DEFAULT_CORPUS}' 백필")
    for corpus, n in rows:
        print(f"    {corpus}: {n}행")


if __name__ == "__main__":
    main()
