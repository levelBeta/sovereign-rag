"""Tamper-evident audit log for Sovereign RAG.
ALL DATA IS SYNTHETIC. JSONL, one entry per line. Each entry's hash covers its own
content and the previous entry's hash, so editing any entry breaks the chain from there on.
"""
import hashlib
import json
import os
from datetime import datetime, timezone

GENESIS = "GENESIS"


def _canonical(entry):
    """Stable JSON of an entry without its hash field."""
    body = {k: v for k, v in entry.items() if k != "hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _hash(entry):
    return hashlib.sha256(_canonical(entry).encode("utf-8")).hexdigest()


def _last_hash(path):
    """Stored hash of the last entry, or GENESIS for a new or empty log."""
    if not os.path.exists(path):
        return GENESIS
    last = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                last = line
    if last is None:
        return GENESIS
    return json.loads(last)["hash"]


def append(path, event, data):
    """Append one chained entry and return it."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "data": data,
        "prev": _last_hash(path),
    }
    entry["hash"] = _hash(entry)
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def verify(path):
    """Walk the log. Return {'ok', 'entries', 'bad_lines', 'first_bad'} (lines are 1-based).

    Once one entry fails, every later entry is also reported bad: the chain of
    custody is broken from that point on, so nothing after it can be trusted.
    """
    bad = []
    count = 0
    broken = False
    first_bad = None
    expected_prev = GENESIS
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                count += 1
                try:
                    entry = json.loads(line)
                    recomputed = _hash(entry)
                    good = entry.get("prev") == expected_prev and entry.get("hash") == recomputed
                except (ValueError, TypeError, AttributeError):
                    good = False
                    recomputed = None
                if not good and not broken:
                    broken = True
                    first_bad = n
                if broken:
                    bad.append(n)
                # Reset to the RECOMPUTED hash so a tamper is detected at the next entry too.
                expected_prev = recomputed
    return {"ok": not bad, "entries": count, "bad_lines": bad, "first_bad": first_bad}
