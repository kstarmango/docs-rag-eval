"""Medusa user-guide 문서(.mdx)를 읽어 청크(chunk)로 쪼갠다.

각 청크 = {id, text, title, heading, source_url, source_path}
- title: `export const metadata = { title: ... }` 에서 추출 (frontmatter 아님)
- source_url: 파일 경로로 생성 (docs.medusajs.com/user-guide/<slug>)
- MDX 노이즈(import/export/JSX/{/* */}) 제거, 헤더(#,##,###) 기준 분할, 길면 크기 분할(+overlap)
"""
import hashlib
import json
import re
from pathlib import Path

import yaml

# user-guide의 Next.js app 라우트 = 상점 관리자용 how-to 문서
DOCS = Path("data/raw/medusa/www/apps/user-guide/app")
BASE_URL = "https://docs.medusajs.com/user-guide"
OUT = Path("data/chunks.json")

MAX_CHARS = 1400   # 청크 최대 크기
OVERLAP = 150      # 크기 분할 시 겹침(문맥 유지)

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HEADER = re.compile(r"^(#{1,3})\s+(.*)$")
# MDX 전용 노이즈
IMPORT = re.compile(r"^import\s.*?(?:from\s*[\"'][^\"']*[\"'])?\s*$", re.MULTILINE)
IMPORT_BLOCK = re.compile(r"^import\s*\{[^}]*\}\s*from\s*[\"'][^\"']*[\"']", re.MULTILINE | re.DOTALL)
EXPORT_META = re.compile(r"^export\s+const\s+metadata\s*=\s*\{.*?\}\s*$", re.MULTILINE | re.DOTALL)
MDX_COMMENT = re.compile(r"\{/\*.*?\*/\}", re.DOTALL)
JSX_TAG = re.compile(r"</?[A-Za-z][^>]*/?>")   # <Note>, <EllipsisHorizontal />, </Table> 등
TITLE_IN_META = re.compile(r"title:\s*[`\"']([^`\"']+)[`\"']")
MDX_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\.mdx[^)]*\)")   # [text](../x/page.mdx) -> text


def path_to_url(rel: str) -> str:
    slug = rel[:-len("/page.mdx")] if rel.endswith("/page.mdx") else rel
    slug = slug.strip("/")
    return f"{BASE_URL}/{slug}" if slug else BASE_URL


def parse_file(path: Path, rel: str):
    raw = path.read_text(encoding="utf-8", errors="ignore")

    m = FRONTMATTER.match(raw)
    fm = {}
    body = raw
    if m:
        try:
            fm = yaml.safe_load(m.group(1)) or {}
        except Exception:
            fm = {}
        body = raw[m.end():]

    # title: metadata -> frontmatter sidebar_label -> 첫 # 헤더 -> 경로
    title = None
    tm = TITLE_IN_META.search(body)
    if tm:
        title = tm.group(1).strip()
    if not title:
        title = fm.get("sidebar_label")

    # MDX 노이즈 제거
    body = EXPORT_META.sub("", body)
    body = IMPORT_BLOCK.sub("", body)
    body = IMPORT.sub("", body)
    body = MDX_COMMENT.sub("", body)
    body = IMAGE.sub("", body)
    body = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
    body = MDX_LINK.sub(r"\1", body)
    body = JSX_TAG.sub("", body)
    # `# {metadata.title}` 같은 JSX 표현식 헤더를 실제 제목으로
    body = body.replace("{metadata.title}", title or "")

    if not title:
        h = re.search(r"^#\s+(.*)$", body, re.MULTILINE)
        title = h.group(1).strip() if h else path.parent.name

    return title, path_to_url(rel), body


def split_by_headers(body: str):
    """(heading, text) 섹션 리스트로 분할."""
    sections, head, lines = [], "", []
    for line in body.splitlines():
        hm = HEADER.match(line)
        if hm:
            if lines:
                sections.append((head, "\n".join(lines).strip()))
            head = re.sub(r"<[^>]+>", "", hm.group(2)).strip()
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
    files = sorted(DOCS.rglob("page.mdx"))
    # Next.js 동적 라우트/렌더러(실 문서 아님) 제외
    files = [f for f in files if "md-content" not in f.parts and "[[" not in str(f)]
    print(f"[1] 대상 문서 {len(files)}개 (Medusa user-guide)")

    chunks = []
    for path in files:
        rel = str(path.relative_to(DOCS)).replace("\\", "/")
        title, url, body = parse_file(path, rel)
        for heading, text in split_by_headers(body):
            text = re.sub(r"\n{3,}", "\n\n", text).strip()   # MDX 제거로 생긴 빈줄 정리
            for piece in cap_size(text):
                piece = piece.strip()
                if len(piece) < 30:      # 너무 짧은 조각 버림
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
