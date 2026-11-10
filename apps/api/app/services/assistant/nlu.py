"""Understand a short business question in English, Hindi or Hinglish.

Rule-based on purpose: every decision is a visible keyword or pattern, so a wrong answer can be
traced and fixed, and no model download or network call is needed. A question that matches no
intent is answered with what the assistant can do, never with a guess.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.services.reviews.analyzer import detect_language

_TOKEN = re.compile(r"[ऀ-ॿ]+|[a-z0-9]+")

INTENTS: dict[str, set[str]] = {
    "sales": {
        "sell",
        "sales",
        "sale",
        "revenue",
        "turnover",
        "sold",
        "selling",
        "bikri",
        "becha",
        "bika",
        "bikta",
        "kamai",
        "income",
        "business",
        "बिक्री",
        "बेचा",
        "कमाई",
        "कारोबार",
        "धंधा",
        "dhanda",
        "kitna",
    },
    "why": {
        "why",
        "reason",
        "cause",
        "drop",
        "dropped",
        "fall",
        "fell",
        "decline",
        "declined",
        "down",
        "kyun",
        "kyu",
        "kyon",
        "gir",
        "gira",
        "girawat",
        "kam",
        "क्यों",
        "गिरावट",
        "गिरी",
        "कम",
        "wajah",
        "वजह",
        "karan",
        "कारण",
    },
    "top_products": {
        "top",
        "best",
        "bestseller",
        "bestsellers",
        "popular",
        "sabse",
        "zyada",
        "jyada",
        "highest",
        "सबसे",
        "ज्यादा",
        "टॉप",
        "बेस्ट",
        "chalta",
        "chalne",
    },
    "slow_products": {
        "slow",
        "worst",
        "least",
        "lowest",
        "bottom",
        "weak",
        "dead",
        "kam",
        "nahi",
        "सुस्त",
        "dhimi",
        "dheeme",
        "धीमे",
    },
    "customers": {
        "customer",
        "customers",
        "regulars",
        "regular",
        "grahak",
        "gaahak",
        "lapsed",
        "churn",
        "repeat",
        "loyal",
        "ग्राहक",
        "ग्राहकों",
        "gone",
        "quiet",
        "wapas",
        "वापस",
    },
    "stock": {
        "stock",
        "reorder",
        "order",
        "restock",
        "inventory",
        "mangwana",
        "mangwao",
        "maal",
        "माल",
        "स्टॉक",
        "ऑर्डर",
        "mangana",
        "khatam",
        "shortage",
        "runout",
        "out",
        "kitna",
    },
    "dead_stock": {
        "dead",
        "overstock",
        "stuck",
        "fasa",
        "unsold",
        "excess",
        "फंसा",
        "paisa",
    },
    "forecast": {
        "forecast",
        "predict",
        "prediction",
        "expect",
        "expected",
        "next",
        "future",
        "tomorrow",
        "agle",
        "agla",
        "aane",
        "anumaan",
        "अनुमान",
        "अगले",
        "bikega",
        "bikenge",
        "hoga",
        "होगी",
    },
    "alerts": {
        "alert",
        "alerts",
        "problem",
        "problems",
        "issue",
        "issues",
        "attention",
        "dhyan",
        "worry",
        "wrong",
        "dikkat",
        "समस्या",
        "ध्यान",
        "चेतावनी",
        "khabar",
    },
    "margin": {
        "margin",
        "margins",
        "profit",
        "profits",
        "munafa",
        "nafa",
        "leak",
        "leaks",
        "fayda",
        "मुनाफा",
        "मुनाफ़ा",
        "फायदा",
        "gross",
    },
    "supplier": {
        "supplier",
        "suppliers",
        "purchase",
        "bill",
        "bills",
        "vendor",
        "wholesaler",
        "costlier",
        "mehenga",
        "mahanga",
        "महंगा",
        "सप्लायर",
        "kharid",
        "खरीद",
    },
    "reviews": {
        "review",
        "reviews",
        "complaint",
        "complaints",
        "feedback",
        "rating",
        "ratings",
        "shikayat",
        "शिकायत",
        "रिव्यू",
    },
    "festival": {
        "festival",
        "festivals",
        "diwali",
        "holi",
        "eid",
        "ipl",
        "cricket",
        "tyohar",
        "tyauhar",
        "त्योहार",
        "दिवाली",
        "होली",
        "navratri",
        "onam",
        "pongal",
        "durga",
        "raksha",
    },
    "help": {"help", "madad", "मदद", "hello", "hi", "hey", "namaste", "नमस्ते"},
}

INTENTS["udhaar"] = {
    "udhaar",
    "udhar",
    "baaki",
    "bakaya",
    "dues",
    "owe",
    "owed",
    "owes",
    "outstanding",
    "receivable",
    "receivables",
    "उधार",
    "बकाया",
    "बाकी",
    "khata",
    "खाता",
    "lena",
    "dena",
}

INTENTS["recommend"] = {
    "recommend",
    "recommendation",
    "recommendations",
    "suggest",
    "suggestion",
    "suggestions",
    "advice",
    "advise",
    "todo",
    "priorities",
    "priority",
    "sujhav",
    "salah",
    "सुझाव",
    "सलाह",
}

INTENTS["pricing"] = {
    "discount",
    "discounts",
    "promotion",
    "promotions",
    "promo",
    "pricing",
    "chhoot",
    "chhut",
    "छूट",
    "डिस्काउंट",
}

INTENTS["goals"] = {"goal", "goals", "target", "targets", "lakshya", "लक्ष्य", "tark"}

# Hindi (Devanagari) forms added after the first evaluation run.
INTENTS["stock"] |= {"मंगवाना", "मंगवाओ", "मंगाना", "मंगवाएं"}
INTENTS["alerts"] |= {"अलर्ट", "अलर्ट्स"}
INTENTS["margin"] |= {"मार्जिन"}
INTENTS["slow_products"] |= {"least"}

# Phrases that outweigh single keywords.
PHRASES: list[tuple[str, str]] = [
    (
        r"dead\s*stock|overstock|paisa\s+fas|stuck\s+(?:stock|money|cash)|not\s+selling",
        "dead_stock",
    ),
    (r"(?:what|kya|kitna)\s+(?:should\s+i\s+|to\s+)?(?:order|mangwa|mangana|reorder)", "stock"),
    (r"run(?:ning)?\s+out|stock\s*out|khatam\s+ho", "stock"),
    (
        r"why\s+(?:did|are|is|have)|kyun\s+gir|kyu\s+gir|kyon\s+gir|क्यों\s+गिर|sales?\s+(?:drop|down|fell)",
        "why",
    ),
    (
        r"top\s*\d*\s*(?:selling\s+)?products?|best\s*sell|sabse\s+(?:zyada|jyada)\s+bik|सबसे\s+ज्यादा\s+बिक",
        "top_products",
    ),
    (
        r"slow\s*(?:moving|sellers?)|sabse\s+kam\s+bik|least\s+sell|worst\s+products?",
        "slow_products",
    ),
    (r"lapsed|gone\s+quiet|churn|wapas\s+nahi|not\s+(?:come|visit)", "customers"),
    (
        r"next\s+(?:week|month|\d+\s+days?|14)|agle\s+(?:hafte|hafta|mahine|\d+\s+din)|अगले",
        "forecast",
    ),
    (
        r"price\s+(?:rise|hike|increase)|cost\s+(?:rise|increase|went\s+up)|mehenga\s+(?:hua|ho\s+gaya)",
        "supplier",
    ),
    (r"what\s+can\s+you|help\s+me|kya\s+kar\s+sakte|मदद", "help"),
    (r"complain|shikayat|शिकायत", "reviews"),
    (r"sell\s+least|least\s+sell|sell\s+the\s+least", "slow_products"),
]
PHRASES.append(
    (
        r"did\s+(?:my\s+)?(?:discounts?|offers?)|discounts?\s+(?:work|pay|help)|worth\s+discount|raise\s+my\s+prices?|safe\s+to\s+(?:raise|increase)|discount\s+se\s+fayda|chhoot\s+se\s+fayda",
        "pricing",
    )
)
PHRASES.append(
    (
        r"on\s+track|hit\s+my\s+(?:target|goal)|reach\s+my\s+(?:target|goal)|will\s+i\s+(?:reach|hit|make)|target\s+poora|goal\s+poora|lakshya\s+poora|लक्ष्य",
        "goals",
    )
)
PHRASES.append(
    (
        r"what\s+(?:should|do)\s+i\s+do|what\s+to\s+do|next\s+steps?|this\s+week.{0,12}(?:do|focus)|kya\s+kar(?:na|u|oon)\s+(?:chahiye|hai)|क्या\s+करना\s+चाहिए",
        "recommend",
    )
)
PHRASES.append(
    (
        r"who\s+owes|owe\s+me|paisa\s+(?:lena|dena)|kitna\s+(?:baaki|udhaar|udhar)|pending\s+(?:money|payments?)|ने\s+उधार|किसका\s+(?:बाकी|उधार)",
        "udhaar",
    )
)

MONTHS = {
    m: i for i, names in enumerate(
        [("jan", "january", "janvari", "जनवरी"), ("feb", "february", "farvari", "फरवरी"),
         ("mar", "march", "march", "मार्च"), ("apr", "april", "april", "अप्रैल"),
         ("may", "may", "mai", "मई"), ("jun", "june", "june", "जून"),
         ("jul", "july", "julai", "जुलाई"), ("aug", "august", "agast", "अगस्त"),
         ("sep", "september", "sitambar", "सितंबर"), ("oct", "october", "october", "अक्टूबर"),
         ("nov", "november", "navambar", "नवंबर"), ("dec", "december", "disambar", "दिसंबर")], 1
    ) for m in names
}  # fmt: skip


@dataclass(slots=True)
class Period:
    start: date
    end: date
    label: str  # "last 7 days", "October 2026"
    explicit: bool = True  # False when we defaulted because the user named no period


@dataclass(slots=True)
class Understood:
    intent: str
    language: str
    period: Period | None
    product_text: str | None = None
    top_n: int = 5
    scores: dict[str, float] = field(default_factory=dict)


def tokens(text: str) -> list[str]:
    t = unicodedata.normalize("NFC", text).lower()
    return _TOKEN.findall(t)


def _month_range(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    return start, nxt - timedelta(days=1)


def find_period(text: str, today: date, intent: str) -> Period | None:
    t = unicodedata.normalize("NFC", text).lower()
    toks = set(tokens(t))

    def p(a: date, b: date, label: str) -> Period:
        return Period(a, b, label)

    m = re.search(
        r"(?:last|past|pichhle|pichle|pichhla|पिछले)\s*(\d{1,3})\s*(?:days?|din|दिन)", t
    ) or re.search(r"(\d{1,3})\s*(?:days?|din|दिन)", t)
    if m and 1 <= int(m[1]) <= 366:
        n = int(m[1])
        return p(today - timedelta(days=n - 1), today, f"last {n} days")
    if re.search(r"(?:last|past|pichhle|pichle|पिछले)\s+(?:week|hafte|hafta|हफ्ते|सप्ताह)", t):
        mon = today - timedelta(days=today.weekday() + 7)
        return p(mon, mon + timedelta(days=6), "last week")
    if re.search(r"(?:this|is|इस)\s+(?:week|hafte|hafta|हफ्ते|सप्ताह)", t):
        return p(today - timedelta(days=today.weekday()), today, "this week")
    if re.search(r"(?:last|past|pichhle|pichle|पिछले)\s+(?:month|mahine|mahina|महीने)", t):
        first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        a, b = _month_range(first.year, first.month)
        return p(a, b, f"{a:%B %Y}")
    if re.search(r"(?:this|is|इस)\s+(?:month|mahine|mahina|महीने)", t):
        return p(today.replace(day=1), today, f"{today:%B %Y} so far")
    if re.search(r"(?:this|is|इस)\s+(?:year|saal|sal|साल)|year\s+to\s+date|ytd", t):
        return p(date(today.year, 1, 1), today, f"{today.year} so far")
    if toks & {"yesterday", "kal", "कल"} and intent not in {"forecast"}:
        d = today - timedelta(days=1)
        return p(d, d, "yesterday")
    if toks & {"today", "aaj", "आज"}:
        return p(today, today, "today")
    for tok in toks:
        if (tok in MONTHS and len(tok) >= 3 and tok not in {"may", "mar"}) or (
            tok in {"may", "mar"} and re.search(rf"\b(?:in|of|for|ka|ke)\s+{tok}\b", t)
        ):
            ym = re.search(r"\b(20\d{2})\b", t)
            mo = MONTHS[tok]
            yr = int(ym[1]) if ym else (today.year if mo <= today.month else today.year - 1)
            a, b = _month_range(yr, mo)
            return p(a, b, f"{a:%B %Y}")
    return None


def _top_n(t: str) -> int:
    m = re.search(r"\btop\s*(\d{1,2})\b|\b(\d{1,2})\s*(?:best|top|products)", t)
    n = int(next(g for g in (m[1], m[2]) if g)) if m else 5
    return max(1, min(n, 15))


def route(text: str, today: date) -> Understood:
    t = unicodedata.normalize("NFC", text).lower().strip()
    toks = tokens(t)
    scores: dict[str, float] = {}
    for intent, words in INTENTS.items():
        s = float(sum(1 for w in toks if w in words))
        if s:
            scores[intent] = s
    for pat, intent in PHRASES:
        if re.search(pat, t):
            scores[intent] = scores.get(intent, 0) + 3.0
    if scores.get("festival"):
        scores["festival"] += 1.5  # "Diwali ke liye kya stock" is about the festival
    # words that only make sense with a partner intent
    if "why" in scores and "sales" not in scores and scores["why"] < 3:
        scores.pop("why")
    if not scores or max(scores.values()) < 1:
        intent = "help" if len(toks) <= 2 and scores.get("help") else "unknown"
    else:
        # keywords shared across intents ("kitna", "kam") should not win alone
        weak = {"kitna", "kam", "out", "next", "order", "what", "can", "kya", "hi"}
        solid = {
            k: v - 0.5 * sum(1 for w in toks if w in weak and w in INTENTS[k])
            for k, v in scores.items()
        }
        intent = max(solid, key=lambda k: (solid[k], k != "help"))
        if solid[intent] <= 0:
            intent = "unknown"
    lang = detect_language(text)
    period = find_period(t, today, intent)
    return Understood(intent, lang, period, None, _top_n(t), scores)
