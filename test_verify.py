import chunker
import verify

CS = chunker.load_chunks()
Q2 = "Passwords must be rotated every 90 days."
Q1 = "All staff must use passwords of at least 14 characters."
K = "Master encryption keys are rotated every 180 days."
IDS = ["syn-doc-001#01", "syn-doc-001#02"]


def v(answer, cites, ids=IDS, role="analyst"):
    return verify.verify({"answer": answer, "citations": cites}, ids, CS, role)


def c(cid, quote):
    return {"chunk_id": cid, "quote": quote}


def has(r, text):
    return any(text in x for x in r["reasons"])


def test_valid_answer_passes():
    assert v(Q2, [c("syn-doc-001#02", Q2)]) == {"ok": True, "reasons": []}


def test_chunk_id_digits_in_answer_are_ignored():
    r = v("Rotate every 90 days [syn-doc-001#02].", [c("syn-doc-001#02", Q2)])
    assert r["ok"]


def test_wrong_number_fails():
    r = v("Passwords must be rotated every 60 days.", [c("syn-doc-001#02", Q2)])
    assert not r["ok"] and has(r, "numbers not in cited chunks: 60")


def test_number_needs_its_own_citation():
    ans = "Use 14 characters and rotate every 90 days."
    bad = v(ans, [c("syn-doc-001#02", Q2)])
    assert not bad["ok"] and has(bad, "numbers not in cited chunks: 14")
    assert v(ans, [c("syn-doc-001#02", Q2), c("syn-doc-001#01", Q1)])["ok"]


def test_altered_quote_fails():
    r = v(Q2, [c("syn-doc-001#02", Q2.replace("90", "30"))])
    assert not r["ok"] and has(r, "not verbatim")


def test_case_changed_quote_fails():
    r = v(Q2, [c("syn-doc-001#02", Q2.lower())])
    assert not r["ok"] and has(r, "not verbatim")


def test_unretrieved_chunk_fails():
    r = v(Q1, [c("syn-doc-001#01", Q1)], ids=["syn-doc-001#02"])
    assert not r["ok"] and has(r, "chunk not retrieved")


def test_role_denied_chunk_fails_even_if_retrieved():
    ids = ["syn-doc-007#01"]
    r = v("Keys rotate every 180 days.", [c("syn-doc-007#01", K)], ids=ids)
    assert not r["ok"] and has(r, "not permitted for role")
    ok = v("Keys rotate every 180 days.", [c("syn-doc-007#01", K)], ids=ids, role="ciso")
    assert ok["ok"]


def test_unknown_chunk_fails():
    r = v(Q2, [c("syn-doc-999#01", Q2)])
    assert not r["ok"] and has(r, "unknown chunk id")


def test_bad_shapes_fail():
    for bad in (None, "text", {"answer": Q2}, {"answer": Q2, "citations": []},
                {"answer": Q2, "citations": "x"}, {"answer": Q2, "citations": [5]},
                {"answer": " ", "citations": [c("syn-doc-001#02", Q2)]}):
        assert verify.verify(bad, IDS, CS, "analyst")["ok"] is False


def test_short_quote_fails():
    r = v("90 days.", [c("syn-doc-001#02", "90 days")])
    assert not r["ok"] and has(r, "too short")
