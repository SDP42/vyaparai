# Ask: the plain-language assistant

Ask in English, हिन्दी or Hinglish ("pichle hafte ki bikri", "what should I order?"). The reply is built from read-only tools over the same numbers as the dashboards, with a link to the page that shows them. Typing or voice (the browser's own speech recognition, when available).

## How it works

1. **Understand** (`assistant/nlu.py`): rule-based, so every decision is a visible keyword or phrase. It detects language, intent (sales, why, top and slow products, customers, stock, dead stock, forecast, alerts, margin, supplier prices, reviews, festivals, help) and a period (today, yesterday, last week, last 7 days, last month, a named month, this year), in three languages. "Kal" means yesterday for sales and tomorrow for forecasts.
2. **Run one typed tool** (`assistant/tools.py`), which calls the existing services. If the asked period has no sales it says so and uses the latest 30 days instead, naming the date range.
3. **Write the answer** (`assistant/replies.py`) from the tool's numbers in the asker's language. No number is generated; all are formatted from the result (Indian digit grouping).
4. **Fallback**: questions the numbers cannot answer go to document search; if that finds nothing, the assistant says it did not understand and lists what it can do. It does not guess.

## Measured

A fixed set of 66 questions (en/hinglish/hi) in `tests/test_assistant.py` routes 100%, but keywords were added for the misses after the first run (it started at 91%), so that is a development figure. Unseen phrasing will do worse; a wrong route shows its intent and period on the answer so the user can see it.

## Limits

- Follow-ups work through a small context (previous intent, period and product) that the browser sends back; it is not stored on the server and covers one step back.
- Keyword routing can be pulled the wrong way by a stray business word; policy-style words route to the documents first to reduce this.
- Products are found by their distinctive words (all words for short names, 60% for long ones, at least one of 4+ letters); an unusual spelling or a Hindi product name is not matched.
- Forecast accuracy is quoted from the stored backtest, including when it is poor.
- With a persona assigned, the assistant only answers that job's questions and refuses the rest ([PERSONAS](PERSONAS.md)); questions can also be spoken ([VOICE](VOICE.md)). Spoken Hindi arrives spelt by ear, so Devanagari words are also matched on their consonant skeleton with one slip allowed.

## Product questions, follow-ups, evidence and streaming

- "how is Weekly selling", "stock of Steady", "forecast for Rare" run the same calculations filtered to that product; a test checks the number equals the filtered dashboard.
- "and Weekly?" or "what about last 7 days" after an answer reuse its intent, period and product. Without context the same words are not guessed at.
- Every answer carries an evidence list (label, value, source such as `metric:net_sales@v1`) shown in a collapsible panel.
- `POST .../assistant/stream` sends the real recorded steps (understood, tool run with milliseconds, done), then the answer, evidence and the full result as server-sent events. The answer is computed before streaming begins, so the steps are not an animation.
- "What should I do this week?" lists the top recommendations.

## API

`POST /workspaces/{id}/assistant/ask` `{question}` returns intent, language, period, answer, rows, link, note and suggestions.
