"""Hindi product names spoken to a shop whose catalogue is in English.

A shopkeeper says "चावल" or "बासमती राइस"; the catalogue says "Basmati Rice 5 kg". Two helps:

1. a glossary of everyday retail words (चावल -> rice, आटा -> atta, चीनी -> sugar ...);
2. a rough Devanagari -> Roman spelling, compared with catalogue words by *sound class* (vowels dropped, look-alike
   consonants merged), so "बासमती" meets "Basmati" and "राइस" meets "Rice".

It only ever proposes candidates; the page shows what it understood and the person confirms.
"""

import re
import unicodedata

GLOSSARY = {
    "चावल": "rice", "आटा": "atta", "आटे": "atta", "गेहूं": "wheat", "गेहूँ": "wheat", "दाल": "dal", "चीनी": "sugar",
    "शक्कर": "sugar", "नमक": "salt", "तेल": "oil", "घी": "ghee", "दूध": "milk", "साबुन": "soap", "चाय": "tea",
    "बिस्कुट": "biscuit", "बिस्किट": "biscuit", "मसाला": "masala", "हल्दी": "turmeric", "मिर्च": "chilli",
    "जीरा": "jeera", "पनीर": "paneer", "दही": "curd", "मक्खन": "butter", "चना": "chana", "मूंग": "moong",
    "राजमा": "rajma", "शैम्पू": "shampoo", "शैंपू": "shampoo", "टूथपेस्ट": "toothpaste", "पोहा": "poha",
    "सूजी": "suji", "रवा": "rava", "बेसन": "besan", "मैदा": "maida", "सरसों": "mustard", "कॉफी": "coffee",
    "कॉफ़ी": "coffee", "नूडल्स": "noodles", "मैगी": "maggi", "जूस": "juice", "पानी": "water", "अचार": "pickle",
    "मूंगफली": "peanut", "काजू": "cashew", "बादाम": "almond", "किशमिश": "raisin", "गुड़": "jaggery",
}  # fmt: skip

_CONS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "n", "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "n",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n", "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m", "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h",
}  # fmt: skip
_VOWEL = {
    "अ": "a",
    "आ": "aa",
    "इ": "i",
    "ई": "ee",
    "उ": "u",
    "ऊ": "oo",
    "ऋ": "ri",
    "ए": "e",
    "ऐ": "ai",
    "ओ": "o",
    "औ": "au",
    "ऑ": "o",
}
_MATRA = {
    "ा": "aa",
    "ि": "i",
    "ी": "ee",
    "ु": "u",
    "ू": "oo",
    "े": "e",
    "ै": "ai",
    "ो": "o",
    "ौ": "au",
    "ॉ": "o",
    "ृ": "ri",
}
_NUKTA = {"ड": "r", "ढ": "rh", "फ": "f", "ज": "z", "ख": "kh", "ग": "g", "क": "k"}


def has_devanagari(text: str) -> bool:
    return bool(re.search(r"[ऀ-ॿ]", text))


def to_roman(word: str) -> str:
    """A rough, readable Roman spelling of a Devanagari word (not a standard scheme)."""
    w = unicodedata.normalize("NFD", word)
    out: list[str] = []
    i, n = 0, len(w)
    while i < n:
        c = w[i]
        nxt = w[i + 1] if i + 1 < n else ""
        if c in _CONS:
            base = _NUKTA.get(c, _CONS[c]) if nxt == "़" else _CONS[c]
            if nxt == "़":
                i += 1
                nxt = w[i + 1] if i + 1 < n else ""
            out.append(base)
            if nxt in _MATRA:
                out.append(_MATRA[nxt])
                i += 1
            elif nxt == "्":
                i += 1  # virama: no vowel
            elif i + 1 < n and w[i + 1] not in "ंँः":
                out.append("a")  # inherent vowel inside the word; dropped at the end
        elif c in _VOWEL:
            out.append(_VOWEL[c])
        elif c in "ंँ":
            out.append("n")
        elif c == "ः":
            out.append("h")
        i += 1
    return "".join(out)


def sound_class(word: str) -> str:
    """Latin word reduced to its consonant skeleton with look-alike sounds merged: rice ~ राइस ~ rais."""
    w = re.sub(r"[^a-z]", "", word.lower())
    w = (
        w.replace("ph", "p")
        .replace("f", "p")
        .replace("kh", "k")
        .replace("gh", "g")
        .replace("th", "t")
    )
    w = (
        w.replace("dh", "d")
        .replace("bh", "b")
        .replace("jh", "j")
        .replace("sh", "s")
        .replace("chh", "c")
        .replace("ch", "c")
    )
    w = (
        re.sub(r"c(?=[eiy])", "s", w)
        .replace("c", "k")
        .replace("q", "k")
        .replace("x", "ks")
        .replace("z", "s")
        .replace("w", "v")
    )
    w = re.sub(r"[aeiouy]", "", w)
    return re.sub(r"(.)\1+", r"\1", w)


def expand(text: str) -> tuple[set[str], set[str]]:
    """(English words, sound classes) the Devanagari words in `text` stand for. Both empty for plain Latin text."""
    words: set[str] = set()
    sounds: set[str] = set()
    for tok in re.findall(r"[ऀ-ॿ]+", unicodedata.normalize("NFC", text)):
        if tok in GLOSSARY:
            words.add(GLOSSARY[tok])
        r = to_roman(tok)
        if len(r) >= 3:
            sounds.add(sound_class(r))
    return words, {s for s in sounds if len(s) >= 2}
