import pytest
import chunker
import vstore
import retrieval

CS = chunker.load_chunks()


def test_rrf_hand_computed():
    out = dict(retrieval.rrf([["a", "b"], ["b", "c"]]))
    assert round(out["a"], 5) == round(1 / 61, 5)
    assert round(out["b"], 5) == round(1 / 62 + 1 / 61, 5)
    assert round(out["c"], 5) == round(1 / 62, 5)
    assert [k for k, v in retrieval.rrf([["a", "b"], ["b", "c"]])][0] == "b"


def test_unknown_role_rejected():
    with pytest.raises(ValueError):
        retrieval.retrieve(None, CS, "anything", "intern")


class FakeCol:
    """Simulates a broken vector filter that leaks a restricted chunk."""
    def query(self, query_embeddings, n_results, where):
        return {"ids": [["syn-doc-007#01", "syn-doc-001#02"]], "distances": [[0.1, 0.2]]}


def test_code_recheck_catches_leaked_chunk(monkeypatch):
    monkeypatch.setattr(vstore, "embed", lambda texts: [[0.0] * 768])
    out = retrieval.retrieve(FakeCol(), CS, "How often are master keys rotated?", "analyst")
    ids = [r["chunk_id"] for r in out["results"]]
    assert "syn-doc-007#01" not in ids
    assert [d["chunk_id"] for d in out["filtered_out"]] == ["syn-doc-007#01"]


def test_results_never_exceed_role(monkeypatch):
    monkeypatch.setattr(vstore, "embed", lambda texts: [[0.0] * 768])
    for role in ("analyst", "manager", "ciso"):
        out = retrieval.retrieve(FakeCol(), CS, "keys rotated passwords", role)
        by_id = {c["chunk_id"]: c for c in CS}
        assert all(role in by_id[r["chunk_id"]]["roles"] for r in out["results"])
