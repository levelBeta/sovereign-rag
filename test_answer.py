import json
import chunker
import answer

CS = chunker.load_chunks()
Q2 = "Passwords must be rotated every 90 days."
K = "Master encryption keys are rotated every 180 days."
RES = [{"chunk_id": "syn-doc-001#02", "text": Q2}]
RESK = [{"chunk_id": "syn-doc-007#01", "text": K}]


def reply(ans, cid, quote):
    return json.dumps({"answer": ans, "citations": [{"passage": cid, "quote": quote}]})


GOOD = reply(Q2, "P1", Q2)
BAD = reply("Rotate every 60 days.", "P1", Q2)


def scripted(*replies):
    it = iter(replies)

    def chat(model, messages):
        chat.calls.append(messages)
        return next(it)
    chat.calls = []
    return chat


def ask(chat, results=RES, role="analyst"):
    return answer.ask("How often?", results, CS, role, chat=chat)


def test_first_try_answers():
    ch = scripted(GOOD)
    r = ask(ch)
    assert r["status"] == "answered" and r["attempts"] == 1 and len(ch.calls) == 1


def test_retry_tells_model_why_then_answers():
    ch = scripted(BAD, GOOD)
    r = ask(ch)
    assert r["status"] == "answered" and r["attempts"] == 2
    assert "numbers not in cited chunks: 60" in ch.calls[1][-1]["content"]


def test_two_failures_refuse_and_hide_answer():
    r = ask(scripted(BAD, BAD))
    assert r["status"] == "refused" and r["attempts"] == 2 and "answer" not in r
    assert any("60" in d for d in r["details"])


def test_non_json_refuses():
    r = ask(scripted("not json", "still not json"))
    assert r["status"] == "refused" and r["details"] == ["output is not valid JSON"]


def test_model_declining_is_a_refusal_without_retry():
    ch = scripted(json.dumps({"answer": "", "citations": []}))
    r = ask(ch)
    assert r["status"] == "refused" and r["attempts"] == 1 and len(ch.calls) == 1


def test_no_passages_never_calls_model():
    ch = scripted()
    r = ask(ch, results=[])
    assert r["status"] == "refused" and r["attempts"] == 0 and ch.calls == []


def test_role_denied_citation_refused():
    bad = reply("Keys rotate every 180 days.", "P1", K)
    r = ask(scripted(bad, bad), results=RESK)
    assert r["status"] == "refused" and any("not permitted" in d for d in r["details"])


def test_prompt_marks_passages_as_untrusted_data():
    ch = scripted(GOOD)
    ask(ch)
    assert "untrusted" in ch.calls[0][0]["content"]
    assert "[P1] " + Q2 in ch.calls[0][1]["content"]


def test_unknown_label_is_refused():
    r = ask(scripted(reply(Q2, "P9", Q2), reply(Q2, "P9", Q2)))
    assert r["status"] == "refused" and any("unknown label" in d for d in r["details"])


def test_model_supplied_chunk_id_is_ignored():
    raw = json.dumps({"answer": Q2, "citations": [{"chunk_id": "syn-doc-001#02", "quote": Q2}]})
    r = ask(scripted(raw, raw))
    assert r["status"] == "refused" and any("unknown label" in d for d in r["details"])
