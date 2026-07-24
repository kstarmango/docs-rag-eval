"""n8n 문서(.md)를 읽어 청크(chunk)로 쪼갠다.

각 청크 = {id, text, title, heading, source_url, source_path}
- frontmatter(YAML)에서 공개 URL 추출 -> 인용 출처로 사용
- 헤더(#, ##, ###) 기준 의미 단위 분할, 너무 길면 크기 기준 추가 분할(+overlap)
"""
import hashlib
import json
import re
from pathlib import Path

import yaml

DOCS = Path("data/raw/n8n-docs/docs")
INCLUDE = ["get-started", "build", "connect", "deploy",
           "administer", "hosting", "privacy-and-security"]
OUT = Path("data/chunks.json")

MAX_CHARS = 1400   # 청크 최대 크기
OVERLAP = 150      # 크기 분할 시 겹침(문맥 유지)

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HEADER = re.compile(r"^(#{1,3})\s+(.*)$")


def parse_file(path: Path):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    meta, body = {}, raw
    m = FRONTMATTER.match(raw)
    if m:
        try:
            meta = yaml.safe_load(m.group(1)) or {}
        except Exception:
            meta = {}
        body = raw[m.end():]
    body = IMAGE.sub("", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)

    url = meta.get("url")
    title = meta.get("title") or meta.get("nodeTitle")
    if not title:
        h = re.search(r"^#\s+(.*)$", body, re.MULTILINE)
        title = h.group(1).strip() if h else path.stem
    return title, url, body


def split_by_headers(body: str):
    """(heading, text) 섹션 리스트로 분할."""
    sections, head, lines = [], "", []
    for line in body.splitlines():
        hm = HEADER.match(line)
        if hm:
            if lines:
                sections.append((head, "\n".join(lines).strip()))
            head = re.sub(r"<[^>]+>", "", hm.group(2)).strip()  # HTML 앵커 제거
            lines = []
        else:
            lines.append(line)
    if lines:
        sections.append((head, "\n".join(lines).strip()))
    return [(h, t) for h, t in sections if t]


def cap_size(text: str):
    """MAX_CHARS 넘으면 overlap 두고 여러 조각으로."""
    if len(text) <= MAX_CHARS:
        return [text]
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + MAX_CHARS])
        start += MAX_CHARS - OVERLAP
    return out


def main():
    files = []
    for d in INCLUDE:
        files += sorted((DOCS / d).rglob("*.md"))
    print(f"[1] 대상 문서 {len(files)}개 ({', '.join(INCLUDE)})")

    chunks = []
    for path in files:
        title, url, body = parse_file(path)
        rel = str(path.relative_to(DOCS)).replace("\\", "/")
        for heading, text in split_by_headers(body):
            for piece in cap_size(text):
                piece = piece.strip()
                if len(piece) < 30:      # 너무 짧은 조각(제목만 등) 버림
                    continue
                cid = hashlib.md5((rel + heading + piece[:60]).encode()).hexdigest()[:12]
                chunks.append({
                    "id": cid,
                    "text": piece,
                    "title": title,
                    "heading": heading,
                    "source_url": url,
                    "source_path": rel,
                })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    lens = [len(c["text"]) for c in chunks]
    print(f"[완료] 청크 {len(chunks)}개 → {OUT}")
    print(f"    평균 길이 {sum(lens) // len(lens)}자, 최대 {max(lens)}자")
    c = chunks[len(chunks) // 2]
    print("\n=== 샘플 청크 (중간 것) ===")
    print(f"title    : {c['title']}")
    print(f"heading  : {c['heading']}")
    print(f"source   : {c['source_url']}")
    print(f"text     : {c['text'][:280]}...")


if __name__ == "__main__":
    main()
