"""Numbers as people say them: "पचास", "डेढ़ सौ", "do hazaar paanch sau", "twelve thousand five hundred".

Speech recognition may return digits or words, in Devanagari, Roman Hinglish or English. This reads all of them,
including the Indian forms (lakh, crore) and the fractions shopkeepers use (डेढ़ 1.5, ढाई 2.5, सवा +0.25, साढ़े +0.5).
Only whole numbers up to a crore-crore range are returned; anything it cannot read is left alone.
"""

import re

_HINDI_0_100 = [
    "शून्य",
    "एक",
    "दो",
    "तीन",
    "चार",
    "पाँच",
    "छह",
    "सात",
    "आठ",
    "नौ",
    "दस",
    "ग्यारह",
    "बारह",
    "तेरह",
    "चौदह",
    "पंद्रह",
    "सोलह",
    "सत्रह",
    "अठारह",
    "उन्नीस",
    "बीस",
    "इक्कीस",
    "बाईस",
    "तेईस",
    "चौबीस",
    "पच्चीस",
    "छब्बीस",
    "सत्ताईस",
    "अट्ठाईस",
    "उनतीस",
    "तीस",
    "इकतीस",
    "बत्तीस",
    "तैंतीस",
    "चौंतीस",
    "पैंतीस",
    "छत्तीस",
    "सैंतीस",
    "अड़तीस",
    "उनतालीस",
    "चालीस",
    "इकतालीस",
    "बयालीस",
    "तैंतालीस",
    "चवालीस",
    "पैंतालीस",
    "छियालीस",
    "सैंतालीस",
    "अड़तालीस",
    "उनचास",
    "पचास",
    "इक्यावन",
    "बावन",
    "तिरेपन",
    "चौवन",
    "पचपन",
    "छप्पन",
    "सत्तावन",
    "अट्ठावन",
    "उनसठ",
    "साठ",
    "इकसठ",
    "बासठ",
    "तिरसठ",
    "चौंसठ",
    "पैंसठ",
    "छियासठ",
    "सड़सठ",
    "अड़सठ",
    "उनहत्तर",
    "सत्तर",
    "इकहत्तर",
    "बहत्तर",
    "तिहत्तर",
    "चौहत्तर",
    "पचहत्तर",
    "छिहत्तर",
    "सतहत्तर",
    "अठहत्तर",
    "उनासी",
    "अस्सी",
    "इक्यासी",
    "बयासी",
    "तिरासी",
    "चौरासी",
    "पचासी",
    "छियासी",
    "सत्तासी",
    "अट्ठासी",
    "नवासी",
    "नब्बे",
    "इक्यानवे",
    "बानवे",
    "तिरानवे",
    "चौरानवे",
    "पंचानवे",
    "छियानवे",
    "सत्तानवे",
    "अट्ठानवे",
    "निन्यानवे",
    "सौ",
]

WORDS: dict[str, float] = {w: float(i) for i, w in enumerate(_HINDI_0_100) if w != "सौ"}
# common spelling variants (speech recognition does not agree with itself)
WORDS.update(
    {"पांच": 5, "छः": 6, "छे": 6, "छ": 6, "पंद्रा": 15, "पन्द्रह": 15, "सताईस": 27, "अठाईस": 28, "पैतीस": 35, "पैंतिस": 35,
     "चौतीस": 34, "तेंतीस": 33, "सैतीस": 37, "अठतीस": 38, "पैंतालिस": 45, "अट्ठारह": 18, "बाइस": 22, "तेइस": 23}
)  # fmt: skip

ROMAN = [
    "zero",
    "ek",
    "do",
    "teen",
    "char",
    "paanch",
    "panch",
    "chhe",
    "che",
    "saat",
    "aath",
    "nau",
    "das",
    "gyarah",
    "barah",
    "terah",
    "chaudah",
    "pandrah",
    "solah",
    "satrah",
    "atharah",
    "unnis",
    "bees",
    "pachchis",
    "tees",
    "chalis",
    "pachas",
    "saath",
    "sattar",
    "assi",
    "nabbe",
]
_ROMAN_VALUES = [
    0,
    1,
    2,
    3,
    4,
    5,
    5,
    6,
    6,
    7,
    8,
    9,
    10,
    11,
    12,
    13,
    14,
    15,
    16,
    17,
    18,
    19,
    20,
    25,
    30,
    40,
    50,
    60,
    70,
    80,
    90,
]
WORDS.update({w: float(v) for w, v in zip(ROMAN, _ROMAN_VALUES, strict=True)})

ENGLISH = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
]
WORDS.update({w: float(i) for i, w in enumerate(ENGLISH)})
WORDS.update(
    {"thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
)

MULTIPLIERS: dict[str, int] = {
    "सौ": 100, "सो": 100, "sau": 100, "so": 100, "hundred": 100,
    "हज़ार": 1000, "हजार": 1000, "hazaar": 1000, "hazar": 1000, "thousand": 1000,
    "लाख": 100_000, "lakh": 100_000, "lac": 100_000, "lakhs": 100_000,
    "करोड़": 10_000_000, "करोड": 10_000_000, "crore": 10_000_000, "karod": 10_000_000, "million": 1_000_000,
}  # fmt: skip
SPECIAL = {"डेढ़": 1.5, "डेढ": 1.5, "dedh": 1.5, "ढाई": 2.5, "dhai": 2.5, "adhai": 2.5}
QUARTER = {"सवा", "sava", "sawa"}
HALF = {"साढ़े", "साढे", "saade", "sade", "saadhe"}

_TOKEN = re.compile(r"[ऀ-ॿ]+|[a-z]+|\d+(?:\.\d+)?", re.IGNORECASE)


def _is_number_token(t: str) -> bool:
    return (
        t in WORDS
        or t in MULTIPLIERS
        or t in SPECIAL
        or t in QUARTER
        or t in HALF
        or bool(re.fullmatch(r"\d+(?:\.\d+)?", t))
    )


def parse(text: str) -> list[tuple[int, int, int]]:
    """Every number in the text as (first token, last token + 1, value), reading words and digits."""
    toks = [t.lower() for t in _TOKEN.findall(text)]
    out: list[tuple[int, int, int]] = []
    i = 0
    while i < len(toks):
        if not _is_number_token(toks[i]) or (
            toks[i] in {"so", "do", "das", "char", "one", "che", "bees", "tees"}
            and not _near_number(toks, i)
        ):
            i += 1
            continue
        j, total, current = i, 0.0, 0.0
        pending = 0.0
        quarter_open = False
        while j < len(toks) and _is_number_token(toks[j]):
            t = toks[j]
            if t in HALF:
                pending = 0.5
            elif t in QUARTER:
                pending = 0.25
                quarter_open = True
            elif t in SPECIAL:
                current += SPECIAL[t]
            elif t in MULTIPLIERS:
                m = MULTIPLIERS[t]
                if quarter_open and current == 0:
                    current = 1 + pending
                    pending = 0.0
                    quarter_open = False
                if m >= 1000:
                    total += (current or 1) * m
                    current = 0.0
                else:
                    current = (current or 1) * m
            elif t in WORDS:
                current += WORDS[t] + pending
                pending = 0.0
            else:
                current += float(t) + pending
                pending = 0.0
            j += 1
        out.append((i, j, round(total + current)))
        i = j
    return out


def _near_number(toks: list[str], i: int) -> bool:
    """Short words that are also ordinary words (so, do, one) only count next to another number word or digit."""
    around = [toks[k] for k in (i - 1, i + 1) if 0 <= k < len(toks)]
    return any(
        a in MULTIPLIERS or a in WORDS or re.fullmatch(r"\d+", a) for a in around if a != toks[i]
    )


def first(text: str) -> int | None:
    found = parse(text)
    return found[0][2] if found else None
