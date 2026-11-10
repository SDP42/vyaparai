"""Import reviews from a CSV, analyse them, and summarise what customers are saying."""

import csv
import hashlib
import io
import re
import uuid
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.commerce import Product
from app.models.review import Review
from app.services.reviews import analyzer, lexicon, supervised

MAX_ROWS = 20_000
MAX_TEXT = 2_000

HEADERS = {
    "text": {"review", "review text", "reviews", "comment", "comments", "feedback", "text",
             "description", "remark", "remarks", "review body", "content", "रिव्यू", "समीक्षा"},
    "rating": {"rating", "ratings", "stars", "star", "star rating", "score", "rate", "रेटिंग"},
    "date": {"date", "review date", "created", "created at", "time", "posted", "reviewed on",
             "तारीख"},
    "product": {"product", "sku", "item", "item name", "item code", "product name", "product id",
                "प्रोडक्ट"},
    "source": {"source", "platform", "channel", "site"},
}  # fmt: skip


class BadReviewsFileError(AppError):
    status_code = 422
    code = "bad_reviews_file"


def _decode(content: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return content.decode(enc)
        except UnicodeError:
            continue
    raise BadReviewsFileError("The file could not be read. Save it as CSV (UTF-8) and try again.")


def _map_headers(headers: list[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    for i, h in enumerate(headers):
        key = re.sub(r"[_\-]+", " ", h.strip().lower())
        for field, names in HEADERS.items():
            if key in names and field not in found:
                found[field] = i
    return found


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d %b %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(raw[:20] if fmt != "%Y-%m-%d" else raw[:10], fmt).date()
        except ValueError:
            continue
    return None


def _parse_rating(raw: str) -> int | None:
    m = re.search(r"\d+(?:\.\d+)?", raw)
    if not m:
        return None
    v = round(float(m.group()))
    return v if 1 <= v <= 5 else None


def _fingerprint(source: str, d: date | None, rating: int | None, text: str) -> str:
    key = f"{source}|{d}|{rating}|{' '.join(text.lower().split())}"
    return hashlib.sha256(key.encode()).hexdigest()


def import_reviews(
    db: Session, ws: uuid.UUID, content: bytes, source: str = "upload"
) -> dict[str, Any]:
    rows = list(csv.reader(io.StringIO(_decode(content))))
    if len(rows) < 2:
        raise BadReviewsFileError("The file has no reviews in it.")
    cols = _map_headers(rows[0])
    if "text" not in cols:
        raise BadReviewsFileError(
            "No review column found. Name the column 'Review', 'Comment' or 'Feedback'."
        )
    if len(rows) - 1 > MAX_ROWS:
        raise BadReviewsFileError(f"Too many reviews in one file (limit {MAX_ROWS}).")
    products = db.scalars(select(Product).where(Product.workspace_id == ws)).all()
    by_key = {p.sku.lower(): p.id for p in products} | {p.name.lower(): p.id for p in products}
    have = set(db.scalars(select(Review.fingerprint).where(Review.workspace_id == ws)))
    added = dupes = empty = 0
    langs: Counter[str] = Counter()

    def cell(r: list[str], f: str) -> str:
        i = cols.get(f)
        return r[i].strip() if i is not None and i < len(r) else ""

    for r in rows[1:]:
        text = cell(r, "text")[:MAX_TEXT]
        if not text:
            empty += 1
            continue
        d, rating = _parse_date(cell(r, "date")), _parse_rating(cell(r, "rating"))
        src = cell(r, "source")[:60] or source
        fp = _fingerprint(src, d, rating, text)
        if fp in have:
            dupes += 1
            continue
        have.add(fp)
        hint = cell(r, "product")[:255] or None
        a = analyzer.analyse(text)
        langs[a.language] += 1
        db.add(
            Review(
                workspace_id=ws, fingerprint=fp, source=src, review_date=d, rating=rating,
                product_hint=hint, product_id=by_key.get((hint or "").lower()), text=text,
                language=a.language, sentiment=a.sentiment, label=a.label,
                themes=[t.as_dict() for t in a.themes], analysed_with=analyzer.VERSION,
            )
        )  # fmt: skip
        added += 1
    db.commit()
    if added and len(have) >= supervised.MIN_RATED:
        reanalyse(db, ws)  # enough reviews may now have stars to learn from
    return {
        "added": added, "duplicates": dupes, "empty": empty, "languages": dict(langs),
        "columns_found": sorted(cols),
    }  # fmt: skip


def reanalyse(db: Session, ws: uuid.UUID) -> dict[str, Any]:
    """Re-read every review; if the shop has enough star ratings, learn from them too."""
    rows = list(db.scalars(select(Review).where(Review.workspace_id == ws)))
    model = supervised.fit([r.text for r in rows], [r.rating for r in rows])
    for rv in rows:
        a = analyzer.analyse(rv.text)
        score = supervised.blend(a.sentiment, model, rv.text)
        rv.language, rv.sentiment = a.language, round(score, 3)
        rv.label = analyzer.label_for(score)
        rv.themes = [t.as_dict() for t in a.themes]
        rv.analysed_with = analyzer.VERSION + ("+shop-model" if model else "")
    db.commit()
    return {
        "reanalysed": len(rows),
        "shop_model": None if model is None else {
            "trained_on": model.trained_on, "holdout_accuracy": model.holdout_accuracy
        },
    }  # fmt: skip


def _load(db: Session, ws: uuid.UUID, since: date | None = None) -> list[Review]:
    stmt = select(Review).where(Review.workspace_id == ws)
    if since is not None:
        stmt = stmt.where((Review.review_date >= since) | (Review.review_date.is_(None)))
    return list(db.scalars(stmt))


def _theme_table(reviews: list[Review], prior: list[Review]) -> list[dict[str, Any]]:
    def stats(rs: list[Review]) -> dict[str, tuple[int, int, float]]:
        agg: dict[str, list[float]] = defaultdict(list)
        for r in rs:
            for t in r.themes or []:
                agg[t["theme"]].append(float(t["polarity"]))
        return {
            k: (len(v), sum(1 for x in v if x <= -analyzer.THRESHOLD), sum(v) / len(v))
            for k, v in agg.items()
        }

    now, before = stats(reviews), stats(prior)
    out = []
    for key, spec in lexicon.THEMES.items():
        if key not in now:
            continue
        n, neg, mean = now[key]
        pn, pneg, _ = before.get(key, (0, 0, 0.0))
        out.append(
            {
                "theme": key, "label": spec["label"], "mentions": n,
                "negative": neg, "negative_pct": round(100 * neg / n, 1),
                "mean_polarity": round(mean, 2),
                "prior_mentions": pn,
                "prior_negative_pct": round(100 * pneg / pn, 1) if pn else None,
            }
        )  # fmt: skip
    return sorted(out, key=lambda x: (-int(x["negative"]), -int(x["mentions"])))


def summary(
    db: Session, ws: uuid.UUID, days: int = 90, today: date | None = None
) -> dict[str, Any]:
    today = today or datetime.now(UTC).date()
    all_rows = _load(db, ws)
    cut = today - timedelta(days=days)
    dated = [r for r in all_rows if r.review_date is not None]
    recent = [r for r in all_rows if r.review_date is None or r.review_date >= cut]
    start = cut - timedelta(days=days)
    prior = [r for r in dated if r.review_date is not None and start <= r.review_date < cut]
    labels = Counter(r.label for r in recent)
    rated = [r.rating for r in recent if r.rating is not None]
    weekly: dict[date, list[float]] = defaultdict(list)
    for r in recent:
        if r.review_date:
            weekly[r.review_date - timedelta(days=r.review_date.weekday())].append(r.sentiment)
    return {
        "total": len(all_rows), "window_days": days, "in_window": len(recent),
        "labels": {k: labels.get(k, 0) for k in ("positive", "neutral", "negative")},
        "mean_sentiment": _mean([r.sentiment for r in recent], 3),
        "mean_rating": _mean([float(x) for x in rated], 2),
        "languages": dict(Counter(r.language for r in recent)),
        "themes": _theme_table(recent, prior),
        "weekly": [
            {"week": k.isoformat(), "reviews": len(v), "mean_sentiment": round(sum(v) / len(v), 3)}
            for k, v in sorted(weekly.items())
        ],
        "unscored": sum(1 for r in recent if r.sentiment == 0.0),
        "mismatch": sum(1 for r in recent if r.rating and _mismatch(r)),
    }  # fmt: skip


def _mean(xs: list[float], nd: int) -> float | None:
    return round(sum(xs) / len(xs), nd) if xs else None


def _mismatch(r: Review) -> bool:
    """A 4-5 star review that reads negative, or a 1-2 star one that reads positive."""
    if r.rating is None:
        return False
    return (r.rating >= 4 and r.label == "negative") or (r.rating <= 2 and r.label == "positive")


def by_product(db: Session, ws: uuid.UUID, limit: int = 30) -> list[dict[str, Any]]:
    names = {p.id: p.name for p in db.scalars(select(Product).where(Product.workspace_id == ws))}
    groups: dict[uuid.UUID, list[Review]] = defaultdict(list)
    for r in _load(db, ws):
        if r.product_id:
            groups[r.product_id].append(r)
    out = []
    for pid, rs in groups.items():
        themes = Counter(t["theme"] for r in rs for t in (r.themes or []) if t["polarity"] <= -0.15)
        out.append(
            {
                "product_id": str(pid), "product": names.get(pid, "?"), "reviews": len(rs),
                "mean_sentiment": round(sum(r.sentiment for r in rs) / len(rs), 3),
                "negative_pct": round(100 * sum(r.label == "negative" for r in rs) / len(rs), 1),
                "top_problem": themes.most_common(1)[0][0] if themes else None,
            }
        )  # fmt: skip
    return sorted(out, key=lambda x: float(x["mean_sentiment"] or 0))[:limit]


def list_reviews(
    db: Session, ws: uuid.UUID, *, label: str | None, theme: str | None, language: str | None,
    product_id: uuid.UUID | None, q: str | None, limit: int, offset: int,
) -> tuple[list[Review], int]:  # fmt: skip
    stmt = select(Review).where(Review.workspace_id == ws)
    if label:
        stmt = stmt.where(Review.label == label)
    if language:
        stmt = stmt.where(Review.language == language)
    if product_id:
        stmt = stmt.where(Review.product_id == product_id)
    if q:
        stmt = stmt.where(Review.text.ilike(f"%{q[:80]}%"))
    rows = list(
        db.scalars(stmt.order_by(Review.review_date.desc().nulls_last(), Review.created_at.desc()))
    )
    if theme:
        rows = [r for r in rows if any(t["theme"] == theme for t in (r.themes or []))]
    return rows[offset : offset + limit], len(rows)
