import re
import pytest
import chunker


def test_totals_match_hand_count():
    cs = chunker.load_chunks()
    assert len(cs) == 49
    by = {}
    for c in cs:
        by[c["classification"]] = by.get(c["classification"], 0) + 1
    assert by == {"public": 23, "internal": 15, "restricted": 11}


def test_ids_unique_and_well_formed():
    ids = [c["chunk_id"] for c in chunker.load_chunks()]
    assert len(set(ids)) == len(ids)
    assert all(re.fullmatch(r"syn-doc-\d{3}#\d{2}", i) for i in ids)


def test_roles_follow_classification():
    for c in chunker.load_chunks():
        if c["classification"] == "restricted":
            assert c["roles"] == ["ciso"]
        elif c["classification"] == "internal":
            assert c["roles"] == ["manager", "ciso"]
        else:
            assert c["roles"] == ["analyst", "manager", "ciso"]


def test_canary_only_in_one_known_chunk():
    hits = [c["chunk_id"] for c in chunker.load_chunks() if "CANARY" in c["text"]]
    assert hits == ["syn-doc-013#02"]


def test_ids_are_deterministic():
    a = [c["chunk_id"] for c in chunker.load_chunks()]
    b = [c["chunk_id"] for c in chunker.load_chunks()]
    assert a == b


def test_bad_documents_are_rejected():
    ok = "doc_id: x\ntitle: t\nclassification: public\nroles: analyst\n---\nline\n"
    assert len(chunker.parse_document(ok)) == 1
    with pytest.raises(ValueError):
        chunker.parse_document(ok.replace("---\n", ""))
    with pytest.raises(ValueError):
        chunker.parse_document(ok.replace("public", "secret"))
    with pytest.raises(ValueError):
        chunker.parse_document(ok.replace("analyst", "intern"))
