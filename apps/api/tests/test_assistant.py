# ruff: noqa: E501
"""The assistant: routing accuracy on a fixed question set, grounding, and honesty."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.services.assistant import nlu
from app.services.assistant.tools import inr
from tests.test_forecast_api import shop_csv
from tests.test_intelligence_api import make_shop

TODAY = date(2026, 11, 10)

# (question, expected intent). Development set: written first, then keywords were added for the misses, so 100% here is optimistic.
QUESTIONS = [
    ("What were my sales last week?", "sales"), ("how much did I sell yesterday", "sales"),
    ("revenue this month", "sales"), ("total turnover in October", "sales"), ("sales for the last 7 days", "sales"),
    ("pichle hafte ki bikri kitni thi", "sales"), ("aaj kitna becha", "sales"), ("is mahine ki bikri", "sales"),
    ("पिछले महीने की बिक्री", "sales"), ("आज की बिक्री कितनी हुई", "sales"),
    ("why did sales drop?", "why"), ("why are my sales down this week", "why"), ("sales kyun gir gayi", "why"),
    ("bikri kyu kam hui", "why"), ("बिक्री क्यों गिरी", "why"),
    ("top 5 products", "top_products"), ("which are my best selling items", "top_products"), ("best sellers last month", "top_products"),
    ("sabse zyada kya bikta hai", "top_products"), ("सबसे ज्यादा बिकने वाला प्रोडक्ट", "top_products"),
    ("slow moving products", "slow_products"), ("which products sell least", "slow_products"), ("sabse kam bikne wale products", "slow_products"),
    ("how many customers do I have", "customers"), ("which regulars have gone quiet", "customers"), ("lapsed customers", "customers"),
    ("grahak kitne hain", "customers"), ("ग्राहक कितने हैं", "customers"),
    ("what should I order?", "stock"), ("what is running out of stock", "stock"), ("kya mangwana hai", "stock"),
    ("kitna maal order karna chahiye", "stock"), ("क्या मंगवाना है", "stock"),
    ("dead stock", "dead_stock"), ("what stock is stuck and not selling", "dead_stock"), ("paisa fasa hua stock", "dead_stock"),
    ("next week forecast", "forecast"), ("how much will I sell next 14 days", "forecast"), ("agle hafte kitna bikega", "forecast"),
    ("अगले हफ्ते का अनुमान", "forecast"),
    ("any alerts?", "alerts"), ("what needs my attention", "alerts"), ("koi alert hai", "alerts"), ("कोई अलर्ट", "alerts"),
    ("what is my margin", "margin"), ("any margin leaks", "margin"), ("margin kaisa hai", "margin"), ("मार्जिन कितना है", "margin"),
    ("did any supplier raise prices", "supplier"), ("supplier price rises", "supplier"), ("mehenga hua kya supplier ka maal", "supplier"),
    ("what do customers complain about", "reviews"), ("review summary", "reviews"), ("reviews me kya shikayat hai", "reviews"),
    ("रिव्यू में क्या शिकायत है", "reviews"),
    ("upcoming festivals", "festival"), ("what should I stock for Diwali", "festival"), ("Diwali ke liye kya stock", "festival"),
    ("आने वाले त्योहार", "festival"),
    ("who owes me money", "udhaar"), ("udhaar kitna baaki hai", "udhaar"), ("outstanding dues from customers", "udhaar"), ("उधार कितना बाकी है", "udhaar"),
    ("hello", "help"), ("help", "help"), ("what can you do", "help"), ("namaste", "help"),
    ("asdf qwerty", "unknown"), ("what is the capital of France", "unknown"), ("tell me a joke", "unknown"),
]  # fmt: skip


def test_routing_accuracy_on_the_fixed_question_set() -> None:
    wrong = [
        (q, want, nlu.route(q, TODAY).intent)
        for q, want in QUESTIONS
        if nlu.route(q, TODAY).intent != want
    ]
    acc = 1 - len(wrong) / len(QUESTIONS)
    print(f"routing accuracy {acc:.0%} on {len(QUESTIONS)} questions; wrong: {wrong}")
    assert acc >= 0.85, wrong


def test_periods_are_read_in_three_languages() -> None:
    def lab(t: str) -> str | None:
        p = nlu.route(t, TODAY).period
        return p.label if p else None

    assert lab("sales last week") == "last week"
    assert lab("pichle hafte ki bikri") == "last week"
    assert lab("sales for the last 30 days") == "last 30 days"
    assert lab("pichle 7 din ki bikri") == "last 7 days"
    assert lab("बिक्री पिछले महीने") == "October 2026"
    assert lab("sales in october") == "October 2026"
    assert lab("sales yesterday") == "yesterday"
    assert lab("sales") is None


def test_kal_means_tomorrow_for_forecasts_and_yesterday_for_sales() -> None:
    assert nlu.route("kal ki bikri", TODAY).period is not None
    assert nlu.route("kal kitna bikega forecast", TODAY).period is None


def test_languages_are_detected() -> None:
    assert nlu.route("agle hafte kitna bikega", TODAY).language == "hinglish"
    assert nlu.route("पिछले महीने की बिक्री", TODAY).language == "hi"
    assert nlu.route("top 5 products", TODAY).language == "en"


def test_inr_uses_indian_grouping() -> None:
    assert inr(1234567) == "₹12,34,567"
    assert inr(999) == "₹999"
    assert inr(100000) == "₹1,00,000"
    assert inr(-52300.6) == "-₹52,301"
    assert inr(None) == "–"


# ------------------------------------------------------------------ API


@pytest.fixture
def shop(client: TestClient, make_user):
    return make_shop(client, make_user, "ask@shop.in", shop_csv(84))


def ask(client: TestClient, shop, q: str) -> dict:
    h, ws = shop
    r = client.post(f"/api/v1/workspaces/{ws}/assistant/ask", json={"question": q}, headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def test_sales_answer_quotes_the_metric_layer_number(client: TestClient, shop) -> None:
    h, ws = shop
    ov = client.get(
        f"/api/v1/workspaces/{ws}/analytics/overview?from=2026-08-03&to=2026-10-25",
        headers=h,
    ).json()
    net = next(k for k in ov["headline"] if k["key"] == "net_sales")["value"]
    a = ask(client, shop, "sales in October")
    assert a["intent"] == "sales"
    # October is inside the data, so the answer must contain exactly the figure the dashboard shows for it
    oct_ov = client.get(
        f"/api/v1/workspaces/{ws}/analytics/overview?from=2026-10-01&to=2026-10-25",
        headers=h,
    ).json()
    oct_net = next(k for k in oct_ov["headline"] if k["key"] == "net_sales")["value"]
    assert inr(oct_net) in a["answer"]
    assert net is not None


def test_a_period_with_no_sales_says_so_and_falls_back(client: TestClient, shop) -> None:
    a = ask(client, shop, "sales in March")
    assert a["note"]
    assert "no sales" in a["note"].lower()


def test_every_intent_answers_without_error_and_in_the_asked_language(
    client: TestClient, shop
) -> None:
    for q, _ in QUESTIONS:
        a = ask(client, shop, q)
        assert a["answer"]
        assert a["language"] in {"en", "hinglish", "hi"}


def test_unknown_questions_are_not_guessed(client: TestClient, shop) -> None:
    a = ask(client, shop, "what is the capital of France")
    assert a["intent"] == "unknown"
    assert a["grounded"] is False
    assert "not guess" in a["answer"]


def test_empty_workspace_is_honest(client: TestClient, make_user) -> None:
    h = make_user("empty@shop.in")
    ws = client.post("/api/v1/workspaces", json={"name": "Empty"}, headers=h).json()["id"]
    r = client.post(
        f"/api/v1/workspaces/{ws}/assistant/ask", json={"question": "sales last week"}, headers=h
    )
    assert r.status_code == 200
    assert "nothing" in r.json()["answer"].lower() or "no sales" in r.json()["answer"].lower()


def test_input_is_bounded_and_tenancy_holds(client: TestClient, shop, make_user) -> None:
    h, ws = shop
    base = f"/api/v1/workspaces/{ws}/assistant/ask"
    assert client.post(base, json={"question": ""}, headers=h).status_code == 422
    assert client.post(base, json={"question": "x" * 301}, headers=h).status_code == 422
    stranger = make_user("other@shop.in")
    assert client.post(base, json={"question": "sales"}, headers=stranger).status_code == 404


def test_unanswerable_by_numbers_falls_back_to_documents(client: TestClient, shop) -> None:
    h, ws = shop
    doc = b"Return Policy\n\nPackaged food can be returned within 3 days if the pack is sealed and the bill is shown."
    up = client.post(
        f"/api/v1/workspaces/{ws}/documents", files={"file": ("return_policy.txt", doc)}, headers=h
    )
    assert up.status_code == 201
    a = ask(client, shop, "can customers return sealed packs after a few days")
    assert a["intent"] == "documents"
    assert "3 days" in a["answer"]
    assert "return policy" in a["rows"][0]["source"].lower()
    assert ask(client, shop, "what is the capital of France")["intent"] in {"unknown", "documents"}
