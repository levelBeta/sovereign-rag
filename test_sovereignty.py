import socket
import time
import sovereignty


def test_loopback_connection_is_seen_and_passes():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port = srv.getsockname()[1]
    with sovereignty.SovereigntyMonitor(interval=0.05) as m:
        c = socket.create_connection(("127.0.0.1", port))
        time.sleep(0.3)
        c.close()
    srv.close()
    r = m.report()
    assert r["passed"] is True
    assert r["samples"] >= 2
    assert any(x[2] == port for x in r["loopback_connections"])


def test_external_address_is_flagged(monkeypatch):
    fake = [(1234, "203.0.113.5", 443)]
    monkeypatch.setattr(sovereignty, "_remote_conns", lambda pids: fake)
    m = sovereignty.SovereigntyMonitor(interval=0.05)
    m._sample()
    r = m.report()
    assert r["passed"] is False
    assert (1234, "203.0.113.5", 443) in r["external_connections"]
    assert "external TCP connection" in r["claim"]


def test_report_states_scope():
    r = sovereignty.SovereigntyMonitor().report()
    assert "TCP only" in r["scope"]
