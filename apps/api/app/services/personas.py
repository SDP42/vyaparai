"""Who is asking: five personas, what each may ask the assistant, and which data each may open.

A persona is a job in the shop (owner, operations manager, analyst, accountant, counter staff). It sits on top
of the workspace role (owner, admin, analyst, viewer):

- the **role** decides what a person may *do* (edit, import, approve);
- the **persona** decides what they are *meant to see and ask about*, so a cashier is not shown the credit book
  and the assistant does not answer them questions that belong to the owner.

Enforcement: the assistant refuses questions outside the persona's remit (and says who can answer), redacts
margin where the persona may not see it, and a few sensitive endpoints (credit, supplier bills, margins, customer
lists, reports) require the matching capability. A member with no persona set keeps the plain role-based access
they always had; personas apply once one is assigned (invite, Team page, or a demo account).
"""

from dataclasses import dataclass, field

from app.models.workspace import WorkspaceRole

CAPABILITIES = ("credit", "margin", "supplier", "customers", "stock", "reports", "staff")

ALL_INTENTS = {
    "sales", "why", "top_products", "slow_products", "customers", "stock", "dead_stock", "forecast", "alerts", "margin", "supplier",
    "reviews", "festival", "udhaar", "recommend", "pricing", "goals", "product_sales", "product_stock", "product_forecast",
    "documents", "help", "unknown",
}  # fmt: skip


@dataclass(frozen=True, slots=True)
class Persona:
    key: str
    label: dict[str, str]
    about: dict[str, str]
    default_role: WorkspaceRole
    capabilities: frozenset[str]
    intents: frozenset[str]
    owner_only_hint: dict[str, str] = field(default_factory=dict)
    home: str = "/app"
    nav: frozenset[str] = frozenset()  # app paths shown; empty means all
    suggestions: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def can(self, capability: str) -> bool:
        return capability in self.capabilities

    def allows(self, intent: str) -> bool:
        return intent in self.intents


def _p(**kw) -> Persona:  # type: ignore[no-untyped-def]
    kw["capabilities"] = frozenset(kw["capabilities"])
    kw["intents"] = frozenset(kw["intents"]) | {"help", "unknown", "documents"}
    kw["nav"] = frozenset(kw.get("nav", ()))
    return Persona(**kw)


PERSONAS: dict[str, Persona] = {
    "owner": _p(
        key="owner", default_role=WorkspaceRole.OWNER, capabilities=CAPABILITIES, intents=ALL_INTENTS,
        label={"en": "Store owner", "hinglish": "Dukaan malik", "hi": "दुकान मालिक"},
        about={"en": "Sees everything: sales, profit, stock, customers, credit, and decides what to do.", "hinglish": "Sab kuch dekhta hai: bikri, munafa, stock, grahak, udhaar, aur faisla leta hai.", "hi": "सब कुछ देखता है: बिक्री, मुनाफ़ा, स्टॉक, ग्राहक, उधार, और फैसला लेता है।"},
        suggestions={"en": ("What should I do this week?", "Sales last week", "Why did sales drop?", "Who owes me money?", "Did my discounts work?"),
                     "hinglish": ("Is hafte kya karna chahiye?", "Pichle hafte ki bikri", "Bikri kyun gir gayi?", "Kis par kitna udhaar hai?", "Chhoot se fayda hua kya?"),
                     "hi": ("इस हफ्ते क्या करना चाहिए?", "पिछले हफ्ते की बिक्री", "बिक्री क्यों गिरी?", "किस पर कितना उधार है?", "छूट से फायदा हुआ क्या?")},
    ),
    "ops_manager": _p(
        key="ops_manager", default_role=WorkspaceRole.ADMIN, capabilities=("supplier", "stock", "credit", "reports", "staff"),
        intents={"sales", "why", "top_products", "slow_products", "stock", "dead_stock", "forecast", "alerts", "supplier", "reviews", "festival",
                 "udhaar", "recommend", "goals", "product_sales", "product_stock", "product_forecast"},
        label={"en": "Operations manager", "hinglish": "Operations manager", "hi": "ऑपरेशंस मैनेजर"},
        about={"en": "Keeps shelves full and the shop running: stock, orders, suppliers, festivals.", "hinglish": "Shelf bhari rakhta hai aur dukaan chalata hai: stock, order, supplier, tyohar.", "hi": "शेल्फ भरी रखता है और दुकान चलाता है: स्टॉक, ऑर्डर, सप्लायर, त्योहार।"},
        owner_only_hint={"en": "the owner", "hinglish": "malik se", "hi": "मालिक से"},
        home="/app/inventory",
        nav={"/app", "/app/ask", "/app/recommendations", "/app/goals", "/app/alerts", "/app/sales", "/app/products", "/app/forecasts", "/app/inventory", "/app/festivals", "/app/bills", "/app/udhaar", "/app/reviews", "/app/documents", "/app/reports", "/app/digest", "/app/investigate", "/app/staff", "/app/team"},
        suggestions={"en": ("What should I order?", "What will run out first?", "Dead stock", "Next week forecast", "Which festival is coming?"),
                     "hinglish": ("Kya mangwana hai?", "Pehle kya khatam hoga?", "Dead stock kitna hai?", "Agle hafte ka forecast", "Kaun sa tyohar aa raha hai?"),
                     "hi": ("क्या मंगवाना है?", "पहले क्या खत्म होगा?", "डेड स्टॉक कितना है?", "अगले हफ्ते का अनुमान", "कौन सा त्योहार आ रहा है?")},
    ),
    "analyst": _p(
        key="analyst", default_role=WorkspaceRole.ANALYST, capabilities=("margin", "supplier", "customers", "stock", "reports", "staff"),
        intents={"sales", "why", "top_products", "slow_products", "customers", "stock", "dead_stock", "forecast", "alerts", "margin", "supplier",
                 "reviews", "festival", "recommend", "pricing", "goals", "product_sales", "product_stock", "product_forecast"},
        label={"en": "Data analyst", "hinglish": "Data analyst", "hi": "डेटा एनालिस्ट"},
        about={"en": "Finds patterns: why sales moved, which customers and products matter, how accurate forecasts are.", "hinglish": "Pattern dhoondhta hai: bikri kyun badli, kaun se grahak aur products zaroori hain.", "hi": "पैटर्न ढूँढता है: बिक्री क्यों बदली, कौन से ग्राहक और प्रोडक्ट ज़रूरी हैं।"},
        owner_only_hint={"en": "the owner", "hinglish": "malik se", "hi": "मालिक से"},
        home="/app/investigate",
        nav={"/app", "/app/ask", "/app/recommendations", "/app/goals", "/app/alerts", "/app/investigate", "/app/sales", "/app/customers", "/app/products", "/app/pricing", "/app/reviews", "/app/forecasts", "/app/inventory", "/app/festivals", "/app/bills", "/app/costs", "/app/documents", "/app/reports", "/app/digest", "/app/data", "/app/staff"},
        suggestions={"en": ("Why did sales change?", "Top 5 products", "Customers who stopped coming", "What do customers complain about?", "What is my margin?"),
                     "hinglish": ("Bikri kyun badli?", "Top 5 products", "Kaun se grahak aana band hue?", "Reviews mein kya shikayat hai?", "Margin kaisa hai?"),
                     "hi": ("बिक्री क्यों बदली?", "टॉप 5 प्रोडक्ट", "कौन से ग्राहक आना बंद हुए?", "रिव्यू में क्या शिकायत है?", "मार्जिन कितना है?")},
    ),
    "accountant": _p(
        key="accountant", default_role=WorkspaceRole.VIEWER, capabilities=("credit", "margin", "supplier", "reports"),
        intents={"sales", "why", "margin", "supplier", "udhaar", "alerts", "goals", "product_sales", "pricing"},
        label={"en": "Accountant", "hinglish": "Accountant", "hi": "अकाउंटेंट"},
        about={"en": "Reads the numbers: sales, margin, credit and supplier bills, for accounts and tax. View only.", "hinglish": "Numbers padhta hai: bikri, margin, udhaar aur supplier bill, hisaab aur tax ke liye. Sirf dekhna.", "hi": "आंकड़े पढ़ता है: बिक्री, मार्जिन, उधार और सप्लायर बिल, हिसाब और टैक्स के लिए। सिर्फ़ देखना।"},
        owner_only_hint={"en": "the owner", "hinglish": "malik se", "hi": "मालिक से"},
        home="/app/reports",
        nav={"/app", "/app/ask", "/app/goals", "/app/alerts", "/app/sales", "/app/pricing", "/app/bills", "/app/costs", "/app/udhaar", "/app/documents", "/app/reports", "/app/digest"},
        suggestions={"en": ("Sales last month", "What is my margin?", "Who owes me money?", "Did any supplier raise prices?", "Return policy"),
                     "hinglish": ("Pichle mahine ki bikri", "Margin kaisa hai?", "Kis par kitna baaki hai?", "Supplier ka price badha kya?", "Return policy kya hai?"),
                     "hi": ("पिछले महीने की बिक्री", "मार्जिन कितना है?", "किस पर कितना बाकी है?", "सप्लायर का दाम बढ़ा क्या?", "रिटर्न पॉलिसी क्या है?")},
    ),
    "cashier": _p(
        key="cashier", default_role=WorkspaceRole.VIEWER, capabilities=("stock",),
        intents={"sales", "top_products", "product_stock", "product_sales", "festival", "stock"},
        label={"en": "Counter staff", "hinglish": "Counter staff", "hi": "काउंटर स्टाफ"},
        about={"en": "Serves customers: is it in stock, what is the price, what sells best, what is the return rule.", "hinglish": "Grahak ko sambhalta hai: stock mein hai kya, daam kya hai, kya zyada bikta hai, return ka niyam kya hai.", "hi": "ग्राहकों को संभालता है: स्टॉक में है क्या, दाम क्या है, क्या ज़्यादा बिकता है, रिटर्न का नियम क्या है।"},
        owner_only_hint={"en": "the owner or manager", "hinglish": "malik ya manager se", "hi": "मालिक या मैनेजर से"},
        home="/app/ask",
        nav={"/app/ask", "/app/inventory", "/app/products", "/app/documents", "/app/festivals", "/app/staff"},
        suggestions={"en": ("Is Basmati rice in stock?", "What sells the most?", "Today's sales", "Return policy", "Which festival is coming?"),
                     "hinglish": ("Basmati rice stock mein hai?", "Sabse zyada kya bikta hai?", "Aaj ki bikri", "Return ka niyam kya hai?", "Kaun sa tyohar aa raha hai?"),
                     "hi": ("बासमती चावल स्टॉक में है?", "सबसे ज़्यादा क्या बिकता है?", "आज की बिक्री", "रिटर्न का नियम क्या है?", "कौन सा त्योहार आ रहा है?")},
    ),
}  # fmt: skip

ROLE_DEFAULT = {
    WorkspaceRole.OWNER: "owner",
    WorkspaceRole.ADMIN: "ops_manager",
    WorkspaceRole.ANALYST: "analyst",
    WorkspaceRole.VIEWER: "accountant",
}


def get(key: str | None) -> Persona | None:
    return PERSONAS.get(key) if key else None


def valid_for_role(persona: str, role: WorkspaceRole) -> bool:
    """A persona may not carry more power than the role allows (a cashier cannot be an owner, an owner is always owner)."""
    p = PERSONAS.get(persona)
    if p is None:
        return False
    if role == WorkspaceRole.OWNER:
        return persona == "owner"
    return p.default_role.rank <= role.rank and persona != "owner"


def refusal(persona: Persona, lang: str, intent_label: str) -> str:
    who = persona.owner_only_hint.get(lang) or persona.owner_only_hint.get("en", "the owner")
    label = persona.label.get(lang, persona.label["en"])
    return {
        "en": f"That is not something I can answer for a {label.lower()}. Please ask {who}. Here is what I can help with.",
        "hinglish": f"Yeh {label} ke liye mere jawab dene ka sawaal nahi hai. Kripya {who} poochiye. Main in cheezon mein madad kar sakta hoon.",
        "hi": f"यह {label} के लिए मेरे जवाब देने का सवाल नहीं है। कृपया {who} पूछिए। मैं इन चीज़ों में मदद कर सकता हूँ।",
    }.get(lang, "")


def remit_summary(persona: Persona, lang: str) -> str:
    return persona.about.get(lang, persona.about["en"])
