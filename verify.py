"""Citation verifier for Sovereign RAG. ALL DATA IS SYNTHETIC.
Deterministic checks on the model's cited answer. The model decides nothing: every
citation must be retrieved, permitted for the role and a verbatim quote, and every
number in the answer must appear in the cited chunks. It cannot check reasoning.
"""
import re

NUM = re.compile(r"\d+(?:\.\d+)?")
CID = re.compile(r"syn-doc-\d{3}#\d{2}")
MIN_QUOTE = 10


def numbers(text):
    return set(NUM.findall(CID.sub(" ", text)))


def verify(parsed, retrieved_ids, chunks, role):
    if not isinstance(parsed, dict):
        return {"ok": False, "reasons": ["output is not a JSON object"]}
    reasons = []
    answer = parsed.get("answer")
    cites = parsed.get("citations")
    if not isinstance(answer, str) or not answer.strip():
        reasons.append("empty or missing answer")
    if not isinstance(cites, list) or not cites:
        reasons.append("no citations")
        return {"ok": False, "reasons": reasons}
    by_id = {c["chunk_id"]: c for c in chunks}
    cited = ""
    for cit in cites:
        cid = cit.get("chunk_id") if isinstance(cit, dict) else None
        quote = cit.get("quote") if isinstance(cit, dict) else None
        c = by_id.get(cid) if isinstance(cid, str) else None
        if c is None:
            reasons.append("unknown chunk id: %s" % cid)
            continue
        bad = False
        if cid not in retrieved_ids:
            reasons.append("chunk not retrieved: %s" % cid)
            bad = True
        if role not in c["roles"]:
            reasons.append("chunk not permitted for role: %s" % cid)
            bad = True
        if bad:
            continue
        if not isinstance(quote, str) or len(quote.strip()) < MIN_QUOTE:
            reasons.append("quote missing or too short: %s" % cid)
        elif quote not in c["text"]:
            reasons.append("quote not verbatim in %s" % cid)
        else:
            cited += " " + c["text"]
    if isinstance(answer, str):
        extra = numbers(answer) - numbers(cited)
        if extra:
            reasons.append("numbers not in cited chunks: " + ", ".join(sorted(extra)))
    return {"ok": not reasons, "reasons": reasons}
