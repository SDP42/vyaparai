"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

/**
 * Interface language: English, Hinglish (Hindi in Roman letters) and Hindi (Devanagari).
 * Every language must define every key: the `Record<Key, string>` type makes the compiler check it.
 * Covered: navigation, the app shell, and the Ask, Next steps and Udhaar pages. Other pages stay in English.
 * The Hinglish and Hindi wording has not been reviewed by a native speaker yet.
 */
const en = {
  "nav.command": "Command center", "nav.ask": "Ask", "nav.steps": "Next steps", "nav.alerts": "Alerts", "nav.investigate": "Investigate", "nav.sales": "Sales",
  "nav.customers": "Customers", "nav.products": "Products", "nav.forecasts": "Forecasts", "nav.stock": "Stock", "nav.festivals": "Festivals", "nav.bills": "Bills",
  "nav.pricing": "Pricing", "nav.costs": "Costs", "nav.reviews": "Reviews", "nav.documents": "Documents", "nav.campaigns": "Campaigns", "nav.udhaar": "Udhaar",
  "nav.digest": "Digest", "nav.data": "Data", "nav.reports": "Reports", "nav.stores": "Stores", "nav.team": "Team", "nav.goals": "Goals",
  "group.overview": "Overview", "group.sales": "Sales and customers", "group.ops": "Running the shop", "group.more": "Reports and settings", "shell.more": "More", "shell.close": "Close", "nav.home": "Home",
  "shell.workspace": "Workspace", "shell.signOut": "Sign out", "shell.skip": "Skip to content", "shell.language": "Language", "shell.switch": "Switch workspace",
  "ask.title": "Ask your shop", "ask.intro": "Ask in English, हिन्दी or Hinglish. Every number comes from your own data, with a link to where you can check it. If it cannot answer, it says so instead of guessing.",
  "ask.placeholder": "Ask about sales, stock, customers…", "ask.send": "Ask", "ask.try": "Try one of these:", "ask.evidence": "Evidence: where these numbers come from", "ask.check": "Check it →",
  "ask.fromData": "From your data", "ask.follow": "Follow-up", "ask.looking": "Looking at your numbers…",
  "steps.title": "What is worth doing next", "steps.intro": "Ranked by likely value, how sure we are, and how much effort it takes. Nothing happens until you choose, and every figure shows how it was worked out.",
  "steps.decide": "To decide", "steps.todo": "To do", "steps.done": "Done", "steps.dismissed": "Dismissed", "steps.stale": "No longer needed",
  "steps.approve": "I will do this", "steps.later": "Not now", "steps.markDone": "Mark done", "steps.again": "Look again", "steps.open": "Open the page →",
  "udhaar.title": "Who owes you, and for how long", "udhaar.intro": "Payments are counted against the oldest udhaar first, so the age of what is still owed is honest. Reminders are drafts you send yourself.",
  "udhaar.total": "Total owed", "udhaar.old": "Older than 30 days", "udhaar.notPaying": "Not paying", "udhaar.first": "Who to chase first", "udhaar.draft": "Draft reminders",
  "udhaar.write": "Write an entry", "udhaar.gave": "Gave udhaar", "udhaar.got": "Got payment", "udhaar.save": "Save entry", "udhaar.name": "Name", "udhaar.amount": "Amount (₹)",
  "ask.didYouMean": "Did you mean:", "voice.tap": "Tap and speak", "voice.stop": "Tap to finish", "voice.listening": "Listening… speak your question", "voice.working": "Understanding what you said…",
  "voice.heard": "I heard:", "voice.ask": "Yes, ask this", "voice.again": "Speak again", "voice.edit": "Fix the words if needed",
  "voice.none": "I could not hear you. Hold the phone closer and try again.", "voice.denied": "The microphone is blocked. Allow it in the browser, or type your question.",
  "voice.unsupported": "Voice is not available in this browser. Please type.", "voice.privacy": "Your voice is turned into words on our server and is not saved.",
  "voice.low": "I am not sure I heard that right. Please check the words.", "voice.readAloud": "Read answers aloud", "voice.listen": "Listen", "voice.noVoice": "This phone has no voice for this language, so the answer is only in text.", "voice.unavailable": "Voice is not set up on this server. Please type.",
} as const;
export type Key = keyof typeof en;
type Dict = Record<Key, string>;

const hinglish: Dict = {
  "nav.command": "Dashboard", "nav.ask": "Poochiye", "nav.steps": "Agla kadam", "nav.alerts": "Alerts", "nav.investigate": "Jaanch", "nav.sales": "Bikri",
  "nav.customers": "Grahak", "nav.products": "Products", "nav.forecasts": "Anumaan", "nav.stock": "Stock", "nav.festivals": "Tyohar", "nav.bills": "Kharid bill",
  "nav.pricing": "Daam", "nav.costs": "Laagat", "nav.reviews": "Reviews", "nav.documents": "Kaagaz", "nav.campaigns": "Campaign", "nav.udhaar": "Udhaar",
  "nav.digest": "Roz ka saar", "nav.data": "Data", "nav.reports": "Reports", "nav.stores": "Dukaanein", "nav.team": "Team", "nav.goals": "Lakshya",
  "group.overview": "Ek nazar", "group.sales": "Bikri aur grahak", "group.ops": "Dukaan chalana", "group.more": "Reports aur settings", "shell.more": "Aur", "shell.close": "Band karein", "nav.home": "Ghar",
  "shell.workspace": "Dukaan", "shell.signOut": "Sign out", "shell.skip": "Seedhe content par jaayein", "shell.language": "Bhasha", "shell.switch": "Dukaan badlein",
  "ask.title": "Apni dukaan se poochiye", "ask.intro": "English, हिन्दी ya Hinglish mein poochiye. Har number aapke apne data se aata hai, aur check karne ka link milta hai. Jawab na ho toh andaza nahi lagata, saaf bata deta hai.",
  "ask.placeholder": "Bikri, stock, grahak ke baare mein poochiye…", "ask.send": "Poochiye", "ask.try": "Inmein se koi try karein:", "ask.evidence": "Saboot: yeh number kahan se aaye", "ask.check": "Check karein →",
  "ask.fromData": "Aapke data se", "ask.follow": "Aage ka sawaal", "ask.looking": "Aapke numbers dekh raha hoon…",
  "steps.title": "Ab kya karna sabse faydemand hai", "steps.intro": "Fayde, bharose aur mehnat ke hisaab se kram mein. Jab tak aap na chunein kuch nahi hota, aur har figure ke saath dikhta hai ki woh kaise nikla.",
  "steps.decide": "Tay karna hai", "steps.todo": "Karna hai", "steps.done": "Ho gaya", "steps.dismissed": "Chhod diya", "steps.stale": "Ab zaroori nahi",
  "steps.approve": "Main karunga", "steps.later": "Abhi nahi", "steps.markDone": "Ho gaya likhein", "steps.again": "Dobara dekhein", "steps.open": "Page kholein →",
  "udhaar.title": "Kis par kitna aur kab se baaki hai", "udhaar.intro": "Payment sabse purane udhaar mein pehle jodi jaati hai, isliye baaki ki umar sahi dikhti hai. Reminder sirf draft hain, bhejna aapko hai.",
  "udhaar.total": "Kul baaki", "udhaar.old": "30 din se purana", "udhaar.notPaying": "Nahi de rahe", "udhaar.first": "Pehle kise yaad dilayein", "udhaar.draft": "Reminder draft karein",
  "udhaar.write": "Entry likhein", "udhaar.gave": "Udhaar diya", "udhaar.got": "Payment mili", "udhaar.save": "Entry save karein", "udhaar.name": "Naam", "udhaar.amount": "Raqam (₹)",
  "ask.didYouMean": "Kya aapka matlab:", "voice.tap": "Dabaiye aur boliye", "voice.stop": "Poora hone par dabaiye", "voice.listening": "Sun raha hoon… apna sawaal boliye", "voice.working": "Aapki baat samajh raha hoon…",
  "voice.heard": "Maine suna:", "voice.ask": "Haan, yeh poochho", "voice.again": "Phir se boliye", "voice.edit": "Zaroorat ho to shabd theek karein",
  "voice.none": "Aawaz nahi aayi. Phone paas laakar phir koshish kijiye.", "voice.denied": "Microphone band hai. Browser mein allow kijiye, ya sawaal likhiye.",
  "voice.unsupported": "Is browser mein voice nahi chalti. Kripya likhiye.", "voice.privacy": "Aapki aawaz hamare server par shabdon mein badalti hai aur save nahi hoti.",
  "voice.low": "Pakka nahi hoon ki sahi suna. Shabd check kar lijiye.", "voice.readAloud": "Jawab bolkar sunao", "voice.listen": "Sunein", "voice.noVoice": "Is phone mein is bhasha ki aawaz nahi hai, isliye jawab sirf likha hua hai.", "voice.unavailable": "Is server par voice shuru nahi hai. Kripya likhiye.",
};

const hi: Dict = {
  "nav.command": "डैशबोर्ड", "nav.ask": "पूछिए", "nav.steps": "अगला कदम", "nav.alerts": "अलर्ट", "nav.investigate": "जाँच", "nav.sales": "बिक्री",
  "nav.customers": "ग्राहक", "nav.products": "प्रोडक्ट", "nav.forecasts": "अनुमान", "nav.stock": "स्टॉक", "nav.festivals": "त्योहार", "nav.bills": "खरीद बिल",
  "nav.pricing": "दाम", "nav.costs": "लागत", "nav.reviews": "रिव्यू", "nav.documents": "कागज़", "nav.campaigns": "कैंपेन", "nav.udhaar": "उधार",
  "nav.digest": "रोज़ का सार", "nav.data": "डेटा", "nav.reports": "रिपोर्ट", "nav.stores": "दुकानें", "nav.team": "टीम", "nav.goals": "लक्ष्य",
  "group.overview": "एक नज़र", "group.sales": "बिक्री और ग्राहक", "group.ops": "दुकान चलाना", "group.more": "रिपोर्ट और सेटिंग", "shell.more": "और", "shell.close": "बंद करें", "nav.home": "होम",
  "shell.workspace": "दुकान", "shell.signOut": "साइन आउट", "shell.skip": "सीधे सामग्री पर जाएँ", "shell.language": "भाषा", "shell.switch": "दुकान बदलें",
  "ask.title": "अपनी दुकान से पूछिए", "ask.intro": "English, हिन्दी या Hinglish में पूछिए। हर आँकड़ा आपके अपने डेटा से आता है, और जाँचने का लिंक मिलता है। जवाब न हो तो अंदाज़ा नहीं लगाता, साफ़ बता देता है।",
  "ask.placeholder": "बिक्री, स्टॉक, ग्राहकों के बारे में पूछिए…", "ask.send": "पूछिए", "ask.try": "इनमें से कोई आज़माइए:", "ask.evidence": "सबूत: ये आँकड़े कहाँ से आए", "ask.check": "जाँचिए →",
  "ask.fromData": "आपके डेटा से", "ask.follow": "आगे का सवाल", "ask.looking": "आपके आँकड़े देख रहा हूँ…",
  "steps.title": "अब क्या करना सबसे फायदेमंद है", "steps.intro": "फायदे, भरोसे और मेहनत के हिसाब से क्रम में। जब तक आप न चुनें कुछ नहीं होता, और हर आँकड़े के साथ दिखता है कि वह कैसे निकला।",
  "steps.decide": "तय करना है", "steps.todo": "करना है", "steps.done": "हो गया", "steps.dismissed": "छोड़ दिया", "steps.stale": "अब ज़रूरी नहीं",
  "steps.approve": "मैं करूँगा", "steps.later": "अभी नहीं", "steps.markDone": "हो गया लिखें", "steps.again": "फिर से देखें", "steps.open": "पेज खोलें →",
  "udhaar.title": "किस पर कितना और कब से बाकी है", "udhaar.intro": "भुगतान सबसे पुराने उधार में पहले जोड़ा जाता है, इसलिए बाकी की उम्र सही दिखती है। रिमाइंडर सिर्फ़ ड्राफ्ट हैं, भेजना आपको है।",
  "udhaar.total": "कुल बाकी", "udhaar.old": "30 दिन से पुराना", "udhaar.notPaying": "नहीं दे रहे", "udhaar.first": "पहले किसे याद दिलाएँ", "udhaar.draft": "रिमाइंडर ड्राफ्ट करें",
  "udhaar.write": "एंट्री लिखें", "udhaar.gave": "उधार दिया", "udhaar.got": "भुगतान मिला", "udhaar.save": "एंट्री सेव करें", "udhaar.name": "नाम", "udhaar.amount": "रकम (₹)",
  "ask.didYouMean": "क्या आपका मतलब:", "voice.tap": "दबाइए और बोलिए", "voice.stop": "पूरा होने पर दबाइए", "voice.listening": "सुन रहा हूँ… अपना सवाल बोलिए", "voice.working": "आपकी बात समझ रहा हूँ…",
  "voice.heard": "मैंने सुना:", "voice.ask": "हाँ, यह पूछो", "voice.again": "फिर से बोलिए", "voice.edit": "ज़रूरत हो तो शब्द ठीक करें",
  "voice.none": "आवाज़ नहीं आई। फ़ोन पास लाकर फिर कोशिश कीजिए।", "voice.denied": "माइक्रोफ़ोन बंद है। ब्राउज़र में अनुमति दीजिए, या सवाल लिखिए।",
  "voice.unsupported": "इस ब्राउज़र में आवाज़ नहीं चलती। कृपया लिखिए।", "voice.privacy": "आपकी आवाज़ हमारे सर्वर पर शब्दों में बदलती है और सेव नहीं होती।",
  "voice.low": "पक्का नहीं हूँ कि सही सुना। शब्द जाँच लीजिए।", "voice.readAloud": "जवाब बोलकर सुनाओ", "voice.listen": "सुनें", "voice.noVoice": "इस फ़ोन में इस भाषा की आवाज़ नहीं है, इसलिए जवाब सिर्फ़ लिखा हुआ है।", "voice.unavailable": "इस सर्वर पर आवाज़ चालू नहीं है। कृपया लिखिए।",
};

export type Lang = "en" | "hinglish" | "hi";
export const LANGS: { key: Lang; label: string }[] = [{ key: "en", label: "English" }, { key: "hinglish", label: "Hinglish" }, { key: "hi", label: "हिन्दी" }];
const DICTS: Record<Lang, Dict> = { en, hinglish, hi };

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: Key) => string };
const LangContext = createContext<Ctx>({ lang: "en", setLang: () => undefined, t: (k) => en[k] });

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => {
    try {
      const saved = localStorage.getItem("vyapar.lang") as Lang | null;
      if (saved && saved in DICTS) setLangState(saved);
    } catch {
      /* storage unavailable: English */
    }
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang === "hi" ? "hi" : lang === "hinglish" ? "en-IN" : "en";
  }, [lang]);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("vyapar.lang", l);
    } catch {
      /* ignore */
    }
  }, []);
  const t = useCallback((k: Key) => DICTS[lang][k] ?? en[k], [lang]);
  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
}

export const useT = () => useContext(LangContext);
