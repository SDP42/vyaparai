"""Split blocks into passages of about 90-170 words that keep their page and heading.

Short blocks under the same heading are merged so a rule and its exception stay together; long
blocks are cut at sentence ends with a small overlap so an answer that spans a cut is not lost.
"""

import re
from dataclasses import dataclass

from app.services.docs.extract import Block

TARGET_WORDS = 130
MAX_WORDS = 190
OVERLAP_WORDS = 25
_SENT = re.compile(r"(?<=[.!?।])\s+")


@dataclass(slots=True)
class Chunk:
    text: str
    page: int | None
    section: str | None


def _words(s: str) -> int:
    return len(s.split())


def _split_long(text: str) -> list[str]:
    sents = [s for s in _SENT.split(text) if s.strip()]
    out: list[str] = []
    cur: list[str] = []
    for s in sents:
        if cur and _words(" ".join([*cur, s])) > MAX_WORDS:
            out.append(" ".join(cur))
            tail = " ".join(" ".join(cur).split()[-OVERLAP_WORDS:])
            cur = [tail, s] if tail else [s]
        else:
            cur.append(s)
    if cur:
        out.append(" ".join(cur))
    return out


def chunk(blocks: list[Block]) -> list[Chunk]:
    out: list[Chunk] = []
    cur: list[str] = []
    cur_key: tuple[int | None, str | None] | None = None

    def flush() -> None:
        nonlocal cur, cur_key
        if cur and cur_key is not None:
            body = "\n".join(cur)
            # the heading travels with the passage: it is context for both search and the reader
            head = cur_key[1]
            out.append(Chunk(f"{head}\n{body}" if head else body, cur_key[0], head))
        cur, cur_key = [], None

    for b in blocks:
        key = (b.page, b.heading)
        pieces = _split_long(b.text) if _words(b.text) > MAX_WORDS else [b.text]
        for piece in pieces:
            same = cur_key is not None and cur_key[1] == key[1]
            if cur and (not same or _words("\n".join([*cur, piece])) > TARGET_WORDS):
                flush()
            if cur_key is None:
                cur_key = key
            cur.append(piece)
    flush()
    return out
