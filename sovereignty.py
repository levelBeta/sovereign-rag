"""Process-scoped sovereignty check for Sovereign RAG.
ALL DATA IS SYNTHETIC. Samples TCP connections of THIS process and its children
while work runs, and reports any non-loopback remote address. The claim is about
this process only, not the whole machine. TCP only. Snapshot sampling, not proof.
"""
import os
import threading
import time

import psutil

LOOPBACK = {"127.0.0.1", "::1", "::ffff:127.0.0.1"}


def _tree_pids():
    me = psutil.Process(os.getpid())
    pids = [me.pid]
    try:
        pids += [c.pid for c in me.children(recursive=True)]
    except psutil.Error:
        pass
    return pids


def _ollama_pids():
    pids = []
    for p in psutil.process_iter(["pid", "name"]):
        if (p.info["name"] or "").lower() == "ollama.exe":
            pids.append(p.info["pid"])
    return pids


def _remote_conns(pids):
    """Return (pid, remote_ip, remote_port) for connections with a remote address."""
    found = []
    for pid in pids:
        try:
            conns = psutil.Process(pid).net_connections(kind="tcp")
        except (psutil.Error, OSError):
            continue
        for c in conns:
            if c.raddr:
                found.append((pid, c.raddr.ip, c.raddr.port))
    return found


class SovereigntyMonitor:
    def __init__(self, interval=0.2):
        self.interval = interval
        self._stop = threading.Event()
        self._thread = None
        self.samples = 0
        self.external = set()
        self.loopback = set()
        self.ollama_external = set()

    def _sample(self):
        for pid, ip, port in _remote_conns(_tree_pids()):
            if ip in LOOPBACK:
                self.loopback.add((pid, ip, port))
            else:
                self.external.add((pid, ip, port))
        for pid, ip, port in _remote_conns(_ollama_pids()):
            if ip not in LOOPBACK:
                self.ollama_external.add((pid, ip, port))
        self.samples += 1

    def _run(self):
        while not self._stop.is_set():
            self._sample()
            time.sleep(self.interval)

    def __enter__(self):
        self._sample()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._thread.join()
        self._sample()
        return False

    def report(self):
        n = self.samples
        if self.external:
            claim = f"{len(self.external)} external TCP connection(s) observed."
        else:
            claim = f"No external TCP connection observed from this process tree in {n} samples."
        scope = f"TCP only. Snapshot sampling every {self.interval}s, so a very short connection could be missed."
        return {
            "passed": not self.external,
            "samples": n,
            "external_connections": sorted(self.external),
            "loopback_connections": sorted(self.loopback),
            "ollama_server_external": sorted(self.ollama_external),
            "claim": claim,
            "scope": scope,
        }
