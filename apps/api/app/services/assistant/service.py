"""Answer a question: route it, run one typed tool, write the reply from the tool's numbers."""

from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.workspace import Workspace, WorkspaceRole
from app.services.assistant import nlu, replies, tools
from app.services.docs import service as docs

SUGGESTIONS = {
    "en": ["Sales last week", "Why did sales drop?", "What should I order?", "Any alerts?"],
    "hinglish": [
        "Pichle hafte ki bikri",
        "Sales kyun gir gayi?",
        "Kya mangwana hai?",
        "Koi alert?",
    ],
    "hi": ["पिछले हफ्ते की बिक्री", "बिक्री क्यों गिरी?", "क्या मंगवाना है?", "कोई अलर्ट?"],
}


def _run(db: Session, ws: Workspace, u: nlu.Understood) -> tools.Result | None:
    i, p = u.intent, u.period
    if i == "sales":
        return tools.sales(db, ws, p)
    if i == "why":
        return tools.why(db, ws, p)
    if i in {"top_products", "slow_products"}:
        return tools.products(db, ws, p, u.top_n, slow=i == "slow_products")
    return {
        "customers": lambda: tools.customers(db, ws),
        "stock": lambda: tools.stock(db, ws),
        "dead_stock": lambda: tools.dead_stock(db, ws),
        "forecast": lambda: tools.forecast(db, ws),
        "alerts": lambda: tools.alerts(db, ws),
        "margin": lambda: tools.margin(db, ws, p),
        "supplier": lambda: tools.supplier(db, ws),
        "reviews": lambda: tools.review_summary(db, ws),
        "festival": lambda: tools.festivals(db, ws),
    }.get(i, lambda: None)()


# Words that signal "what do our own papers say" rather than "what do the numbers say".
DOC_CUES = {
    "policy", "policies", "rule", "rules", "terms", "allowed", "return", "returned", "refund", "exchange",
    "procedure", "sop", "niyam", "नियम", "limit", "due", "deadline", "leave", "salary", "checklist",
    "document", "documents", "contract", "agreement", "warranty", "guarantee",
}  # fmt: skip


def _from_documents(
    db: Session, ws: Workspace, role: WorkspaceRole, question: str, lang: str, base: dict[str, Any]
) -> dict[str, Any] | None:
    """Questions the numbers cannot answer may be answered by the shop's own documents."""
    try:
        r = docs.search(db, ws.id, role, question, 3)
    except Exception:  # model not available on this server: fall back to "not understood"
        return None
    if r["confidence"] == "none" or not r["answer"]:
        return None
    top = r["results"][0]
    cite = str(top["title"]) + (f", page {top['page']}" if top["page"] else "")
    if top["section"]:
        cite += f", {top['section']}"
    maybe = ""
    if r["confidence"] == "possible":
        maybe = {
            "en": "This may not answer it. ",
            "hinglish": "Shayad yeh jawab na ho. ",
            "hi": "शायद यह जवाब न हो। ",
        }[lang]
    return {
        **base, "intent": "documents", "answer": maybe + str(r["answer"]), "rows": [{"source": cite}],
        "link": "/app/documents", "note": None, "grounded": True, "source": "documents",
    }  # fmt: skip


def ask(
    db: Session,
    workspace: Workspace,
    question: str,
    role: WorkspaceRole = WorkspaceRole.VIEWER,
    today: date | None = None,
) -> dict[str, Any]:
    u = nlu.route(question, today or date.today())
    lang = u.language if u.language in replies.L else "en"
    base: dict[str, Any] = {
        "intent": u.intent, "language": lang, "question": question,
        "period": None if u.period is None else {"label": u.period.label, "start": u.period.start.isoformat(), "end": u.period.end.isoformat()},
        "suggestions": SUGGESTIONS[lang],
    }  # fmt: skip
    if u.intent not in {"help", "unknown"} and DOC_CUES & set(nlu.tokens(question)):
        found = _from_documents(db, workspace, role, question, lang, base)
        if found is not None and not found["answer"].startswith(
            ("This may not", "Shayad yeh", "शायद यह")
        ):
            return found  # a confident match in the shop's own papers wins over a keyword guess
    if u.intent == "help":
        return {
            **base,
            "answer": replies.HELP[lang],
            "rows": [],
            "link": None,
            "note": None,
            "grounded": False,
        }
    if u.intent == "unknown":
        found = _from_documents(db, workspace, role, question, lang, base)
        if found is not None:
            return found
        return {
            **base,
            "answer": replies.UNKNOWN[lang] + replies.HELP[lang],
            "rows": [],
            "link": None,
            "note": None,
            "grounded": False,
        }
    res = _run(db, workspace, u)
    if res is None or res.empty:
        hint = replies.EMPTY_HINT.get(u.intent)
        text = replies.EMPTY[lang] + (
            hint[replies.L.index(lang)] if hint else (res.note if res and res.note else "")
        )
        return {**base, "answer": text, "rows": [],
                "link": res.link if res else None, "note": None, "grounded": True}  # fmt: skip
    answer = replies.BUILD[u.intent](lang, res)
    return {
        **base,
        "answer": answer.strip(),
        "rows": res.rows,
        "link": res.link,
        "note": res.note,
        "grounded": True,
    }
