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

- No follow-up memory: each question stands alone.
- Keyword routing can be pulled the wrong way by a stray business word; policy-style words route to the documents first to reduce this.
- Product-specific questions ("sales of Basmati rice") are not yet supported; the product matcher exists and is the next step.
- Forecast accuracy is quoted from the stored backtest, including when it is poor.

## API

`POST /workspaces/{id}/assistant/ask` `{question}` returns intent, language, period, answer, rows, link, note and suggestions.
