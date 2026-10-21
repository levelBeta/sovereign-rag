import json
import audit
import agent
import chunker
import vstore

CS = chunker.load_chunks()
Q2 = "Passwords must be rotated every 90 days."
GOOD = json.dumps({"answer": Q2, "citations": [{"chunk_id": "syn-doc-001#02", "quote": Q2}]})


class FakeCol:
    def __init__(self, ids, dist):
        self.ids, self.dist = ids, dist

    def query(self, query_embeddings, n_results, where):
        return {"ids": [self.ids], "distances": [[self.dist] * len(self.ids)]}


def scripted(*replies):
    it = iter(replies)

    def chat(model, messages):
        chat.calls.append(messages)
        return next(it)
    chat.calls = []
    return chat


def good_chat():
    def chat(model, messages):
        chat.calls.append(messages)
        lines = messages[1]["content"].splitlines()
        label = [x[1:x.index("]")] for x in lines if x.startswith("[P") and x.endswith(Q2)][0]
        return json.dumps({"answer": Q2, "citations": [{"passage": label, "quote": Q2}]})
    chat.calls = []
    return chat


def run(tmp_path, col, q="How often are passwords rotated?", role="analyst", chat=None):
    p = str(tmp_path / "audit_t.jsonl")
    return agent.analyse(col, CS, q, role, chat=chat, audit_path=p)


def test_low_confidence_refuses_without_model(tmp_path, monkeypatch):
    monkeypatch.setattr(vstore, "embed", lambda t: [[0.0] * 768])
    ch = scripted()
    out = run(tmp_path, FakeCol(["syn-doc-001#02"], 0.9), chat=ch)
    assert out["result"]["status"] == "refused"
    assert out["result"]["reason"] == "retrieval confidence too low"
    assert ch.calls == []


def test_confident_answer_is_returned_and_audited(tmp_path, monkeypatch):
    monkeypatch.setattr(vstore, "embed", lambda t: [[0.0] * 768])
    out = run(tmp_path, FakeCol(["syn-doc-001#02"], 0.1), chat=good_chat())
    assert out["result"]["status"] == "answered"
    v = audit.verify(str(tmp_path / "audit_t.jsonl"))
    assert v["ok"] and v["entries"] == 1


def test_pii_redacted_and_not_logged(tmp_path, monkeypatch):
    monkeypatch.setattr(vstore, "embed", lambda t: [[0.0] * 768])
    q = "My card 4111 1111 1111 1111 was used. How often are passwords rotated?"
    col = FakeCol(["syn-doc-001#02"], 0.1)
    out = run(tmp_path, col, q=q, chat=good_chat())
    assert "4111" not in out["redacted_query"]
    assert out["pii_counts"] == {"card": 1}
    log = (tmp_path / "audit_t.jsonl").read_text(encoding="utf-8")
    assert "4111" not in log and "passwords rotated" not in log


def test_leaked_restricted_chunk_is_filtered(tmp_path, monkeypatch):
    monkeypatch.setattr(vstore, "embed", lambda t: [[0.0] * 768])
    col = FakeCol(["syn-doc-007#01"], 0.1)
    out = run(tmp_path, col, chat=scripted(GOOD, GOOD))
    ids = [d["chunk_id"] for d in out["retrieval"]["filtered_out"]]
    assert ids == ["syn-doc-007#01"]
    shown = [r["chunk_id"] for r in out["retrieval"]["results"]]
    assert "syn-doc-007#01" not in shown
