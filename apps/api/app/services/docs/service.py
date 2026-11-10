"""Add, search and remove documents.

Search = pretrained multilingual embeddings fused with BM25 keywords (weight chosen by measurement,
docs/DOCUMENTS.md), run only over documents the asker's role may read. The answer is extractive:
the best sentence of the best passage with its citation. It never composes new text, so a document
containing instructions cannot make the product do or say anything; it can only be quoted.
"""

import hashlib
import re
import uuid
from dataclasses import dataclass
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, NotFoundError
from app.models.document import Document, DocumentChunk
from app.models.workspace import WorkspaceRole
from app.services import audit
from app.services.docs import bm25, chunk, embed, extract

KEYWORD_WEIGHT = 0.3
CONFIDENT = 0.40  # dense cosine of the best passage at or above this: answer
POSSIBLE = 0.30  # between this and CONFIDENT: show it but say it may not answer the question
MAX_DOCS = 200
MAX_CHUNKS = 20_000
_SENT = re.compile(r"(?<=[.!?।])\s+|\n+")


class DocLimitError(AppError):
    status_code = 409
    code = "limit_reached"


@dataclass(slots=True)
class _Index:
    signature: tuple[int, str]
    ids: list[uuid.UUID]
    docs: list[uuid.UUID]
    matrix: np.ndarray
    bm: bm25.BM25
    min_roles: list[str]


_cache: dict[uuid.UUID, _Index] = {}


def _signature(db: Session, ws: uuid.UUID) -> tuple[int, str]:
    n, last = db.execute(
        select(func.count(Document.id), func.max(Document.updated_at)).where(
            Document.workspace_id == ws
        )
    ).one()
    return int(n), str(last)


def add_document(
    db: Session, ws: uuid.UUID, user_id: uuid.UUID, filename: str, content: bytes, min_role: str
) -> Document:
    if min_role not in {r.value for r in WorkspaceRole}:
        raise AppError("Unknown access level")
    fh = hashlib.sha256(content).hexdigest()
    if db.scalars(
        select(Document).where(Document.workspace_id == ws, Document.file_hash == fh)
    ).first():
        raise ConflictError("This exact file was already added")
    if (
        db.scalar(select(func.count(Document.id)).where(Document.workspace_id == ws)) or 0
    ) >= MAX_DOCS:
        raise DocLimitError(f"A workspace can hold {MAX_DOCS} documents.")
    kind, blocks = extract.extract(filename, content)
    chunks = chunk.chunk(blocks)
    total = (
        db.scalar(select(func.count(DocumentChunk.id)).where(DocumentChunk.workspace_id == ws)) or 0
    )
    if total + len(chunks) > MAX_CHUNKS:
        raise DocLimitError("This workspace's document index is full.")
    vecs = embed.embed([c.text for c in chunks])
    title = re.sub(r"[_\-]+", " ", filename.rsplit(".", 1)[0]).strip()[:200] or "Document"
    doc = Document(
        workspace_id=ws, title=title, filename=filename[:255], kind=kind, file_hash=fh,
        pages=max((b.page or 0 for b in blocks), default=0) or None, chunk_count=len(chunks),
        embed_model=embed.DEFAULT_MODEL, min_role=min_role, created_by_id=user_id,
    )  # fmt: skip
    for i, (c, v) in enumerate(zip(chunks, vecs, strict=True)):
        doc.chunks.append(
            DocumentChunk(
                workspace_id=ws, position=i, page=c.page, section=c.section, text=c.text,
                embedding=v.astype(np.float32).tobytes(),
            )
        )  # fmt: skip
    db.add(doc)
    audit.record(
        db, action="document.added", actor_user_id=user_id, workspace_id=ws,
        entity_type="document", entity_id=None, details={"chunks": len(chunks), "min_role": min_role},
    )  # fmt: skip
    db.commit()
    _cache.pop(ws, None)
    return doc


def get(db: Session, ws: uuid.UUID, doc_id: uuid.UUID, role: WorkspaceRole) -> Document:
    d = db.get(Document, doc_id)
    if d is None or d.workspace_id != ws or not role.at_least(WorkspaceRole(d.min_role)):
        raise NotFoundError("Document not found")  # same answer for "missing" and "not allowed"
    return d


def listing(db: Session, ws: uuid.UUID, role: WorkspaceRole) -> list[Document]:
    rows = db.scalars(
        select(Document).where(Document.workspace_id == ws).order_by(Document.created_at.desc())
    )
    return [d for d in rows if role.at_least(WorkspaceRole(d.min_role))]


def remove(db: Session, doc: Document, actor_id: uuid.UUID) -> None:
    audit.record(
        db, action="document.removed", actor_user_id=actor_id, workspace_id=doc.workspace_id,
        entity_type="document", entity_id=doc.id,
    )  # fmt: skip
    ws = doc.workspace_id
    db.delete(doc)
    db.commit()
    _cache.pop(ws, None)


def _index(db: Session, ws: uuid.UUID) -> _Index | None:
    sig = _signature(db, ws)
    hit = _cache.get(ws)
    if hit is not None and hit.signature == sig:
        return hit
    rows = db.execute(
        select(
            DocumentChunk.id,
            DocumentChunk.document_id,
            DocumentChunk.text,
            DocumentChunk.embedding,
            Document.min_role,
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.workspace_id == ws)
        .order_by(Document.created_at, DocumentChunk.position)
    ).all()
    if not rows:
        return None
    idx = _Index(
        signature=sig, ids=[r[0] for r in rows], docs=[r[1] for r in rows],
        matrix=np.vstack([np.frombuffer(r[3], dtype=np.float32) for r in rows]),
        bm=bm25.BM25([bm25.tokenize(r[2]) for r in rows]), min_roles=[r[4] for r in rows],
    )  # fmt: skip
    _cache[ws] = idx
    return idx


def _norm(x: np.ndarray) -> np.ndarray:
    r = float(x.max() - x.min()) if len(x) else 0.0
    return (x - x.min()) / r if r else np.zeros_like(x)


def _best_sentence(
    text: str, query_vec: np.ndarray, query_tokens: list[str], heading: str | None
) -> str:
    body = text[len(heading) :].lstrip("\n") if heading and text.startswith(heading) else text
    sents = [s.strip() for s in _SENT.split(body) if len(s.strip().split()) >= 4]
    if len(sents) <= 1:
        return (sents[0] if sents else body).strip()
    sv = embed.embed(sents)
    dense = sv @ query_vec
    kw = np.array([len(set(query_tokens) & set(bm25.tokenize(s))) for s in sents], dtype=float)
    score = _norm(dense) * 0.7 + _norm(kw) * 0.3
    best = int(np.argmax(score))
    # A near-tie is shown together: two neighbouring rules are better than the wrong one alone.
    close = [i for i in np.argsort(-score)[:2] if score[i] >= 0.8 * score[best]]
    return " ".join(sents[i] for i in sorted(int(i) for i in close))


def search(
    db: Session, ws: uuid.UUID, role: WorkspaceRole, query: str, k: int = 4
) -> dict[str, Any]:
    q = query.strip()
    idx = _index(db, ws)
    empty: dict[str, Any] = {"query": q, "answer": None, "confidence": "none", "results": []}
    if idx is None:
        return empty
    allowed = np.array(
        [role.at_least(WorkspaceRole(r)) for r in idx.min_roles]
    )  # filter BEFORE ranking
    if not allowed.any():
        return empty
    qv = embed.embed([q])[0]
    qt = bm25.tokenize(q)
    dense = idx.matrix @ qv
    kw = np.array(idx.bm.scores(qt))
    pos = np.where(allowed)[0]
    fused = KEYWORD_WEIGHT * _norm(kw[pos]) + (1 - KEYWORD_WEIGHT) * _norm(dense[pos])
    order = pos[np.argsort(-fused)][: max(1, min(k, 10))]
    ids = [idx.ids[i] for i in order]
    chunks = {c.id: c for c in db.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(ids)))}
    docs = {
        d.id: d
        for d in db.scalars(select(Document).where(Document.id.in_({idx.docs[i] for i in order})))
    }
    top_dense = float(dense[order[0]])
    lex = len(set(qt) & set(bm25.tokenize(chunks[idx.ids[order[0]]].text)))  # exact words in common
    if top_dense >= CONFIDENT or (lex >= 2 and top_dense >= 0.15):
        conf = "high"
    elif top_dense >= POSSIBLE or (lex >= 1 and top_dense >= 0.2):
        conf = "possible"
    else:
        conf = "none"
    results = []
    for i in order:
        c, d = chunks[idx.ids[i]], docs[idx.docs[i]]
        results.append(
            {"document_id": str(d.id), "title": d.title, "page": c.page, "section": c.section,
             "text": c.text, "score": round(float(dense[i]), 3)}
        )  # fmt: skip
    if conf == "none":
        return {**empty, "results": []}
    answer = _best_sentence(
        str(results[0]["text"]),
        qv,
        qt,
        results[0]["section"] if isinstance(results[0]["section"], str) else None,
    )
    return {"query": q, "answer": answer, "confidence": conf, "results": results}
