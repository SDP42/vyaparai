# ruff: noqa: E501
"""Document intelligence: reading files, chunking, hybrid retrieval, permissions and honesty."""

import io
import json
import zipfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.services.docs import bm25, chunk, embed, extract
from tests.test_bills import _pdf
from tests.test_team import _join

ROOT = Path(__file__).resolve().parents[3] / "data" / "sample" / "docs"
EVAL = json.loads((Path(__file__).parent / "data" / "docs_eval.json").read_text(encoding="utf-8"))


def _model_ready() -> bool:
    try:
        embed.embed(["x"])
        return True
    except Exception:
        return False


needs_model = pytest.mark.skipif(not _model_ready(), reason="embedding model not available offline")


def _docx(paragraphs: list[tuple[str, str]]) -> bytes:
    ns = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    body = ""
    for style, text in paragraphs:
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        body += f"<w:p>{ppr}<w:r><w:t>{text}</w:t></w:r></w:p>"
    xml = f'<?xml version="1.0"?><w:document {ns}><w:body>{body}</w:body></w:document>'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


# ------------------------------------------------------------------ reading and chunking


def test_text_headings_are_kept_with_their_paragraphs() -> None:
    kind, blocks = extract.extract(
        "a.txt",
        b"Refund Policy\n\nRefunds take two days.\n\nExchange Rules\n\nExchange within a week.",
    )
    assert kind == "text"
    assert [(b.heading, b.text) for b in blocks] == [
        ("Refund Policy", "Refunds take two days."),
        ("Exchange Rules", "Exchange within a week."),
    ]


def test_docx_headings_and_text() -> None:
    kind, blocks = extract.extract(
        "terms.docx",
        _docx(
            [
                ("Heading1", "Payment"),
                ("", "Pay in 21 days."),
                ("Heading1", "Delivery"),
                ("", "Next day."),
            ]
        ),
    )
    assert kind == "docx"
    assert [(b.heading, b.text) for b in blocks] == [
        ("Payment", "Pay in 21 days."),
        ("Delivery", "Next day."),
    ]


def test_pdf_pages_are_recorded() -> None:
    _, blocks = extract.extract(
        "a.pdf", _pdf("Return Policy\n\nSealed packs can be returned within three days.")
    )
    assert blocks
    assert blocks[0].page == 1


def test_bad_files_are_refused() -> None:
    for name, data in [
        ("a.exe", b"MZ"),
        ("a.txt", b""),
        ("a.docx", b"PK\x03\x04junk"),
        ("a.pdf", b"%PDF-1.4 junk"),
    ]:
        with pytest.raises(extract.DocumentFileError):
            extract.extract(name, data)
    with pytest.raises(extract.DocumentFileError):
        extract.extract("big.txt", b"x" * (extract.MAX_BYTES + 1))


def test_chunks_respect_size_and_keep_sections() -> None:
    long = " ".join(f"Sentence number {i} is about rice and sugar." for i in range(120))
    cs = chunk.chunk([extract.Block(long, 1, "Stock"), extract.Block("Short rule.", 2, "Other")])
    assert all(len(c.text.split()) <= chunk.MAX_WORDS + chunk.OVERLAP_WORDS + 10 for c in cs)
    assert cs[0].section == "Stock"
    assert cs[-1].section == "Other"
    assert len(cs) >= 3


def test_bm25_finds_exact_terms_in_three_scripts() -> None:
    docs = [
        "GSTR-3B is due on the 20th",
        "रिफंड दो दिन में मिलता है",
        "udhaar ka limit teen hazar hai",
        "wholesale rice price list",
    ]
    bm = bm25.BM25([bm25.tokenize(d) for d in docs])
    for q, want in [("when is GSTR-3B due", 0), ("रिफंड कब मिलता है", 1), ("udhaar limit", 2)]:
        s = bm.scores(bm25.tokenize(q))
        assert int(np.argmax(s)) == want


# ------------------------------------------------------------------ retrieval quality (needs the model)


@pytest.fixture(scope="module")
def corpus():
    from app.services.docs.service import KEYWORD_WEIGHT

    chunks, meta = [], []
    for f in sorted(ROOT.glob("*.txt")):
        _, blocks = extract.extract(f.name, f.read_bytes())
        for c in chunk.chunk(blocks):
            chunks.append(c.text)
            meta.append(f.name)
    return (
        chunks,
        meta,
        embed.embed(chunks),
        bm25.BM25([bm25.tokenize(c) for c in chunks]),
        KEYWORD_WEIGHT,
    )


def _rank(corpus, q: str):
    _, _, emb, bm, a = corpus
    d, k = emb @ embed.embed([q])[0], np.array(bm.scores(bm25.tokenize(q)))
    mm = lambda x: (x - x.min()) / (x.max() - x.min()) if x.max() > x.min() else x * 0  # noqa: E731
    return list(np.argsort(-(a * mm(k) + (1 - a) * mm(d))))


@needs_model
@pytest.mark.parametrize(("tier", "min_r3", "min_mrr"), [(None, 0.95, 0.90), ("hard", 0.85, 0.75)])
def test_retrieval_quality(corpus, tier, min_r3, min_mrr) -> None:
    """Development set: the keyword weight was tuned on these questions, so these scores are optimistic."""
    chunks, meta, *_ = corpus
    qs = [q for q in EVAL if q["doc"] and q.get("tier") == tier]
    r3 = mrr = 0.0
    for q in qs:
        order = _rank(corpus, q["q"])
        good = [meta[i] == q["doc"] and q["must"].lower() in chunks[i].lower() for i in order[:10]]
        r3 += any(good[:3])
        mrr += next((1 / (r + 1) for r, g in enumerate(good) if g), 0)
    n = len(qs)
    print(f"{tier or 'easy'}: R@3 {r3 / n:.2f} MRR {mrr / n:.2f} (n={n})")
    assert r3 / n >= min_r3
    assert mrr / n >= min_mrr


# ------------------------------------------------------------------ API


@pytest.fixture
def ws(client: TestClient, make_user):
    h = make_user("docs@shop.in")
    wid = client.post("/api/v1/workspaces", json={"name": "Shop"}, headers=h).json()["id"]
    return h, wid


def _up(
    client,
    h,
    wid,
    path: Path | None = None,
    name="doc.txt",
    data: bytes | None = None,
    role="viewer",
):
    return client.post(
        f"/api/v1/workspaces/{wid}/documents",
        files={
            "file": (
                name if path is None else path.name,
                data if data is not None else path.read_bytes(),
            )
        },
        data={"min_role": role},
        headers=h,
    )


@needs_model
def test_upload_search_and_cite(client: TestClient, ws) -> None:
    h, wid = ws
    for f in ("supplier_terms_ganesh.txt", "return_policy_shop.txt", "gst_notes_for_ca.txt"):
        assert _up(client, h, wid, ROOT / f).status_code == 201
    r = client.post(
        f"/api/v1/workspaces/{wid}/documents/search",
        json={"query": "How many days to pay the Ganesh Traders invoice?"},
        headers=h,
    ).json()
    assert r["confidence"] in {"high", "possible"}
    assert "21 days" in r["answer"]
    assert r["results"][0]["title"].lower().startswith("supplier terms")
    assert r["results"][0]["section"] or r["results"][0]["page"] is None


@needs_model
def test_hindi_and_hinglish_questions_find_their_documents(client: TestClient, ws) -> None:
    h, wid = ws
    for f in ("udhaar_credit_rules.txt", "hindi_safai_niyam.txt", "hinglish_stock_hidayat.txt"):
        _up(client, h, wid, ROOT / f)
    base = f"/api/v1/workspaces/{wid}/documents/search"
    a = client.post(base, json={"query": "udhaar ka limit kitna hai"}, headers=h).json()
    assert "3,000" in a["answer"]
    b = client.post(base, json={"query": "एक्सपायरी की तारीख कब जाँचनी है"}, headers=h).json()
    assert "सोमवार" in b["answer"]


@needs_model
def test_questions_outside_the_documents_do_not_get_a_confident_answer(
    client: TestClient, ws
) -> None:
    h, wid = ws
    for f in ROOT.glob("*.txt"):
        _up(client, h, wid, f)
    base = f"/api/v1/workspaces/{wid}/documents/search"
    unanswerable = [q["q"] for q in EVAL if q["doc"] is None]
    confident = [
        q
        for q in unanswerable
        if client.post(base, json={"query": q}, headers=h).json()["confidence"] == "high"
    ]
    print("confident answers to unanswerable questions:", confident)
    assert len(confident) <= 2  # honest limit: similarity alone cannot refuse everything


@needs_model
def test_a_document_that_contains_instructions_is_only_quoted(client: TestClient, ws) -> None:
    h, wid = ws
    _up(client, h, wid, ROOT / "ignore_instructions_test.txt")
    r = client.post(
        f"/api/v1/workspaces/{wid}/documents/search",
        json={"query": "how many packs in a carton of tea"},
        headers=h,
    ).json()
    assert "24 packs" in r["answer"]
    assert "transfer" not in r["answer"].lower()
    # nothing was executed: no new members, no changes; the text is only returned as data
    assert client.get(f"/api/v1/workspaces/{wid}/members", headers=h).json().__len__() == 1


@needs_model
def test_restricted_documents_are_filtered_before_ranking(
    client: TestClient, ws, make_user
) -> None:
    h, wid = ws
    viewer = make_user("view@shop.in")
    assert _join(client, wid, h, viewer, "viewer")[0].status_code == 200
    assert _up(client, h, wid, ROOT / "staff_leave_salary.txt", role="admin").status_code == 201
    assert _up(client, h, wid, ROOT / "return_policy_shop.txt", role="viewer").status_code == 201
    base = f"/api/v1/workspaces/{wid}/documents"
    docs = client.get(base, headers=viewer).json()
    assert [d["title"] for d in docs] == ["return policy shop"]
    r = client.post(
        f"{base}/search", json={"query": "how many paid leaves per year"}, headers=viewer
    ).json()
    assert all("salary" not in x["title"].lower() for x in r["results"])
    assert "12 paid" not in (r["answer"] or "")
    admin_doc = client.get(base, headers=h).json()
    leave = next(d for d in admin_doc if "salary" in d["title"])
    assert client.get(f"{base}/{leave['id']}", headers=viewer).status_code == 404
    mine = client.post(
        f"{base}/search", json={"query": "how many paid leaves per year"}, headers=h
    ).json()
    assert "12 paid" in mine["answer"]


@needs_model
def test_access_level_cannot_exceed_the_uploaders_role(client: TestClient, ws, make_user) -> None:
    h, wid = ws
    analyst = make_user("an@shop.in")
    _join(client, wid, h, analyst, "analyst")
    assert (
        _up(
            client, analyst, wid, data=b"Secret admin note about margins.", role="owner"
        ).status_code
        == 403
    )
    assert (
        _up(
            client, analyst, wid, data=b"Public note about opening hours.", role="viewer"
        ).status_code
        == 201
    )


@needs_model
def test_duplicates_delete_and_tenancy(client: TestClient, ws, make_user) -> None:
    h, wid = ws
    assert (
        _up(
            client, h, wid, data=b"Return Policy\n\nSealed packs can be returned in 3 days."
        ).status_code
        == 201
    )
    assert (
        _up(
            client, h, wid, data=b"Return Policy\n\nSealed packs can be returned in 3 days."
        ).status_code
        == 409
    )
    stranger = make_user("x@x.in")
    base = f"/api/v1/workspaces/{wid}/documents"
    assert client.get(base, headers=stranger).status_code == 404
    doc = client.get(base, headers=h).json()[0]
    assert client.delete(f"{base}/{doc['id']}", headers=h).status_code == 204
    assert (
        client.post(f"{base}/search", json={"query": "return policy"}, headers=h).json()["results"]
        == []
    )


def test_search_input_is_bounded(client: TestClient, ws) -> None:
    h, wid = ws
    base = f"/api/v1/workspaces/{wid}/documents/search"
    assert client.post(base, json={"query": "x"}, headers=h).status_code == 422
    assert client.post(base, json={"query": "y" * 301}, headers=h).status_code == 422
    r = client.post(base, json={"query": "anything here"}, headers=h)
    assert r.status_code == 200
    assert r.json()["results"] == []
