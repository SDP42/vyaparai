# LinkedIn post

Copy everything between the two lines and paste it into LinkedIn as is. It is about 2,850 characters by LinkedIn's
count (limit 3,000). Only the first two lines show before "see more", so they carry the hook.

The opening is an illustrative scene, not a personal story. If you have a real moment from a family shop or a
shopkeeper you know, swap it in: it will read even better.

Images: LinkedIn shows up to 20; these 12 are the pick, already numbered in posting order in
`Vyapar-AI-LinkedIn-12.zip` (rebuilt from the files below):

1. `showcase/cover.png`
2. `showcase/problem.png`
3. `showcase/ask.png`
4. `images/11-app-today.png`
5. `showcase/agents.png`
6. `images/12-app-command-center.png`
7. `images/14-app-forecasts.png`
8. `showcase/architecture.png`
9. `showcase/stack.png`
10. `showcase/opening.png`
11. `images/00-repo-summary.png`
12. `images/26-github-repo.png`

---

9 PM. The shutter is half down. The galla is ₹1,340 short, the udhaar notebook has three new names, and the supplier is coming at 8 AM tomorrow. What should the owner order? 🛍️

That moment happens in lakhs of Indian shops every night. I spent the last two weeks building something for it.

The shop already has the data: a billing export, an udhaar notebook, a cash drawer counted by hand. What it doesn't have is time. Nobody at the counter wants a dashboard full of "AOV" and "gross margin". So fast movers run out, slow stock sits on cash, a supplier's quiet price rise eats the margin for weeks, and nobody knows which udhaar to chase first.

So I built 𝗩𝘆𝗮𝗽𝗮𝗿 𝗔𝗜: decision support for Indian kirana and retail shops.

Here's that same night with it:
🌙 The galla close shows cash counted against cash expected, so the ₹1,340 gap gets found the same evening, not at month end
🌅 Next morning, the Today page has yesterday's sales, who to call for udhaar, what to order and what expires this week
📦 The reorder planner turns the forecast into an order list per supplier, ready to share
🗣️ The owner asks the way they talk, typed or spoken: "kal kitna becha?", "Ramesh ko 200 udhaar"
🤖 10 LangGraph agents prepare the work: morning brief, udhaar collector, expiry clearance, price watch and more. A person still decides and sends
👥 The owner, manager, accountant and counter staff each see only what their job needs

𝗪𝗵𝗮𝘁 𝗺𝗮𝗸𝗲𝘀 𝗶𝘁 𝗱𝗶𝗳𝗳𝗲𝗿𝗲𝗻𝘁
1️⃣ No language model writes the answers. Questions go to tested calculations, and every answer shows its evidence, so it can't make up a number
2️⃣ Agents only read. Nothing is ordered, messaged or changed without a person
3️⃣ Made for India: lakh and crore, festival calendars, udhaar, Hinglish typed the way people really type it
4️⃣ Free to run: only permissively licensed software, no paid API keys, speech recognition on the shop's own server
5️⃣ Forecasts have to beat "repeat last week" before they're used, and they show how wrong they've been

𝗨𝗻𝗱𝗲𝗿 𝘁𝗵𝗲 𝗵𝗼𝗼𝗱
⚙️ FastAPI, PostgreSQL, LightGBM, LangGraph, faster-whisper
🎨 Next.js 15, TypeScript, Tailwind, three.js (the shop "opens" when you cut the ribbon ✂️)
✅ 664 backend tests, strict typing, CI on every push, a written threat model

The honest part: no real shopkeeper has used it yet. The voice tests use synthetic speech, and the Hindi needs a native speaker's review. That's what comes next.

If you run a shop, or know someone who does, I'd love 15 minutes of feedback. 🙏

📄 Full project document: https://drive.google.com/drive/folders/1FtSuD1PuTelw9huB_Uoz9cdQK3vUowm7?usp=sharing
💻 Code: https://github.com/SDP42/vyaparai

#BuildInPublic #RetailTech #Kirana #MSME #DigitalIndia #StartupIndia #MachineLearning #AIAgents #LangGraph #FastAPI #NextJS #Python #SoftwareEngineering

---
