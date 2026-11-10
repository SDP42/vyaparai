"""Keyword ranking (Okapi BM25) that works for English, Hindi and Hinglish text.

Dense embeddings miss exact things like "GSTR-3B", "Rs 15,000" or a product code; keywords find
them. Written here in about forty lines so there is no dependency to audit.
"""

import math
import re
import unicodedata
from collections import Counter

_TOKEN = re.compile(r"[ऀ-ॿ]+|[a-z0-9]+")
STOP = {
    "the", "a", "an", "of", "to", "is", "are", "was", "were", "in", "on", "for", "and", "or", "it",
    "do", "does", "how", "what", "when", "which", "who", "can", "i", "we", "my", "be", "at", "by",
    "ka", "ki", "ke", "ko", "se", "hai", "hain", "me", "mein", "kya", "kab", "kitna", "kitne",
    "है", "हैं", "का", "की", "के", "को", "से", "में", "क्या", "कब", "पर", "और",
}  # fmt: skip


def tokenize(text: str) -> list[str]:
    t = unicodedata.normalize("NFC", text).lower()
    out = []
    for tok in _TOKEN.findall(t):
        if tok in STOP:
            continue
        if len(tok) > 4 and tok.isascii() and tok.isalpha():  # crude plural / -ing folding
            for suf in ("ing", "es", "s"):
                if tok.endswith(suf) and len(tok) - len(suf) >= 3:
                    tok = tok[: -len(suf)]
                    break
        out.append(tok)
    return out


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.4, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.len = [len(d) for d in docs]
        self.avg = (sum(self.len) / len(self.len)) if docs else 0.0
        df: Counter[str] = Counter()
        for c in self.tf:
            df.update(c.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for tf, ln in zip(self.tf, self.len, strict=True):
            s = 0.0
            for q in query:
                f = tf.get(q)
                if f:
                    s += (
                        self.idf.get(q, 0.0)
                        * f
                        * (self.k1 + 1)
                        / (f + self.k1 * (1 - self.b + self.b * ln / (self.avg or 1)))
                    )
            out.append(s)
        return out
