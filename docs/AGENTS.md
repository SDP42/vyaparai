# Agent workflows

Bounded, traced, read-only analyst workflows built as LangGraph graphs (`app/services/agents/`).

## What they are (and are not)

A workflow is a small graph of nodes. Each node calls an existing, tested service and returns numbers and findings; the graph decides which node runs next. There is **no language model** in the loop. That is a design choice, not a gap:

- every step is inspectable and reproducible, and can be shown to the owner;
- text from reviews or documents is only ever data, so nothing hidden in it can steer the workflow;
- LangGraph is used for what it is good at here (explicit nodes, conditional edges, state), with our own recorder for the trace.

## Guarantees (tested)

- **Read-only**: only service reads; a test fails if the workflow module contains writes, network or process calls.
- **Bounded**: at most 16 node executions and 20 seconds per run; a node that fails is retried once, then recorded as failed and the run continues with what it has; a budget stop is recorded as "skipped" and the run still ends with a conclusion.
- **Traced**: every node is stored as a step (input, output, attempts, milliseconds, error). The Investigate page shows them.
- **Offline**: no tracing service is enabled (a test checks the LangSmith variables are off).
- **Audited**: each run is logged with who started it.

## Workflows

**investigate_sales** ("why did sales change?"): scope the period and its comparison, compare net sales, stop early if the change is under 3% ("no material change"), otherwise split the change into volume, mix, price, discount and new/discontinued effects, find the products behind it, then check stock (a falling product that is low now), costs and supplier prices, discounts, the festival calendar (a festival in one period and not the other), reviews, and orders versus basket size. Findings are marked *measured* (a share of the actual change) or *worth checking* (context, with a fixed lower weight) and ranked. The conclusion says what the numbers show and that this is not proof of why customers behaved this way.

**weekly_review** ("what should I do this week?"): refresh every recommendation signal, read alert counts, list the top five suggestions with reasons.

## Limits

- Weights are transparent rules (share of the change; fixed weights for context), not learned. They order findings; they are not probabilities.
- The stock check sees today's stock, not the position during the period, so it can only suggest a possibility.
- Two workflows so far; adding one means adding nodes that call existing services.

## API

`GET /workspaces/{id}/agents/workflows` · `POST .../agents/runs` `{workflow, date_from, date_to}` (analyst) · `GET .../agents/runs` · `GET .../agents/runs/{run}` (with steps)
