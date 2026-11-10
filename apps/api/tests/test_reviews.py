"""Review intelligence: reading text, importing files, summaries, and honest accuracy numbers."""

import csv
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.services.reviews.analyzer import analyse, detect_language

GOLD = Path(__file__).parent / "data" / "reviews_gold.csv"
LABELS = ("negative", "neutral", "positive")


def _macro_f1(pairs: list[tuple[str, str]]) -> float:
    f1s = []
    for c in LABELS:
        tp = sum(1 for t, p in pairs if t == c and p == c)
        fp = sum(1 for t, p in pairs if t != c and p == c)
        fn = sum(1 for t, p in pairs if t == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / len(f1s)


def _gold() -> list[dict[str, str]]:
    with GOLD.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_language_detection_on_the_gold_set() -> None:
    rows = _gold()
    right = sum(detect_language(r["text"]) == r["language"] for r in rows)
    assert right / len(rows) >= 0.9


@pytest.mark.parametrize("lang", ["en", "hinglish", "hi"])
def test_sentiment_macro_f1_per_language(lang: str) -> None:
    pairs = [(r["label"], analyse(r["text"]).label) for r in _gold() if r["language"] == lang]
    assert len(pairs) >= 19
    f1 = _macro_f1(pairs)
    print(f"{lang}: macro-F1 {f1:.2f} on {len(pairs)} self-written reviews")
    assert f1 >= 0.75, Counter(pairs)


def test_negation_and_contrast() -> None:
    assert analyse("not good").label == "negative"
    assert analyse("not bad at all, quite good").label != "negative"
    a = analyse("Product accha hai but delivery bahut late aaya")
    polarity = {t.theme: t.polarity for t in a.themes}
    assert polarity["delivery"] < 0 < polarity["quality"]


def test_themes_carry_evidence() -> None:
    a = analyse("Packing was torn. Staff very polite.")
    by = {t.theme: t for t in a.themes}
    assert by["packaging"].polarity < 0 < by["service"].polarity
    assert "torn" in by["packaging"].snippet.lower()


def test_empty_and_odd_text_do_not_crash() -> None:
    for t in ["", "   ", "!!!", "👍", "😡😡", "x" * 5000, "१२३"]:
        a = analyse(t)
        assert -1 <= a.sentiment <= 1


# ------------------------------------------------------------------ API

CSV = (
    "Date,Product,Rating,Review\n"
    "2026-10-01,SKU-A,5,Bahut accha product hai\n"
    "2026-10-02,SKU-A,1,Delivery bahut late aayi and packing torn\n"
    "2026-10-03,Weekly,2,Bekar quality\n"
    "2026-10-03,Weekly,5,Terrible. Not fresh at all.\n"
    "2026-10-03,Weekly,5,Terrible. Not fresh at all.\n"
    ",,,\n"
)


@pytest.fixture
def ws(client: TestClient, make_user):
    h = make_user("rev@shop.in")
    wid = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"]
    return h, wid


def _post(client, h, wid, content: str):
    return client.post(
        f"/api/v1/workspaces/{wid}/reviews/import",
        files={"file": ("r.csv", content.encode(), "text/csv")},
        headers=h,
    )


def test_import_dedupes_and_reports(client: TestClient, ws) -> None:
    h, wid = ws
    r = _post(client, h, wid, CSV).json()
    assert r["added"] == 4
    assert r["duplicates"] == 1
    assert r["empty"] == 1
    again = _post(client, h, wid, CSV).json()
    assert again["added"] == 0


def test_import_needs_a_review_column(client: TestClient, ws) -> None:
    h, wid = ws
    r = _post(client, h, wid, "Date,Rating\n2026-01-01,5\n")
    assert r.status_code == 422


def test_summary_list_and_try(client: TestClient, ws) -> None:
    h, wid = ws
    _post(client, h, wid, CSV)
    base = f"/api/v1/workspaces/{wid}/reviews"
    s = client.get(f"{base}/summary?days=365", headers=h).json()
    assert s["total"] == 4
    assert s["labels"]["negative"] >= 2
    assert {t["theme"] for t in s["themes"]} >= {"delivery", "freshness"}
    assert s["mismatch"] >= 1  # a 5-star "Terrible"
    neg = client.get(f"{base}?label=negative&theme=delivery", headers=h).json()
    assert neg["total"] >= 1
    assert all(i["label"] == "negative" for i in neg["items"])
    t = client.post(f"{base}/try", json={"text": "Delivery nahi hui, bekar service"}, headers=h)
    assert t.json()["label"] == "negative"


def test_viewers_cannot_import_and_strangers_see_nothing(client: TestClient, ws, make_user) -> None:
    _, wid = ws
    stranger = make_user("x@x.in")
    assert (
        client.get(f"/api/v1/workspaces/{wid}/reviews/summary", headers=stranger).status_code == 404
    )
    assert _post(client, stranger, wid, CSV).status_code == 404


# ------------------------------------------------------------------ development set and shop model


def test_development_set_is_optimistic_but_sane() -> None:
    """Vocabulary was extended after reading this set's mistakes, so it is a development set.

    It guards against regressions; it is NOT an estimate of accuracy on unseen reviews.
    """
    dev = Path(__file__).parent / "data" / "reviews_dev.csv"
    with dev.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    right = sum(analyse(r["text"]).label == r["label"] for r in rows)
    assert right / len(rows) >= 0.8


def test_no_polarity_flips_on_clear_cases() -> None:
    for r in _gold():
        got = analyse(r["text"]).label
        assert {r["label"], got} != {"positive", "negative"}, (r["text"], got)


def test_shop_model_learns_words_the_lists_do_not_know() -> None:
    from app.services.reviews import supervised

    good = ["zaika lajawab", "zaika kamaal hai", "zaika ekdum top", "zaika bohot pasand aaya"]
    bad = ["chakachak nahi tha", "chhichhora saman", "chhichhora packing", "chhichhora experience"]
    texts = [t for i in range(60) for t in (good[i % 4], bad[i % 4])]
    ratings = [r for _ in range(60) for r in (5, 1)]
    model = supervised.fit(texts, ratings)
    assert model is not None
    assert model.holdout_accuracy >= 0.9
    # "chhichhora" is in no word list, and the lexicon says 0 for it
    assert analyse("chhichhora dukaan").sentiment == 0.0
    assert supervised.blend(0.0, model, "chhichhora dukaan") < -0.15


def test_shop_model_is_not_used_when_data_is_thin_or_random() -> None:
    from app.services.reviews import supervised

    assert supervised.fit(["a b"] * 20, [5] * 20) is None
    import random

    rnd = random.Random(1)  # noqa: S311  (test data, not security)
    texts = [f"word{rnd.randint(0, 500)} word{rnd.randint(0, 500)}" for _ in range(300)]
    ratings = [rnd.choice([1, 5]) for _ in range(300)]
    assert supervised.fit(texts, ratings) is None  # no better than guessing


def test_rising_complaint_theme_raises_an_alert(client: TestClient, ws) -> None:
    from datetime import UTC, datetime, timedelta

    h, wid = ws
    today = datetime.now(UTC).date()
    # a tiny sales file so alerts have a data range to work with
    rows = ["Bill No,Bill Date,Item Code,Item Name,Qty,Rate"]
    for i in range(10):
        d = (today - timedelta(days=i)).strftime("%d/%m/%Y")
        rows.append(f"B{i},{d},SKU-A,Tea,2,100")
    from tests.test_ingestion import full_flow

    _, base, _ = full_flow(client, h, wid, "\n".join(rows).encode())
    client.post(f"{base}/import", headers=h)
    lines = ["Date,Review"]
    for i in range(8):
        d = (today - timedelta(days=i + 1)).isoformat()
        lines.append(f"{d},Delivery was very late and the courier was rude")
    assert _post(client, h, wid, "\n".join(lines)).json()["added"] == 8
    alerts = client.get(f"/api/v1/workspaces/{wid}/alerts", headers=h).json()
    hit = [a for a in alerts["items"] if a["rule"] == "review_theme"]
    assert hit
    assert "delivery" in hit[0]["key"] or "delivery" in hit[0]["title"].lower()
