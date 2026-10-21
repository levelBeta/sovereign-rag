import chunker
import pii


def r(t):
    return pii.redact(t)


def test_email():
    assert r("Contact jane.doe@example.com now") == ("Contact [REDACTED-EMAIL] now", {"email": 1})


def test_phones():
    for p in ("0412 345 678", "+61 412 345 678", "(03) 9123 4567", "03 9123 4567", "+61 3 9123 4567"):
        assert r("Call " + p + " today") == ("Call [REDACTED-PHONE] today", {"phone": 1})


def test_tfn_valid_redacted_near_miss_kept():
    assert r("TFN 123 456 782") == ("TFN [REDACTED-TFN]", {"tfn": 1})
    assert r("TFN 123 456 783") == ("TFN 123 456 783", {})


def test_medicare_valid_redacted_near_miss_kept():
    assert r("Medicare 2123 45670 1") == ("Medicare [REDACTED-MEDICARE]", {"medicare": 1})
    assert r("Medicare 2123 45671 1") == ("Medicare 2123 45671 1", {})


def test_card_valid_redacted_near_miss_kept():
    assert r("Card 4111 1111 1111 1111") == ("Card [REDACTED-CARD]", {"card": 1})
    assert r("Card 4111 1111 1111 1112") == ("Card 4111 1111 1111 1112", {})


def test_combined():
    t, c = r("Email a@b.co, TFN 123 456 782 and card 4111 1111 1111 1111")
    assert t == "Email [REDACTED-EMAIL], TFN [REDACTED-TFN] and card [REDACTED-CARD]"
    assert c == {"email": 1, "tfn": 1, "card": 1}


def test_corpus_has_no_false_positives():
    for c in chunker.load_chunks():
        assert r(c["text"]) == (c["text"], {})


def test_counts_only_never_values():
    t, c = r("a@b.co 4111 1111 1111 1111")
    assert "4111" not in t and "a@b.co" not in t
    assert all(isinstance(v, int) for v in c.values())
