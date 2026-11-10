"""Answer a question: route it, run one typed tool, write the reply from the tool's numbers."""

import time
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.commerce import Product
from app.models.workspace import Workspace, WorkspaceRole
from app.services.assistant import evidence, nlu, replies, tools
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


def _run(
    db: Session, ws: Workspace, u: nlu.Understood, product: Product | None = None
) -> tools.Result | None:
    i, p = u.intent, u.period
    if product is not None and i == "product_sales":
        return tools.product_sales(db, ws, p, product)
    if product is not None and i == "product_stock":
        return tools.product_stock(db, ws, product)
    if product is not None and i == "product_forecast":
        return tools.product_forecast(db, ws, product)
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
        "udhaar": lambda: tools.udhaar(db, ws),
        "recommend": lambda: tools.recommendations(db, ws),
        "pricing": lambda: tools.pricing_summary(db, ws),
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


PRODUCT_INTENT = {
    "sales": "product_sales", "margin": "product_sales", "unknown": "product_sales",
    "top_products": "product_sales", "slow_products": "product_sales",
    "stock": "product_stock", "dead_stock": "product_stock",
    "forecast": "product_forecast",
}  # fmt: skip
FOLLOW_CUES = {"and", "aur", "also", "phir", "what", "how", "और", "फिर", "same", "iska", "uska"}


def _is_follow_up(u: nlu.Understood, question: str, has_product: bool) -> bool:
    toks = nlu.tokens(question)
    strong = max(u.scores.values(), default=0.0) >= 2
    if u.intent in {"unknown", "help"} and (u.period or has_product or FOLLOW_CUES & set(toks)):
        return u.intent == "unknown" or bool(u.period or has_product)
    return len(toks) <= 5 and bool(u.period or has_product) and not strong


def _ctx(u: nlu.Understood, product: Product | None) -> dict[str, Any]:
    return {
        "intent": u.intent,
        "period": None if u.period is None else {"label": u.period.label, "start": u.period.start.isoformat(), "end": u.period.end.isoformat()},
        "product": None if product is None else {"sku": product.sku, "name": product.name},
    }  # fmt: skip


def _period_from(d: dict[str, Any] | None) -> nlu.Period | None:
    if not d:
        return None
    return nlu.Period(date.fromisoformat(d["start"]), date.fromisoformat(d["end"]), d["label"])


def ask(
    db: Session,
    workspace: Workspace,
    question: str,
    role: WorkspaceRole = WorkspaceRole.VIEWER,
    today: date | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    u = nlu.route(question, today or date.today())
    lang = u.language if u.language in replies.L else "en"
    product = tools.find_product_in_text(db, workspace.id, question)
    followed = False
    if context and _is_follow_up(u, question, product is not None):
        prev = context.get("intent")
        if prev and prev not in {"unknown", "help", "documents"}:
            followed = True
            u.intent = prev
            u.period = u.period or _period_from(context.get("period"))
            if product is None and context.get("product"):
                product = db.scalars(
                    select(Product).where(
                        Product.workspace_id == workspace.id,
                        Product.sku == context["product"]["sku"],
                    )
                ).first()
    if product is not None and u.intent in PRODUCT_INTENT:
        u.intent = PRODUCT_INTENT[u.intent]
    elif product is None and u.intent.startswith("product_"):
        u.intent = {
            "product_sales": "sales",
            "product_stock": "stock",
            "product_forecast": "forecast",
        }[u.intent]
    steps: list[dict[str, Any]] = [
        {"step": "understood", "detail": f"{u.intent} · {lang}" + (f" · {u.period.label}" if u.period else "") + (f" · {product.name}" if product else "") + (" · follow-up" if followed else "")}
    ]  # fmt: skip
    base: dict[str, Any] = {
        "intent": u.intent, "language": lang, "question": question, "follow_up": followed,
        "period": None if u.period is None else {"label": u.period.label, "start": u.period.start.isoformat(), "end": u.period.end.isoformat()},
        "suggestions": SUGGESTIONS[lang], "steps": steps, "evidence": [], "context": _ctx(u, product),
    }  # fmt: skip

    def finish(out: dict[str, Any]) -> dict[str, Any]:
        out["steps"].append({"step": "done", "ms": round((time.perf_counter() - t0) * 1000)})
        return out

    if u.intent not in {"help", "unknown"} and DOC_CUES & set(nlu.tokens(question)):
        found = _from_documents(db, workspace, role, question, lang, base)
        if found is not None and not found["answer"].startswith(
            ("This may not", "Shayad yeh", "शायद यह")
        ):
            found["steps"].append({"step": "tool", "tool": "document_search"})
            return finish(found)
    if u.intent == "help":
        return finish(
            {
                **base,
                "answer": replies.HELP[lang],
                "rows": [],
                "link": None,
                "note": None,
                "grounded": False,
            }
        )
    if u.intent == "unknown":
        found = _from_documents(db, workspace, role, question, lang, base)
        if found is not None:
            found["steps"].append({"step": "tool", "tool": "document_search"})
            return finish(found)
        return finish(
            {
                **base,
                "answer": replies.UNKNOWN[lang] + replies.HELP[lang],
                "rows": [],
                "link": None,
                "note": None,
                "grounded": False,
            }
        )
    t1 = time.perf_counter()
    res = _run(db, workspace, u, product)
    steps.append(
        {
            "step": "tool",
            "tool": u.intent,
            "ms": round((time.perf_counter() - t1) * 1000),
            "empty": bool(res is None or res.empty),
        }
    )
    if res is None or res.empty:
        hint = replies.EMPTY_HINT.get(u.intent)
        text = replies.EMPTY[lang] + (
            hint[replies.L.index(lang)] if hint else (res.note if res and res.note else "")
        )
        return finish(
            {
                **base,
                "answer": text,
                "rows": [],
                "link": res.link if res else None,
                "note": None,
                "grounded": True,
            }
        )
    answer = replies.BUILD[u.intent](lang, res)
    return finish({**base, "answer": answer.strip(), "rows": res.rows, "link": res.link, "note": res.note,
                   "grounded": True, "evidence": evidence.build(u.intent, res)})  # fmt: skip
