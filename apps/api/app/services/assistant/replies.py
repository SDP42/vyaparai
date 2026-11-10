"""Turn a tool result into a short answer in the asker's language (English, Hinglish, Hindi).

Every number in an answer is read from the tool result and formatted here; nothing is generated.
"""

from typing import Any

from app.services.assistant import tools
from app.services.assistant.tools import inr, pct

L = ("en", "hinglish", "hi")


def _pick(lang: str, en: str, hing: str, hi: str) -> str:
    return {"en": en, "hinglish": hing, "hi": hi}.get(lang, en)


def _span(f: dict[str, Any]) -> str:
    a, b = f["start"], f["end"]
    return f"{a:%d %b}" if a == b else f"{a:%d %b} – {b:%d %b %Y}"


def sales(lang: str, r: tools.Result) -> str:
    f = r.facts
    ch = f["net_change_pct"]
    return _pick(
        lang,
        f"Net sales for {_span(f)} were {inr(f['net_sales'])} from {int(f['orders'])} orders (average {inr(f['aov'])} each), "
        f"{pct(ch)} against the period before."
        if ch is not None
        else f"Net sales for {_span(f)} were {inr(f['net_sales'])} from {int(f['orders'])} orders (average {inr(f['aov'])} each).",
        f"{_span(f)} mein net bikri {inr(f['net_sales'])} rahi, {int(f['orders'])} orders se (har order ka average {inr(f['aov'])}). "
        + (f"Pichhle period se {pct(ch)}." if ch is not None else ""),
        f"{_span(f)} में कुल बिक्री {inr(f['net_sales'])} रही, {int(f['orders'])} ऑर्डर से (औसतन {inr(f['aov'])} प्रति ऑर्डर)। "
        + (f"पिछली अवधि से {pct(ch)}।" if ch is not None else ""),
    )


def why(lang: str, r: tools.Result) -> str:
    f = r.facts
    ch = float(f["change"])
    up = ch >= 0
    names = ", ".join(x["name"] for x in (f["gainers"] if up else f["decliners"])[:2]) or "–"
    eff = ", ".join(f"{e['label']} {inr(e['amount'])}" for e in f["effects"]) or "–"
    return _pick(
        lang,
        f"Net sales {'rose' if up else 'fell'} by {inr(abs(ch))} ({_span(f)} vs the period before: {inr(f['now'])} against {inr(f['before'])}). "
        f"Biggest parts: {eff}. Products moving most: {names}. This shows how the numbers changed, not why customers behaved this way.",
        f"Net bikri {inr(abs(ch))} {'badhi' if up else 'ghati'} ({inr(f['now'])} vs {inr(f['before'])}). Sabse bade hisse: {eff}. "
        f"Jin products mein sabse zyada badlav: {names}. Yeh sirf batata hai ki number kaise badle, grahak ka kaaran nahi.",
        f"कुल बिक्री {inr(abs(ch))} {'बढ़ी' if up else 'घटी'} ({inr(f['now'])} बनाम {inr(f['before'])})। सबसे बड़े हिस्से: {eff}। "
        f"सबसे ज्यादा बदले प्रोडक्ट: {names}। यह बताता है कि आंकड़े कैसे बदले, ग्राहकों का कारण नहीं।",
    )


def products(lang: str, r: tools.Result) -> str:
    names = "; ".join(f"{x['name']} ({x['net']})" for x in r.rows)
    slow = r.facts["slow"]
    return _pick(
        lang,
        f"{'Lowest' if slow else 'Top'} {len(r.rows)} products by net sales, {_span(r.facts)}: {names}.",
        f"{_span(r.facts)} mein net bikri ke hisaab se {'sabse kam' if slow else 'top'} {len(r.rows)} products: {names}.",
        f"{_span(r.facts)} में नेट बिक्री के हिसाब से {'सबसे कम' if slow else 'टॉप'} {len(r.rows)} प्रोडक्ट: {names}।",
    )


def customers(lang: str, r: tools.Result) -> str:
    f = r.facts
    st = f["status"]
    return _pick(
        lang,
        f"You have {f['customers']} customers, {float(f['repeat_rate']):.0f}% of them repeat buyers. {f['lapsed_regulars']} regulars have gone quiet "
        f"(Active {st.get('Active', 0)}, Cooling {st.get('Cooling', 0)}, Lapsed {st.get('Lapsed', 0)}). Data to {f['as_of']}.",
        f"Aapke {f['customers']} grahak hain, jinme {float(f['repeat_rate']):.0f}% baar-baar aate hain. {f['lapsed_regulars']} regular grahak ab nahi aa rahe "
        f"(Active {st.get('Active', 0)}, Cooling {st.get('Cooling', 0)}, Lapsed {st.get('Lapsed', 0)}). Data {f['as_of']} tak.",
        f"आपके {f['customers']} ग्राहक हैं, जिनमें {float(f['repeat_rate']):.0f}% बार-बार आते हैं। {f['lapsed_regulars']} नियमित ग्राहक अब नहीं आ रहे "
        f"(Active {st.get('Active', 0)}, Cooling {st.get('Cooling', 0)}, Lapsed {st.get('Lapsed', 0)})। डेटा {f['as_of']} तक।",
    )


def stock(lang: str, r: tools.Result) -> str:
    f = r.facts
    names = ", ".join(x["name"] for x in r.rows[:4]) or "–"
    return _pick(
        lang,
        f"{f['urgent']} products will run out before a new order can arrive and {f['reorder']} should be ordered soon: {names}. Suggested order value {inr(f['order_cost'])}.",
        f"{f['urgent']} products naya maal aane se pehle khatam ho jayenge aur {f['reorder']} ka order jaldi dena chahiye: {names}. Suggested order {inr(f['order_cost'])}.",
        f"{f['urgent']} प्रोडक्ट नया माल आने से पहले खत्म हो जाएंगे और {f['reorder']} का ऑर्डर जल्द देना चाहिए: {names}। सुझाया गया ऑर्डर {inr(f['order_cost'])}।",
    )


def dead_stock(lang: str, r: tools.Result) -> str:
    f = r.facts
    return _pick(
        lang,
        f"{f['dead']} products have stock but have not sold lately, holding {inr(f['dead_cash'])}. Another {inr(f['excess_cash'])} sits in stock beyond what is needed.",
        f"{f['dead']} products ka stock pada hai par bike nahi, {inr(f['dead_cash'])} fasa hua hai. Zaroorat se zyada stock mein aur {inr(f['excess_cash'])} pada hai.",
        f"{f['dead']} प्रोडक्ट का स्टॉक पड़ा है पर बिका नहीं, {inr(f['dead_cash'])} फंसा है। ज़रूरत से ज्यादा स्टॉक में और {inr(f['excess_cash'])} पड़ा है।",
    )


def forecast(lang: str, r: tools.Result) -> str:
    f = r.facts
    stale = (
        _pick(
            lang,
            " The forecast is out of date: new sales came in after it was built.",
            " Forecast purana hai: iske baad nayi bikri aayi hai.",
            " पूर्वानुमान पुराना है: इसके बाद नई बिक्री आई है।",
        )
        if f["stale"]
        else ""
    )
    return _pick(
        lang,
        f"Next {f['horizon']} days: about {f['units_next']:.0f} units (likely {f['low']:.0f} to {f['high']:.0f}), around {inr(f['net_next'])}, {pct(f['change_pct'])} vs the last {f['horizon']} days. "
        f"Past forecasts were off by {float(f['wape']) * 100:.0f}% on average.{stale}",
        f"Agle {f['horizon']} din mein lagbhag {f['units_next']:.0f} units bikne ki ummeed hai ({f['low']:.0f} se {f['high']:.0f} ke beech), yaani {inr(f['net_next'])}, pichhle {f['horizon']} din se {pct(f['change_pct'])}. "
        f"Pichhle forecast average {float(f['wape']) * 100:.0f}% galat the.{stale}",
        f"अगले {f['horizon']} दिन में लगभग {f['units_next']:.0f} यूनिट बिकने की उम्मीद है ({f['low']:.0f} से {f['high']:.0f} के बीच), यानी {inr(f['net_next'])}, पिछले {f['horizon']} दिन से {pct(f['change_pct'])}। "
        f"पिछले पूर्वानुमान औसतन {float(f['wape']) * 100:.0f}% गलत थे।{stale}",
    )


def alerts(lang: str, r: tools.Result) -> str:
    f = r.facts
    if f["count"] == 0:
        return _pick(
            lang,
            "No open alerts. Nothing needs your attention right now.",
            "Koi open alert nahi hai. Abhi kisi cheez par dhyan dene ki zaroorat nahi.",
            "कोई ओपन अलर्ट नहीं है। अभी किसी चीज़ पर ध्यान देने की ज़रूरत नहीं।",
        )
    top = "; ".join(x["title"] for x in r.rows[:3])
    return _pick(
        lang,
        f"{f['count']} open alerts ({f['high']} need attention, {f['medium']} worth a look). Top: {top}.",
        f"{f['count']} open alerts hain ({f['high']} par turant dhyan, {f['medium']} dekhne layak). Sabse upar: {top}.",
        f"{f['count']} ओपन अलर्ट हैं ({f['high']} पर तुरंत ध्यान, {f['medium']} देखने लायक)। सबसे ऊपर: {top}।",
    )


def margin(lang: str, r: tools.Result) -> str:
    f = r.facts
    leaks = "; ".join(x["title"] for x in r.rows[:2])
    tail = f" Leaks: {leaks}." if f["leaks"] else " No margin leaks found."
    return _pick(
        lang,
        f"Gross margin for {_span(f)} was {float(f['margin_pct']):.1f}%.{tail}",
        f"{_span(f)} ka gross margin {float(f['margin_pct']):.1f}% raha.{(' Leaks: ' + leaks + '.') if f['leaks'] else ' Koi margin leak nahi mila.'}",
        f"{_span(f)} का ग्रॉस मार्जिन {float(f['margin_pct']):.1f}% रहा।{(' लीक: ' + leaks + '।') if f['leaks'] else ' कोई मार्जिन लीक नहीं मिला।'}",
    )


def supplier(lang: str, r: tools.Result) -> str:
    f = r.facts
    if f["up"] == 0:
        return _pick(
            lang,
            "No supplier price rises found. Confirm purchase bills on the Bills page to track them.",
            "Supplier ka koi price badhna nahi mila. Bills page par purchase bill confirm karein.",
            "सप्लायर की कोई कीमत बढ़ोतरी नहीं मिली। बिल्स पेज पर खरीद बिल कन्फर्म करें।",
        )
    names = "; ".join(f"{x['name']} {x['change']} ({x['from']}→{x['to']})" for x in r.rows[:3])
    return _pick(
        lang,
        f"{f['up']} products cost more to buy than last time: {names}.",
        f"{f['up']} products pehle se mehenge mil rahe hain: {names}.",
        f"{f['up']} प्रोडक्ट पहले से महंगे मिल रहे हैं: {names}।",
    )


def reviews(lang: str, r: tools.Result) -> str:
    f = r.facts
    worst = (
        ", ".join(f"{x['theme']} ({x['negative_pct']:.0f}% negative)" for x in r.rows[:2]) or "–"
    )
    return _pick(
        lang,
        f"In the last 90 days {f['total']} reviews: {f['positive']} positive, {f['negative']} negative. Most complaints: {worst}.",
        f"Pichhle 90 din mein {f['total']} reviews: {f['positive']} positive, {f['negative']} negative. Sabse zyada shikayat: {worst}.",
        f"पिछले 90 दिन में {f['total']} रिव्यू: {f['positive']} पॉजिटिव, {f['negative']} नेगेटिव। सबसे ज्यादा शिकायत: {worst}।",
    )


def festivals(lang: str, r: tools.Result) -> str:
    if not r.rows:
        return _pick(
            lang,
            "No major festival in the next 60 days for your region.",
            "Agle 60 din mein aapke region ka koi bada tyohar nahi hai.",
            "अगले 60 दिन में आपके क्षेत्र का कोई बड़ा त्योहार नहीं है।",
        )
    first = r.rows[0]
    names = ", ".join(x["name"] for x in r.rows)
    return _pick(
        lang,
        f"Coming up: {names}. First is {first['name']} from {first['start']}"
        + (f"; products likely to move: {first['products']}." if first["products"] else "."),
        f"Aane wale: {names}. Pehla {first['name']}, {first['start']} se"
        + (
            f"; in products ki maang badh sakti hai: {first['products']}."
            if first["products"]
            else "."
        ),
        f"आने वाले: {names}। पहला {first['name']}, {first['start']} से"
        + (f"; इन प्रोडक्ट की मांग बढ़ सकती है: {first['products']}।" if first["products"] else "।"),
    )


def udhaar(lang: str, r: tools.Result) -> str:
    f = r.facts
    return _pick(
        lang,
        f"{f['parties']} people owe you {inr(f['outstanding'])} in udhaar; {inr(f['overdue'])} ({f['overdue_pct']:.0f}%) is more than 30 days old and {f['stalled']} have not paid for two months or more.",
        f"{f['parties']} logon ka {inr(f['outstanding'])} udhaar baaki hai; {inr(f['overdue'])} ({f['overdue_pct']:.0f}%) 30 din se purana hai aur {f['stalled']} ne do mahine se kuch nahi diya.",
        f"{f['parties']} लोगों का {inr(f['outstanding'])} उधार बाकी है; {inr(f['overdue'])} ({f['overdue_pct']:.0f}%) 30 दिन से पुराना है और {f['stalled']} ने दो महीने से कुछ नहीं दिया।",
    )


def product_sales(lang: str, r: tools.Result) -> str:
    f = r.facts
    ch = f["change_pct"]
    tail_en = f", {pct(ch)} against the period before" if ch is not None else ""
    tail_h = f"; pichhle period se {pct(ch)}" if ch is not None else ""
    tail_hi = f"; पिछली अवधि से {pct(ch)}" if ch is not None else ""
    m = f" Margin {float(f['margin']):.1f}%." if f["margin"] is not None else ""
    return _pick(
        lang,
        f"{f['name']}: {inr(f['net_sales'])} net sales and {float(f['units']):.0f} units in {_span(f)}{tail_en}.{m}",
        f"{f['name']}: {_span(f)} mein {inr(f['net_sales'])} net bikri aur {float(f['units']):.0f} units{tail_h}.{m}",
        f"{f['name']}: {_span(f)} में {inr(f['net_sales'])} नेट बिक्री और {float(f['units']):.0f} यूनिट{tail_hi}।",
    )


def product_stock(lang: str, r: tools.Result) -> str:
    f = r.facts
    cover = "no recent demand" if f["cover_days"] is None else f"{f['cover_days']} days of cover"
    cover_h = (
        "haal mein koi maang nahi" if f["cover_days"] is None else f"{f['cover_days']} din ka stock"
    )
    cover_hi = "हाल में कोई मांग नहीं" if f["cover_days"] is None else f"{f['cover_days']} दिन का स्टॉक"
    return _pick(
        lang,
        f"{f['name']}: {cover} (status: {f['status']}). Delivery takes about {f['lead_time']} days. Suggested order: {f['order_qty']} units.",
        f"{f['name']}: {cover_h} (status: {f['status']}). Maal aane mein lagbhag {f['lead_time']} din. Suggested order: {f['order_qty']} units.",
        f"{f['name']}: {cover_hi} (स्थिति: {f['status']})। माल आने में लगभग {f['lead_time']} दिन। सुझाया ऑर्डर: {f['order_qty']} यूनिट।",
    )


def product_forecast(lang: str, r: tools.Result) -> str:
    f = r.facts
    return _pick(
        lang,
        f"{f['name']}: about {f['units_next']:.0f} units in the next {f['horizon']} days (likely {f['low']:.0f} to {f['high']:.0f}), {pct(f['change_pct'])} vs the last {f['horizon']} days. Model confidence: {f['confidence']}.",
        f"{f['name']}: agle {f['horizon']} din mein lagbhag {f['units_next']:.0f} units ({f['low']:.0f} se {f['high']:.0f}), pichhle {f['horizon']} din se {pct(f['change_pct'])}. Model ka bharosa: {f['confidence']}.",
        f"{f['name']}: अगले {f['horizon']} दिन में लगभग {f['units_next']:.0f} यूनिट ({f['low']:.0f} से {f['high']:.0f}), पिछले {f['horizon']} दिन से {pct(f['change_pct'])}। मॉडल का भरोसा: {f['confidence']}।",
    )


def recommend(lang: str, r: tools.Result) -> str:
    top = "; ".join(f"{x['title']} ({x['impact']})" for x in r.rows)
    n = r.facts["count"]
    return _pick(
        lang,
        f"{n} suggestions are waiting. Most valuable first: {top}.",
        f"{n} sujhav intezaar kar rahe hain. Sabse zyada fayde wale pehle: {top}.",
        f"{n} सुझाव इंतज़ार कर रहे हैं। सबसे ज्यादा फायदे वाले पहले: {top}।",
    )


def pricing(lang: str, r: tools.Result) -> str:
    f = r.facts
    return _pick(
        lang,
        f"Of {f['judged']} products with enough discount history, {f['paid']} paid off and {f['lost']} lost money ({inr(f['given'])} given away in those). {f['suggestions']} small price trials are suggested.",
        f"{f['judged']} products mein se {f['paid']} par chhoot se fayda hua aur {f['lost']} par nuksan ({inr(f['given'])} chhoot di gayi). {f['suggestions']} chhote price trial sujhaye gaye hain.",
        f"{f['judged']} प्रोडक्ट में से {f['paid']} पर छूट से फायदा हुआ और {f['lost']} पर नुकसान ({inr(f['given'])} की छूट दी गई)। {f['suggestions']} छोटे प्राइस ट्रायल सुझाए गए हैं।",
    )


def goals(lang: str, r: tools.Result) -> str:
    f = r.facts
    worst = r.rows[0]
    return _pick(
        lang,
        f"You have {f['count']} goals: {f['ok']} on track or reached, {f['behind']} behind or at risk. Most in need of attention: {worst['goal']} ({worst['status']}, {worst['progress']} of target).",
        f"Aapke {f['count']} goal hain: {f['ok']} sahi raste par ya poore, {f['behind']} peeche ya khatre mein. Sabse pehle dhyan: {worst['goal']} ({worst['status']}, target ka {worst['progress']}).",
        f"आपके {f['count']} लक्ष्य हैं: {f['ok']} सही रास्ते पर या पूरे, {f['behind']} पीछे या खतरे में। सबसे पहले ध्यान: {worst['goal']} ({worst['status']}, लक्ष्य का {worst['progress']})।",
    )


HELP = {
    "en": "I answer from your own numbers only. Try: “sales last week”, “why did sales drop?”, “top 5 products”, “what should I order?”, “dead stock”, “next week forecast”, “any alerts?”, “margin”, “supplier price rises”, “customer reviews”, “upcoming festivals”, “who owes me money?”.",
    "hinglish": "Main sirf aapke apne numbers se jawab deta hoon. Poochiye: “pichle hafte ki bikri”, “sales kyun gir gayi”, “top 5 products”, “kya mangwana hai”, “dead stock”, “agle hafte ka forecast”, “koi alert?”, “margin”, “supplier ka price”, “reviews”, “aane wale tyohar”.",
    "hi": "मैं सिर्फ आपके अपने आंकड़ों से जवाब देता हूँ। पूछिए: “पिछले हफ्ते की बिक्री”, “बिक्री क्यों गिरी”, “टॉप 5 प्रोडक्ट”, “क्या मंगवाना है”, “डेड स्टॉक”, “अगले हफ्ते का अनुमान”, “कोई अलर्ट?”, “मार्जिन”, “रिव्यू”, “आने वाले त्योहार”।",
}
UNKNOWN = {
    "en": "I did not understand that, and I will not guess. ",
    "hinglish": "Yeh mujhe samajh nahi aaya, aur main andaza nahi lagaunga. ",
    "hi": "यह मुझे समझ नहीं आया, और मैं अंदाज़ा नहीं लगाऊँगा। ",
}
EMPTY_HINT = {
    "pricing": (
        "Add a few months of sales with discounts.",
        "Kuch mahine ki bikri (chhoot ke saath) daalein.",
        "कुछ महीनों की बिक्री (छूट के साथ) डालें।",
    ),
    "goals": (
        "Set a goal on the Goals page.",
        "Goals page par goal set karein.",
        "लक्ष्य पेज पर लक्ष्य तय करें।",
    ),
    "udhaar": (
        "Add your udhaar ledger on the Udhaar page.",
        "Udhaar page par apna khata daalein.",
        "उधार पेज पर अपना खाता डालें।",
    ),
    "stock": (
        "Add stock counts on the Stock page.",
        "Stock page par stock ginti daalein.",
        "स्टॉक पेज पर स्टॉक की गिनती डालें।",
    ),
    "dead_stock": (
        "Add stock counts on the Stock page.",
        "Stock page par stock ginti daalein.",
        "स्टॉक पेज पर स्टॉक की गिनती डालें।",
    ),
    "forecast": (
        "Build a forecast on the Forecasts page.",
        "Forecasts page par forecast banayein.",
        "फोरकास्ट पेज पर पूर्वानुमान बनाएँ।",
    ),
    "reviews": (
        "Add reviews on the Reviews page.",
        "Reviews page par reviews daalein.",
        "रिव्यू पेज पर रिव्यू डालें।",
    ),
}
EMPTY = {
    "en": "There is nothing to answer this from yet. ",
    "hinglish": "Abhi iska jawab dene ke liye data nahi hai. ",
    "hi": "अभी इसका जवाब देने के लिए डेटा नहीं है। ",
}
BUILD = {
    "sales": sales, "why": why, "top_products": lambda lg, r: products(lg, r), "slow_products": lambda lg, r: products(lg, r),
    "customers": customers, "stock": stock, "dead_stock": dead_stock, "forecast": forecast, "alerts": alerts,
    "margin": margin, "udhaar": udhaar, "pricing": pricing, "goals": goals, "recommend": recommend,
    "product_sales": product_sales, "product_stock": product_stock, "product_forecast": product_forecast, "supplier": supplier, "reviews": reviews, "festival": festivals,
}  # fmt: skip
