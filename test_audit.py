import json
import audit


def _make(tmp_path):
    p = str(tmp_path / "audit_test.jsonl")
    for i in range(4):
        audit.append(p, "event", {"n": i})
    return p


def test_clean_log_verifies(tmp_path):
    r = audit.verify(_make(tmp_path))
    assert r["ok"] and r["entries"] == 4 and r["first_bad"] is None


def test_edit_breaks_chain_and_cascades(tmp_path):
    p = _make(tmp_path)
    lines = open(p, encoding="utf-8").read().splitlines()
    e = json.loads(lines[1])
    e["data"]["n"] = 999
    lines[1] = json.dumps(e, sort_keys=True)
    open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    r = audit.verify(p)
    assert not r["ok"]
    assert r["first_bad"] == 2
    assert r["bad_lines"] == [2, 3, 4]


def test_deleted_entry_is_detected(tmp_path):
    p = _make(tmp_path)
    lines = open(p, encoding="utf-8").read().splitlines()
    del lines[1]
    open(p, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    r = audit.verify(p)
    assert not r["ok"] and r["first_bad"] == 2
