"""Chunker for Sovereign RAG. ALL DATA IS SYNTHETIC.
One chunk per non-empty body line. Chunk ID is doc_id + '#' + the 2-digit position of
the line among the body's non-empty lines, so IDs are stable while lines do not move.
"""
from pathlib import Path

CLASSES = {"public", "internal", "restricted"}
ROLES = {"analyst", "manager", "ciso"}
REQUIRED = ("doc_id", "title", "classification", "roles")


def parse_document(text):
    lines = [ln.rstrip() for ln in text.splitlines()]
    if "---" not in lines:
        raise ValueError("missing --- separator")
    sep = lines.index("---")
    meta = {}
    for ln in lines[:sep]:
        key, colon, val = ln.partition(":")
        if not colon:
            raise ValueError("bad header line: " + ln)
        meta[key.strip()] = val.strip()
    for k in REQUIRED:
        if not meta.get(k):
            raise ValueError("missing header field: " + k)
    if meta["classification"] not in CLASSES:
        raise ValueError("unknown classification: " + meta["classification"])
    roles = [r.strip() for r in meta["roles"].split(",") if r.strip()]
    if not roles or any(r not in ROLES for r in roles):
        raise ValueError("bad roles: " + meta["roles"])
    body = [ln.strip() for ln in lines[sep + 1:] if ln.strip()]
    return [
        {
            "chunk_id": "%s#%02d" % (meta["doc_id"], n),
            "doc_id": meta["doc_id"],
            "title": meta["title"],
            "classification": meta["classification"],
            "roles": roles,
            "text": line,
        }
        for n, line in enumerate(body, start=1)
    ]


def load_chunks(corpus_dir=None):
    folder = Path(corpus_dir) if corpus_dir else Path(__file__).parent / "corpus"
    chunks, seen = [], set()
    for path in sorted(folder.glob("*.md")):
        for c in parse_document(path.read_text(encoding="utf-8")):
            if c["chunk_id"] in seen:
                raise ValueError("duplicate chunk id: " + c["chunk_id"])
            seen.add(c["chunk_id"])
            chunks.append(c)
    return chunks
