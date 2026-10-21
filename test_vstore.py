import pytest
import chunker
import sovereignty
import vstore

PUBLIC = {"syn-doc-001", "syn-doc-002", "syn-doc-004", "syn-doc-011", "syn-doc-012", "syn-doc-013"}
RESTRICTED = {"syn-doc-007", "syn-doc-008", "syn-doc-010"}


def _ollama_up():
    try:
        vstore.embed(["ping"])
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _ollama_up(), reason="Ollama not reachable")


@pytest.fixture(scope="module")
def col():
    return vstore.build_index(chunker.load_chunks())


def _ids(col, question, role, n=5):
    q = vstore.embed([question])
    res = col.query(query_embeddings=q, n_results=n, where={"role_" + role: True})
    return res["ids"][0]


def test_index_count(col):
    assert col.count() == 49


def test_analyst_only_gets_public_docs(col):
    ids = _ids(col, "How often must passwords be rotated?", "analyst")
    assert ids and all(i.split("#")[0] in PUBLIC for i in ids)


def test_analyst_never_sees_restricted(col):
    ids = _ids(col, "How often are master encryption keys rotated?", "analyst", n=10)
    assert not any(i.split("#")[0] in RESTRICTED for i in ids)


def test_ciso_can_reach_restricted(col):
    ids = _ids(col, "How often are master encryption keys rotated?", "ciso")
    assert ids[0] == "syn-doc-007#01"


def test_no_external_tcp_during_build_and_query():
    with sovereignty.SovereigntyMonitor(interval=0.05) as m:
        c = vstore.build_index(chunker.load_chunks())
        c.query(query_embeddings=vstore.embed(["test"]), n_results=1)
    r = m.report()
    assert r["passed"] is True and r["samples"] >= 2
