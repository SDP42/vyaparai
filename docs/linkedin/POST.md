# LinkedIn post

Paste the text between the lines. LinkedIn allows 3,000 characters; only the first two lines (about 210 characters)
show before "see more", so they carry the hook. Suggested images, in order: `showcase/cover.png`,
`showcase/ask.png`, `showcase/agents.png`, `showcase/opening.png`, `images/00-repo-summary.png`,
`images/26-github-repo.png`, then any app screenshots from `images/`.

The project document is on Google Drive and the code on GitHub (both linked in the post). The repository has no
licence file yet, so the post says "code", not "open source".

---

India has more than a crore kirana stores. Almost all of them already have their data. Almost none of them use it to decide anything. 🛍️

That gap is what I spent the last two weeks on.

𝗧𝗵𝗲 𝗽𝗿𝗼𝗯𝗹𝗲𝗺
A shop owner has a billing export, a udhaar notebook and a cash drawer counted every night. What they don't have is the time or the vocabulary to turn that into decisions:
→ Fast movers run out before the supplier visits, while slow stock ties up cash
→ A supplier raises a price quietly and margin leaks for weeks
→ Udhaar grows and nobody tracks who to call first
→ Dashboards speak "AOV" and "gross margin", not the language of the counter

𝗧𝗵𝗲 𝘀𝗼𝗹𝘂𝘁𝗶𝗼𝗻: 𝗩𝘆𝗮𝗽𝗮𝗿 𝗔𝗜
Decision support that reads the exports a shop already has and answers in English, Hinglish or Hindi, typed or spoken.
📊 A Today page: yesterday's sales, who to call for udhaar, what to order, what expires
🗣️ Ask like you talk: "kal kitna becha?" or "Ramesh ko 200 udhaar"
💸 Galla close: counted cash against expected cash, with expenses
📈 Forecasts that must beat "repeat last week" before they're used
🤖 10 LangGraph agents (morning brief, reorder planner, udhaar collector, expiry clearance, price watch) that prepare the work, with every step traced
👥 Five shop jobs, from owner to counter staff, each seeing only what that job needs

𝗪𝗵𝗮𝘁 𝗺𝗮𝗸𝗲𝘀 𝗶𝘁 𝗱𝗶𝗳𝗳𝗲𝗿𝗲𝗻𝘁
1️⃣ No language model writes the answers. Questions go to tested calculations and every answer shows its evidence, so it can't invent a number.
2️⃣ Agents only read. Nothing is ordered, sent or changed without a person; reminders are drafts the owner sends.
3️⃣ Built for Indian retail: lakh and crore formatting, festival calendars, udhaar, and Hinglish the way people actually type it.
4️⃣ Free to run. Only permissively licensed software, no paid API keys, speech recognition on the shop's own server.
5️⃣ Honest by design. Forecasts show how wrong they have been, and the docs list what is not proven yet.

𝗛𝗼𝘄 𝗶𝘁'𝘀 𝗯𝘂𝗶𝗹𝘁
FastAPI · PostgreSQL · LightGBM · LangGraph · faster-whisper · Next.js 15 · TypeScript · Tailwind · three.js
✅ 664 backend tests, strict typing, CI on every push, a written threat model

Where it stands: no real shopkeeper has used it yet, the voice tests use synthetic speech and the Hindi needs a native review. That's the next step, and the reason for this post.

If you run a shop, or know someone who does, I'd love 15 minutes of feedback. 🙏

📄 Full project document: https://drive.google.com/drive/folders/1FtSuD1PuTelw9huB_Uoz9cdQK3vUowm7?usp=sharing
💻 Code: https://github.com/SDP42/vyaparai

#BuildInPublic #RetailTech #Kirana #MSME #DigitalIndia #StartupIndia #MachineLearning #AIAgents #LangGraph #FastAPI #NextJS #Python #SoftwareEngineering

---
