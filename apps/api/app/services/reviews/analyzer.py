"""Read one review: which language, how positive, and which themes it talks about.

No network and no downloaded model. Sentiment is a transparent word-score with negation,
intensifiers and "but" handling; themes come from the keyword lists in ``lexicon``. Every theme
carries the sentence it came from, so a shopkeeper can check the claim.
"""

import re
import unicodedata
from dataclasses import dataclass, field

from app.services.reviews import lexicon

VERSION = "lexicon-1"
NEG_LABEL, NEU_LABEL, POS_LABEL = "negative", "neutral", "positive"
THRESHOLD = 0.15

_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_LATIN = re.compile(r"[A-Za-z]")
_TOKEN = re.compile(r"[ऀ-ॿ]+|[a-z0-9']+")
_SENTENCE = re.compile(r"(?<=[.!?।\n])\s+|\s+(?:but|lekin|magar|however)\s+", re.I)
_REPEAT = re.compile(r"(.)\1{2,}")  # soooo -> soo
_EMOJI_POS = {"👍", "😍", "😊", "😀", "❤", "👌", "🙏", "⭐", "😁", "🥰"}
_EMOJI_NEG = {"👎", "😡", "😠", "😞", "😢", "🤮", "😤", "💔"}

# Hinglish spellings that differ only by vowels: fold them onto one form before matching.
_FOLD = str.maketrans({"w": "v"})


def normalise_token(tok: str) -> str:
    t = _REPEAT.sub(r"\1\1", tok.lower())
    return t


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text).lower()
    for phrase, token in lexicon.PHRASES.items():
        text = text.replace(phrase, token)
    return [normalise_token(t) for t in _TOKEN.findall(text)]


def detect_language(text: str) -> str:
    """'hi' (Devanagari), 'hinglish' (Hindi in Roman letters) or 'en'."""
    dev = len(_DEVANAGARI.findall(text))
    lat = len(_LATIN.findall(text))
    if dev and dev >= lat:
        return "hi"
    toks = [t for t in tokens(text) if _LATIN.search(t)]
    if not toks:
        return "hi" if dev else "en"
    hits = sum(1 for t in toks if t in lexicon.HINGLISH_MARKERS)
    # "to", "me", "the", "par" are also English words: require real evidence.
    strong = sum(
        1
        for t in toks
        if t in lexicon.HINGLISH_MARKERS
        and t not in {"to", "me", "the", "par", "late", "top", "kam", "dam", "do", "ka"}
    )
    if dev or strong >= 2 or (strong >= 1 and hits / len(toks) >= 0.25):
        return "hinglish"
    return "en"


@dataclass(slots=True)
class ThemeHit:
    theme: str
    polarity: float
    snippet: str

    def as_dict(self) -> dict[str, object]:
        return {"theme": self.theme, "polarity": round(self.polarity, 2), "snippet": self.snippet}


@dataclass(slots=True)
class Analysis:
    language: str
    sentiment: float
    label: str
    themes: list[ThemeHit] = field(default_factory=list)


_CLAUSE = re.compile(r"[,;.!?।\n]+|\s-\s")
# "nahi aaya", "not received": something that should have happened did not.
_RECEIPT = {
    "aaya",
    "aayi",
    "aaye",
    "mila",
    "mili",
    "hui",
    "hua",
    "pahuncha",
    "pahunchi",
    "received",
    "receive",
    "receiving",
    "deliver",
    "delivered",
    "arrived",
    "working",
    "come",
    "came",
    "milta",
    "मिला",
    "आया",
    "हुई",
    "पहुंचा",
}


def _score_clause(toks: list[str]) -> float:
    """Word weights with negation (stops at the next opinion word) and a preceding intensifier."""
    total = 0.0
    for i, t in enumerate(toks):
        w = lexicon.POS.get(t, 0.0) - lexicon.NEG.get(t, 0.0)
        if w == 0.0:
            if t in lexicon.NEGATORS and any(x in _RECEIPT for x in toks[i + 1 : i + 3]):
                total -= 2.0
            continue
        if i > 0 and toks[i - 1] in lexicon.INTENSIFIERS:
            w *= lexicon.INTENSIFIERS[toks[i - 1]]
        for x in reversed(toks[max(0, i - 3) : i]):
            if x in lexicon.POS or x in lexicon.NEG:
                break  # the negator belongs to an earlier opinion word
            if x in lexicon.NEGATORS:
                w = -0.8 * w  # "not good" is bad, but milder than "bad"
                break
        total += w
    return total


def _score_tokens(toks: list[str]) -> float:
    return _score_clause(toks)


def _score_text(text: str) -> float:
    return sum(_score_clause(tokens(c)) for c in _CLAUSE.split(text) if c.strip())


def _squash(x: float) -> float:
    """Map an open-ended score into -1..1 (a soft saturation, so long reviews do not dominate)."""
    return x / (abs(x) + 2.5)


def _emoji_score(text: str) -> float:
    return 0.8 * sum(c in _EMOJI_POS for c in text) - 0.8 * sum(c in _EMOJI_NEG for c in text)


def sentiment_score(text: str) -> float:
    """-1..1. After a contrast word ("but", "lekin") the later clause counts more."""
    parts = re.split(r"\b(?:but|however|lekin|magar|though)\b|लेकिन|मगर", text, flags=re.I)
    if len(parts) == 1:
        raw = _score_text(text)
    else:
        raw = sum(
            _score_text(p) * (1.6 if i == len(parts) - 1 else 1.0) for i, p in enumerate(parts)
        )
    return _squash(raw + _emoji_score(text))


def label_for(score: float) -> str:
    return POS_LABEL if score >= THRESHOLD else NEG_LABEL if score <= -THRESHOLD else NEU_LABEL


_SEGMENT = re.compile(
    r"[,;.!?।\n]+|\s-\s|\b(?:but|however|lekin|magar|though|and|aur)\b|लेकिन|मगर|और", re.I
)


def find_themes(text: str, max_snippet: int = 140) -> list[ThemeHit]:
    """One hit per theme. Polarity is read from the short phrase that mentions the theme."""
    hits: dict[str, ThemeHit] = {}
    for seg in (x.strip() for x in _SEGMENT.split(text) if x and x.strip()):
        toks = tokens(seg)
        pol = _squash(_score_clause(toks))
        words = set(toks)
        for key, spec in lexicon.THEMES.items():
            if not words & spec["words"]:  # type: ignore[operator]
                continue
            old = hits.get(key)
            if old is None or abs(pol) > abs(old.polarity):
                snip = seg if len(seg) <= max_snippet else seg[: max_snippet - 1].rstrip() + "…"
                hits[key] = ThemeHit(key, pol, snip)
    return list(hits.values())


def analyse(text: str) -> Analysis:
    text = (text or "").strip()
    score = sentiment_score(text)
    return Analysis(detect_language(text), round(score, 3), label_for(score), find_themes(text))
