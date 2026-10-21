"""Sovereign RAG pipeline. ALL DATA IS SYNTHETIC.
redact -> retrieve (role-filtered) -> confidence gate -> cited answer -> verify -> audit.
Detection and access decisions are code. The model only drafts the cited answer.
"""
import os
import chunker
import pii
import vstore
import retrieval
import answer
import audit
import sovereignty

# Chosen from a gap measured on 12 questions (answerable max 0.3215, unanswerable
# min 0.5579). A small sample: the eval tests it on different questions.
MAX_DISTANCE = 0.45
AUDIT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "audit_log.jsonl")


def build():
    chunks = chunker.load_chunks()
    return vstore.build_index(chunks), chunks


def analyse(col, chunks, question, role, model="qwen2.5:3b", chat=None, audit_path=None):
    path = audit_path or AUDIT_PATH
    with sovereignty.SovereigntyMonitor(interval=0.1) as mon:
        clean, pii_counts = pii.redact(question)
        ret = retrieval.retrieve(col, chunks, clean, role)
        results = ret["results"]
        best = min((r["distance"] for r in results if r["distance"] is not None), default=None)
        if not results:
            out = answer.refuse("no permitted passages retrieved", 0)
        elif best is None or best > MAX_DISTANCE:
            out = answer.refuse("retrieval confidence too low", 0,
                                ["best distance %s > %s" % (best, MAX_DISTANCE)])
        else:
            out = answer.ask(clean, results, chunks, role, model=model, chat=chat)
    sov = mon.report()
    entry = audit.append(path, "analyse", {
        "role": role, "model": model, "pii_counts": pii_counts,
        "retrieved": [r["chunk_id"] for r in results],
        "filtered_out": [d["chunk_id"] for d in ret["filtered_out"]],
        "best_distance": best, "status": out["status"],
        "cited": [c["chunk_id"] for c in out.get("citations", [])],
        "sovereignty_passed": sov["passed"], "samples": sov["samples"],
    })
    return {"redacted_query": clean, "pii_counts": pii_counts, "retrieval": ret,
            "best_distance": best, "result": out, "sovereignty": sov,
            "audit_hash": entry["hash"]}
