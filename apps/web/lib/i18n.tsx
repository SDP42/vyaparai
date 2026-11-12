"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

/**
 * Interface language: English, Hinglish (Hindi in Roman letters) and Hindi (Devanagari).
 * Every language must define every key: the `Record<Key, string>` type makes the compiler check it.
 * Covered: navigation, the app shell, voice, the Ask, Next steps and Udhaar pages in full, and the headline and introduction of every other page. Page bodies stay in English.
 * The Hinglish and Hindi wording has not been reviewed by a native speaker yet.
 */
const en = {
  "nav.command": "Command center", "nav.ask": "Ask", "nav.steps": "Next steps", "nav.alerts": "Alerts", "nav.investigate": "Investigate", "nav.sales": "Sales",
  "nav.customers": "Customers", "nav.products": "Products", "nav.forecasts": "Forecasts", "nav.stock": "Stock", "nav.festivals": "Festivals", "nav.bills": "Bills",
  "nav.pricing": "Pricing", "nav.costs": "Costs", "nav.reviews": "Reviews", "nav.documents": "Documents", "nav.campaigns": "Campaigns", "nav.udhaar": "Udhaar",
  "nav.digest": "Digest", "nav.data": "Data", "nav.reports": "Reports", "nav.stores": "Stores", "nav.team": "Team", "nav.goals": "Goals", "nav.staff": "Staff", "nav.today": "Today", "nav.galla": "Galla", "nav.expiry": "Expiry", "nav.orders": "Orders", "h.today": "Today", "i.today": "Yesterday's sales, who to call for udhaar, what to order and what is expiring. Write an udhaar or expense in one line.", "h.galla": "Galla and expenses", "i.galla": "Count the drawer at the end of the day: what should be there against what is. Write the day's expenses as they happen.", "h.expiry": "Expiring stock", "i.expiry": "Write down the items you worry about with their dates. The list tells you what to take off the shelf and what to sell first.", "h.orders": "Order lists", "i.orders": "What to order, grouped by the supplier who last billed you, as a message you can share. Nothing is sent from here.", "h.staff": "Staff", "i.staff": "Who sold what: each cashier or salesperson, by the name on the bill.",
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
  "h.sales": "Sales", "i.sales": "What moved net sales, how much each part contributed, and the transactions behind it.", "h.customers": "Customers",
  "h.products": "Products", "i.products": "Which products carry the business, which earn their shelf space, and what is bought together.", "h.stock": "Stock",
  "i.stock": "How long your stock will last, what to order and how much, and where cash is stuck on the shelf. It uses your forecast, so build one first for the best advice.",
  "h.forecasts": "Forecasts", "i.forecasts": "What to expect over the next two weeks, how sure we are, and why you can trust it.", "h.alerts": "Alerts",
  "h.digest": "Your daily summary", "i.digest": "Three numbers and one thing to do. Read it in half a minute, without opening a dashboard.",
  "h.goals": "Where you are against where you want to be",
  "i.goals": "Set a target for the month or week. You see your pace, the amount needed each remaining day, and a range for where you will likely finish, not a single promise.",
  "h.festivals": "Festivals and cricket", "i.festivals": "Something is on almost every day in India, but only some dates really move a shop's sales. These are the ones that can, with the products they touch in your shop and whether your stock will last.", "h.bills": "What you paid your suppliers",
  "i.bills": "Take a photo of a bill or upload a PDF. We read the items and rates, you check them, and your costs and supplier price changes stay current without typing.",
  "h.costs": "Costs and margin", "h.reviews": "What customers are saying",
  "i.reviews": "Every review is read for language, mood and what it is about. Each claim shows the words it came from, so you can check it.",
  "h.documents": "Your papers, searchable",
  "i.documents": "Add policies, supplier terms and procedures. Ask in English, हिन्दी or Hinglish and get the exact passage with where it came from. Search reads your files on this server only.",
  "h.pricing": "Did your offers pay off?",
  "i.pricing": "Each product's discount days are compared with its normal days of the same weekday, in sales and in profit after the discount. Price moves are small trials, never big jumps.",
  "h.investigate": "Why did sales change?",
  "i.investigate": "Pick a period. It is compared with the one before, the change is split into effects, and the usual suspects are checked: stock, costs, discounts, festivals, reviews and customers. You see every step.",
  "h.reports": "A summary you can print or send",
  "i.reports": "Sales and what changed, products, customers, stock, udhaar, the forecast and suggested actions, as a PDF for your accountant or partner, or a CSV. A saved report stays exactly as it was made.",
  "h.stores": "All your shops, side by side",
  "i.stores": "Compared on growth, margin and order value rather than raw sales, because a bigger shop is not a better-run one. Each shop keeps its own data and its own team.",
  "h.team": "Who can see this shop", "i.team": "Give people the least access they need. Roles can be changed or removed at any time.", "h.data": "Data",
  "h.campaigns": "Campaigns",
} as const;
export type Key = keyof typeof en;
type Dict = Record<Key, string>;

const hinglish: Dict = {
  "nav.command": "Dashboard", "nav.ask": "Poochiye", "nav.steps": "Agla kadam", "nav.alerts": "Alerts", "nav.investigate": "Jaanch", "nav.sales": "Bikri",
  "nav.customers": "Grahak", "nav.products": "Products", "nav.forecasts": "Anumaan", "nav.stock": "Stock", "nav.festivals": "Tyohar", "nav.bills": "Kharid bill",
  "nav.pricing": "Daam", "nav.costs": "Laagat", "nav.reviews": "Reviews", "nav.documents": "Kaagaz", "nav.campaigns": "Campaign", "nav.udhaar": "Udhaar",
  "nav.digest": "Roz ka saar", "nav.data": "Data", "nav.reports": "Reports", "nav.stores": "Dukaanein", "nav.team": "Team", "nav.goals": "Lakshya", "nav.staff": "Staff", "nav.today": "Aaj", "nav.galla": "Galla", "nav.expiry": "Expiry", "nav.orders": "Order", "h.today": "Aaj", "i.today": "Kal ki bikri, kisse udhaar maangna hai, kya mangwana hai aur kya expire ho raha hai. Udhaar ya kharcha ek line mein likhiye.", "h.galla": "Galla aur kharcha", "i.galla": "Din ke ant mein galla giniye: kitna hona chahiye aur kitna hai. Din ke kharche jaise hon waise likhiye.", "h.expiry": "Expire hone wala maal", "i.expiry": "Jin cheezon ki chinta hai unki taareekh likhiye. List batati hai kya shelf se hatana hai aur kya pehle bechna hai.", "h.orders": "Order list", "i.orders": "Kya mangwana hai, supplier ke hisaab se, ek message ki tarah jo aap bhej sakte hain. Yahan se kuch nahi bheja jaata.", "h.staff": "Staff", "i.staff": "Kisne kitna becha: har cashier ya salesperson, bill par likhe naam se.",
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
  "h.sales": "Bikri", "i.sales": "Bikri kis wajah se badli, har hisse ka kitna asar tha, aur uske peeche ke bill.", "h.customers": "Grahak", "h.products": "Products",
  "i.products": "Kaun se products dhandha chalate hain, kaun shelf ki jagah ke laayak hain, aur saath mein kya bikta hai.", "h.stock": "Stock",
  "i.stock": "Stock kitne din chalega, kya aur kitna mangwana hai, aur shelf par paisa kahan fasa hai. Yeh aapka forecast use karta hai, isliye pehle forecast bana lijiye.",
  "h.forecasts": "Forecast", "i.forecasts": "Agle do hafte mein kya hone ki ummeed hai, hum kitne pakke hain, aur bharosa kyun kar sakte hain.", "h.alerts": "Alerts",
  "h.digest": "Aapka roz ka saar", "i.digest": "Teen numbers aur ek kaam. Aadhe minute mein padhiye, dashboard khole bina.",
  "h.goals": "Aap kahan hain aur kahan pahunchna hai",
  "i.goals": "Mahine ya hafte ka target rakhiye. Aapki raftaar, baaki har din kitna chahiye, aur kahan tak pahunchne ki sambhavna ka daayra dikhta hai, koi ek pakka waada nahi.",
  "h.festivals": "Tyohar aur cricket", "i.festivals": "India mein lagbhag roz kuch na kuch hota hai, par kuch hi taareekhein dukaan ki bikri sach mein hilati hain. Yeh wahi hain, saath mein aapki dukaan ke kaun se products par asar padta hai aur stock chalega ya nahi.", "h.bills": "Supplier ko aapne kya diya",
  "i.bills": "Bill ki photo kheenchiye ya PDF daaliye. Hum item aur rate padhte hain, aap check karte hain, aur aapka cost aur supplier ke daam ka badlaav bina likhe taaza rehta hai.",
  "h.costs": "Cost aur margin", "h.reviews": "Grahak kya keh rahe hain",
  "i.reviews": "Har review ki bhasha, mijaaz aur vishay padha jaata hai. Har baat ke saath wo shabd dikhte hain jinse woh nikli, taaki aap check kar sakein.",
  "h.documents": "Aapke kaagaz, dhoondhne laayak",
  "i.documents": "Policy, supplier ki shartein aur tareeke daaliye. English, हिन्दी ya Hinglish mein poochiye aur sahi hissa paaiye, kahan se aaya yeh bhi. Khoj aapki files sirf is server par padhti hai.",
  "h.pricing": "Kya aapke offers se fayda hua?",
  "i.pricing": "Har product ke chhoot wale din usi weekday ke normal dinon se milaye jaate hain, bikri mein bhi aur chhoot ke baad munafe mein bhi. Daam mein badlaav chhote prayog hain, kabhi bade jhatke nahi.",
  "h.investigate": "Bikri kyun badli?",
  "i.investigate": "Ek samay chuniye. Use pichle samay se milaya jaata hai, badlaav ko asar mein baanta jaata hai, aur aam shak check hote hain: stock, cost, chhoot, tyohar, reviews aur grahak. Aap har kadam dekhte hain.",
  "h.reports": "Ek saar jo chhaap ya bhej sakein",
  "i.reports": "Bikri aur kya badla, products, grahak, stock, udhaar, forecast aur sujhaye kaam, accountant ya partner ke liye PDF, ya CSV. Save ki hui report waisi hi rehti hai jaisi bani thi.",
  "h.stores": "Aapki saari dukaanein, saath saath",
  "i.stores": "Badhat, margin aur bill ki keemat par milaan, sirf bikri par nahi, kyunki badi dukaan ka behtar chalna zaroori nahi. Har dukaan ka apna data aur apni team hai.",
  "h.team": "Is dukaan ko kaun dekh sakta hai", "i.team": "Logon ko utni hi access dijiye jitni zaroori hai. Role kabhi bhi badle ya hataye ja sakte hain.",
  "h.data": "Data", "h.campaigns": "Campaigns",
};

const hi: Dict = {
  "nav.command": "डैशबोर्ड", "nav.ask": "पूछिए", "nav.steps": "अगला कदम", "nav.alerts": "अलर्ट", "nav.investigate": "जाँच", "nav.sales": "बिक्री",
  "nav.customers": "ग्राहक", "nav.products": "प्रोडक्ट", "nav.forecasts": "अनुमान", "nav.stock": "स्टॉक", "nav.festivals": "त्योहार", "nav.bills": "खरीद बिल",
  "nav.pricing": "दाम", "nav.costs": "लागत", "nav.reviews": "रिव्यू", "nav.documents": "कागज़", "nav.campaigns": "कैंपेन", "nav.udhaar": "उधार",
  "nav.digest": "रोज़ का सार", "nav.data": "डेटा", "nav.reports": "रिपोर्ट", "nav.stores": "दुकानें", "nav.team": "टीम", "nav.goals": "लक्ष्य", "nav.staff": "स्टाफ", "nav.today": "आज", "nav.galla": "गल्ला", "nav.expiry": "एक्सपायरी", "nav.orders": "ऑर्डर", "h.today": "आज", "i.today": "कल की बिक्री, किससे उधार माँगना है, क्या मंगवाना है और क्या एक्सपायर हो रहा है। उधार या खर्च एक लाइन में लिखिए।", "h.galla": "गल्ला और खर्च", "i.galla": "दिन के अंत में गल्ला गिनिए: कितना होना चाहिए और कितना है। दिन के खर्च जैसे हों वैसे लिखिए।", "h.expiry": "एक्सपायर होने वाला माल", "i.expiry": "जिन चीज़ों की चिंता है उनकी तारीख लिखिए। सूची बताती है क्या शेल्फ से हटाना है और क्या पहले बेचना है।", "h.orders": "ऑर्डर सूची", "i.orders": "क्या मंगवाना है, सप्लायर के हिसाब से, एक संदेश की तरह जो आप भेज सकते हैं। यहाँ से कुछ नहीं भेजा जाता।", "h.staff": "स्टाफ", "i.staff": "किसने कितना बेचा: हर कैशियर या सेल्समैन, बिल पर लिखे नाम से।",
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
  "h.sales": "बिक्री", "i.sales": "बिक्री किस वजह से बदली, हर हिस्से का कितना असर रहा, और उसके पीछे के बिल।", "h.customers": "ग्राहक", "h.products": "प्रोडक्ट",
  "i.products": "कौन से प्रोडक्ट धंधा चलाते हैं, कौन शेल्फ की जगह के लायक हैं, और साथ में क्या बिकता है।", "h.stock": "स्टॉक",
  "i.stock": "स्टॉक कितने दिन चलेगा, क्या और कितना मंगवाना है, और शेल्फ पर पैसा कहाँ फँसा है। यह आपका अनुमान इस्तेमाल करता है, इसलिए पहले अनुमान बना लीजिए।",
  "h.forecasts": "अनुमान", "i.forecasts": "अगले दो हफ्तों में क्या होने की उम्मीद है, हम कितने पक्के हैं, और भरोसा क्यों कर सकते हैं।", "h.alerts": "अलर्ट",
  "h.digest": "आपका रोज़ का सार", "i.digest": "तीन आँकड़े और एक काम। आधे मिनट में पढ़िए, डैशबोर्ड खोले बिना।", "h.goals": "आप कहाँ हैं और कहाँ पहुँचना है",
  "i.goals": "महीने या हफ्ते का लक्ष्य रखिए। आपकी रफ्तार, बाकी हर दिन कितना चाहिए, और कहाँ तक पहुँचने की संभावना का दायरा दिखता है, कोई एक पक्का वादा नहीं।",
  "h.festivals": "त्योहार और क्रिकेट", "i.festivals": "भारत में लगभग हर दिन कुछ न कुछ होता है, पर कुछ ही तारीखें दुकान की बिक्री सच में हिलाती हैं। ये वही हैं, साथ में आपकी दुकान के कौन से प्रोडक्ट पर असर पड़ता है और स्टॉक चलेगा या नहीं।", "h.bills": "सप्लायर को आपने क्या चुकाया",
  "i.bills": "बिल की फोटो खींचिए या PDF डालिए। हम आइटम और रेट पढ़ते हैं, आप जाँचते हैं, और आपकी लागत और सप्लायर के दाम का बदलाव बिना लिखे ताज़ा रहता है।",
  "h.costs": "लागत और मार्जिन", "h.reviews": "ग्राहक क्या कह रहे हैं",
  "i.reviews": "हर रिव्यू की भाषा, मिज़ाज और विषय पढ़ा जाता है। हर बात के साथ वे शब्द दिखते हैं जिनसे वह निकली, ताकि आप जाँच सकें।",
  "h.documents": "आपके कागज़, खोजने लायक",
  "i.documents": "पॉलिसी, सप्लायर की शर्तें और तरीके डालिए। English, हिन्दी या Hinglish में पूछिए और सही हिस्सा पाइए, कहाँ से आया यह भी। खोज आपकी फ़ाइलें सिर्फ इसी सर्वर पर पढ़ती है।",
  "h.pricing": "क्या आपके ऑफ़र से फायदा हुआ?",
  "i.pricing": "हर प्रोडक्ट के छूट वाले दिन उसी वार के सामान्य दिनों से मिलाए जाते हैं, बिक्री में भी और छूट के बाद मुनाफे में भी। दाम में बदलाव छोटे प्रयोग हैं, कभी बड़े झटके नहीं।", "h.investigate": "बिक्री क्यों बदली?",
  "i.investigate": "एक अवधि चुनिए। उसे पिछली अवधि से मिलाया जाता है, बदलाव को असर में बाँटा जाता है, और आम शक जाँचे जाते हैं: स्टॉक, लागत, छूट, त्योहार, रिव्यू और ग्राहक। आप हर कदम देखते हैं।",
  "h.reports": "एक सार जो छाप या भेज सकें",
  "i.reports": "बिक्री और क्या बदला, प्रोडक्ट, ग्राहक, स्टॉक, उधार, अनुमान और सुझाए काम, अकाउंटेंट या पार्टनर के लिए PDF, या CSV। सेव की हुई रिपोर्ट वैसी ही रहती है जैसी बनी थी।",
  "h.stores": "आपकी सारी दुकानें, साथ-साथ",
  "i.stores": "बढ़त, मार्जिन और बिल की कीमत पर मिलान, सिर्फ बिक्री पर नहीं, क्योंकि बड़ी दुकान का बेहतर चलना ज़रूरी नहीं। हर दुकान का अपना डेटा और अपनी टीम है।",
  "h.team": "इस दुकान को कौन देख सकता है", "i.team": "लोगों को उतनी ही पहुँच दीजिए जितनी ज़रूरी है। भूमिकाएँ कभी भी बदली या हटाई जा सकती हैं।", "h.data": "डेटा",
  "h.campaigns": "कैंपेन",
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
