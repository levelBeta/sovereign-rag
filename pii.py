"""Deterministic PII redaction for Sovereign RAG. ALL DATA IS SYNTHETIC.
Runs on the query before anything else. Returns the redacted text and COUNTS only,
never the matched values. Card, TFN and Medicare matches are checksum-validated.
Limits: regex rules, AU formats only, no names or addresses.
"""
import re

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CARD = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
PHONE = re.compile(
    r"(?<![\d+])(?:(?:\+61 ?|0)4\d{2} ?\d{3} ?\d{3}"
    r"|(?:\+61 ?[2378]|\(0[2378]\)|0[2378]) ?\d{4} ?\d{4})(?!\d)"
)
MEDICARE = re.compile(r"(?<!\d)[2-6]\d{3}[ -]?\d{5}[ -]?\d(?:[ -]?\d)?(?!\d)")
TFN = re.compile(r"(?<!\d)\d{3}[ -]?\d{3}[ -]?\d{3}(?!\d)")


def _luhn(d):
    total = 0
    for i, ch in enumerate(reversed(d)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _tfn_ok(d):
    w = (1, 4, 3, 7, 5, 8, 6, 9, 10)
    return sum(int(c) * k for c, k in zip(d, w)) % 11 == 0


def _medicare_ok(d):
    w = (1, 3, 7, 9, 1, 3, 7, 9)
    return sum(int(c) * k for c, k in zip(d[:8], w)) % 10 == int(d[8])


def redact(text):
    """Return (redacted_text, counts). Counts hold numbers only, never values."""
    counts = {}

    def make(kind, check=None):
        def repl(m):
            digits = re.sub(r"\D", "", m.group())
            if check is not None and not check(digits):
                return m.group()
            counts[kind] = counts.get(kind, 0) + 1
            return "[REDACTED-%s]" % kind.upper()
        return repl

    text = EMAIL.sub(make("email"), text)
    text = CARD.sub(make("card", _luhn), text)
    text = PHONE.sub(make("phone"), text)
    text = MEDICARE.sub(make("medicare", _medicare_ok), text)
    text = TFN.sub(make("tfn", _tfn_ok), text)
    return text, counts
