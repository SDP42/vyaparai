# Agents

The agents live in the API, in [`apps/api/app/services/agents/`](../apps/api/app/services/agents/). This folder only
points there. Each agent is a small [LangGraph](https://github.com/langchain-ai/langgraph) graph whose nodes call
existing, tested services. There is **no language model** in the loop, and every agent is **read-only**: it prepares
findings and drafts (reminders, order lists) for a person to check and send. Every step is stored and shown on the
Investigate page.

## Analyst agents (run on demand)

| Key | Asks | What it checks |
|---|---|---|
| `investigate_sales` | Why did sales change? | Change split into volume, mix, price and discount; products behind it; stock, costs, discounts, festivals, reviews, basket size |
| `weekly_review` | What should I do this week? | Refreshes every recommendation signal and lists the top five with reasons |
| `customer_health` | Are my customers healthy? | Regulars slipping away, repeat rate, concentration, complaints, credit that stopped being paid |
| `stock_risk` | Where is stock at risk? | Products that will run out, cash in dead stock, festivals that may strain stock, forecast freshness |

## Automation agents (on demand, or every day at a chosen hour)

| Key | Title | What it prepares |
|---|---|---|
| `morning_brief` | Start the day | Last day's sales against the same day last week, who to call for udhaar, what to order, what is expiring, whether the galla was closed, urgent alerts |
| `reorder_planner` | Plan today's orders | What to order and roughly what it costs, checked against the last cash count, plus an order list per supplier ready to share |
| `udhaar_collector` | Collect udhaar | Who to call first, who has stopped paying, and a polite reminder drafted for each (English, Hinglish or Hindi) |
| `day_end_check` | Check yesterday's close | Whether the galla was closed, whether the drawer matched, whether typed sales match the file, unusual spending |
| `expiry_clearance` | Clear expiring stock | What to take off the shelf and what to sell first this week |
| `price_watch` | Watch supplier prices | Products whose cost rose while the price stayed the same, with a suggested price |

Schedule them on the Investigate page (owner or admin). A cron entry runs whatever is due:

```bash
*/15 * * * *  cd /path/to/apps/api && uv run python -m app.agent_runner
```

Each enabled agent runs at most once per local day.

## Guarantees (tested)

- **Read-only:** a test fails if a workflow or automation module writes to the database, opens a network connection,
  starts a process or opens a file.
- **Bounded:** at most 16 node executions and 20 seconds per run; a failing node is retried once, then recorded as
  failed and the run continues.
- **Traced:** every node is stored with its input, output, attempts and time.
- **Offline:** no tracing service is enabled.

See [docs/AGENTS.md](../docs/AGENTS.md) for the design and limits.
