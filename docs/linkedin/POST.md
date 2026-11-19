# LinkedIn post

Paste the text between the lines. It is about 2,300 characters (LinkedIn allows 3,000; the first ~210 show
before "see more"). Suggested images, in order: `showcase/cover.png`, `showcase/ask.png`,
`showcase/agents.png`, `showcase/opening.png`, `images/00-repo-summary.png`, then any app screenshots from
`images/`. Attach `Vyapar-AI-Project-Document.pdf` as a document post, or put its Drive link in the first comment.

---

Most kirana and retail shops in India already have their data. A billing export, a udhaar notebook, a cash drawer counted every night. What they don't have is time to turn it into a decision before the shutter goes up.

So I built Vyapar AI: decision support for small Indian shops, in English, Hinglish and Hindi. 🛍️

What it does:
📊 Today page: yesterday's sales, who to call for udhaar, what to order, what expires
🗣️ Ask in your own words, typed or spoken: "kal kitna becha?", "Ramesh ko 200 udhaar"
💸 Galla close: counted cash against expected cash, with expenses
📈 Forecasts that must beat "repeat last week" before they're used, with ranges whose accuracy is measured
🤖 10 LangGraph agents (morning brief, reorder planner, udhaar collector, expiry clearance, price watch and more). Every one only reads data, every step is traced, and every message is a draft a person sends
👥 Five shop jobs (owner, manager, analyst, accountant, counter staff), each seeing only what that job needs; cost and margin are hidden field by field

How it's built:
⚙️ FastAPI, SQLAlchemy, PostgreSQL, LightGBM plus a Theta baseline, LangGraph, faster-whisper (Whisper medium, running on the server)
🎨 Next.js 15, TypeScript, Tailwind 4, GSAP, and a three.js cloth simulation for the opening: drag the scissors, cut the ribbon, the shop opens ✂️
✅ 664 backend tests, strict mypy, CI on every push, a licence audit that fails the build on GPL
🔒 Rotating refresh tokens, per-shop data isolation, rate limits, SSRF and upload hardening, a written threat model

Two choices I'm proud of:
1️⃣ No language model writes the answers. The assistant routes questions to tested calculations and shows its evidence, so it can't invent a number.
2️⃣ Free and permissively licensed only. No paid API keys, nothing a small shop would have to pay for later.

And being honest about where it stands: it hasn't been tested with real shopkeepers yet. The voice numbers come from synthetic speech, and the Hindi wording needs a native review. That's the next step.

461 commits, 22 phases, 31 documents. The full write-up with architecture, benchmarks, security and limits is in the document attached below. 📄

If you run a shop, or know someone who does, I'd love 15 minutes of your feedback. 🙏

#BuildInPublic #FastAPI #NextJS #LangGraph #MachineLearning #Retail #India #Kirana #SoftwareEngineering

---
