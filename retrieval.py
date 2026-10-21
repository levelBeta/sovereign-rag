"""Hybrid retrieval for Sovereign RAG. ALL DATA IS SYNTHETIC.
BM25 (permitted chunks only) + Chroma vector search (role flag in the query), fused with
reciprocal rank fusion. Every fused hit is then re-checked in code against its own roles.
"""
import re
from rank_bm25 import BM25Okapi
import vstore

RRF_K = 60


def _tok(s):
    return re.findall(r"[a-z0-9]+", s.lower())


def rrf(rankings, k=RRF_K):
    scores = {}
    for ranking in rankings:
        for pos, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + pos)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def retrieve(col, chunks, query, role, top_k=5, pool=10):
    if role not in vstore.ROLES:
        raise ValueError("unknown role: " + str(role))
    by_id = {c["chunk_id"]: c for c in chunks}
    allowed = [c for c in chunks if role in c["roles"]]
    sc = BM25Okapi([_tok(c["text"]) for c in allowed]).get_scores(_tok(query))
    ranked = sorted(zip(sc, allowed), key=lambda x: (-x[0], x[1]["chunk_id"]))
    bm_rank = [c["chunk_id"] for s, c in ranked if s > 0][:pool]
    res = col.query(query_embeddings=vstore.embed([query]), n_results=pool,
                    where={"role_" + role: True})
    vec_rank = res["ids"][0]
    dist = dict(zip(res["ids"][0], res["distances"][0]))
    results, denied = [], []
    for cid, score in rrf([bm_rank, vec_rank]):
        c = by_id.get(cid)
        if c is None or role not in c["roles"]:
            denied.append({"chunk_id": cid, "reason": "role not permitted (code re-check)"})
            continue
        results.append({
            "chunk_id": cid, "text": c["text"], "rrf": round(score, 5),
            "bm25_rank": bm_rank.index(cid) + 1 if cid in bm_rank else None,
            "vector_rank": vec_rank.index(cid) + 1 if cid in vec_rank else None,
            "distance": round(dist[cid], 4) if cid in dist else None,
        })
    return {"results": results[:top_k], "filtered_out": denied}
