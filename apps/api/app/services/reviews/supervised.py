"""Learn this shop's own words from its star ratings (numpy logistic regression, no downloads).

The word lists miss shop-specific and spelling-variant words. If a workspace has enough reviews
with stars, we fit a small model on 4-5 stars (positive) against 1-2 stars (negative) and use it
where the lexicon has no opinion. The fit is checked on reviews it did not train on; if it is no
better than guessing it is not used.
"""

import hashlib
from dataclasses import dataclass
from itertools import pairwise

import numpy as np

from app.services.reviews import analyzer

MIN_RATED = 100
MIN_PER_CLASS = 25
DIM = 2048  # hashed features: no vocabulary file to store, and unseen words just land somewhere
MIN_ACCURACY = 0.7


def _features(text: str) -> np.ndarray:
    toks = analyzer.tokens(text)
    grams = toks + [f"{a}_{b}" for a, b in pairwise(toks)]
    v = np.zeros(DIM, dtype=np.float32)
    for g in grams:
        h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=4).digest(), "little")
        v[h % DIM] += 1.0
    n = np.linalg.norm(v)
    return v / n if n else v


@dataclass(slots=True)
class Model:
    w: np.ndarray
    b: float
    holdout_accuracy: float
    trained_on: int

    def score(self, text: str) -> float:
        """-1..1 (2p - 1)."""
        z = float(_features(text) @ self.w + self.b)
        return float(2.0 / (1.0 + np.exp(-z)) - 1.0)


def fit(texts: list[str], ratings: list[int | None], seed: int = 7) -> Model | None:
    """Train on 4-5 vs 1-2 stars. Returns None when there is too little data or it does not help."""
    xs, ys = [], []
    for t, r in zip(texts, ratings, strict=True):
        if r is None or r == 3:
            continue
        xs.append(_features(t))
        ys.append(1.0 if r >= 4 else 0.0)
    if len(ys) < MIN_RATED or min(sum(ys), len(ys) - sum(ys)) < MIN_PER_CLASS:
        return None
    x, y = np.vstack(xs), np.array(ys, dtype=np.float32)
    rng = np.random.default_rng(seed)
    idx = rng.permutation(len(y))
    cut = int(0.8 * len(y))
    tr, te = idx[:cut], idx[cut:]
    w, b = _gd(x[tr], y[tr])
    acc = float((((x[te] @ w + b) > 0) == (y[te] > 0.5)).mean())
    base = max(float(y[te].mean()), 1 - float(y[te].mean()))
    if acc < MIN_ACCURACY or acc <= base:
        return None
    w, b = _gd(x, y)  # final model sees everything
    return Model(w, b, round(acc, 3), len(y))


def _gd(
    x: np.ndarray, y: np.ndarray, epochs: int = 300, lr: float = 1.0, l2: float = 1e-3
) -> tuple[np.ndarray, float]:
    w = np.zeros(x.shape[1], dtype=np.float32)
    b = 0.0
    n = len(y)
    for _ in range(epochs):
        p = 1.0 / (1.0 + np.exp(-(x @ w + b)))
        g = p - y
        w -= lr * (x.T @ g / n + l2 * w)
        b -= lr * float(g.mean())
    return w, b


def blend(lexicon_score: float, model: Model | None, text: str) -> float:
    """Trust the word lists where they have an opinion; let the shop's model fill the gaps."""
    if model is None:
        return lexicon_score
    m = model.score(text)
    if lexicon_score == 0.0:
        return 0.8 * m
    return 0.65 * lexicon_score + 0.35 * m
