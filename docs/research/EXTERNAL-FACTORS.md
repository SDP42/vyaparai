# External factors in forecasting: weather, inflation, trade and more

_2026-11-09. Sources are vendor pages, news and a few papers; none is a rigorous grocery benchmark.
Treat every claim as a hypothesis the backtest must confirm._

## What the evidence says

| Factor | Finding | Source |
|---|---|---|
| Weather | Helps most for seasonal and weather-sensitive items (a thesis reports error cuts up to 45 %, an upper bound for seasonal goods). For everyday grocery the day-to-day effect is small ("people have to eat"); effects show up through interaction with weekday and promotions. Temperature acts roughly linearly, rainfall non-linearly. | [Relex](https://www.relexsolutions.com/resources/improve-demand-forecasting-accuracy-by-factoring-in-weather-impacts/), [SME food demand study](https://iieta.org/download/file/fid/120320), [Unil thesis](https://serval.unil.ch/notice/serval:BIB_35E2A0F51104) |
| Future values | A regressor must be known (or forecast) for the forecast period; training on actual weather but predicting with forecast weather is optimistic. | [ETNA tutorial](https://nbviewer.org/github/tinkoff-ai/etna/blob/1.9.0/examples/exogenous_data.ipynb) |
| Trade policy | India imports about 60 % of its edible oil, so duty changes and the rupee move shelf prices (a 2025 duty cut was expected to lower retail oil prices 5–6 % over weeks, not days). | [The Week](https://www.theweek.in/wire-updates/business/2025/06/02/ccm4-biz-edible-oil.html), [Outlook Business](https://www.outlookbusiness.com/news/retail-prices-of-cooking-oils-may-fall-after-duty-cut-industry-body-ivpa) |
| Inflation | Cost-to-price pass-through is modest and non-linear in India; sticky inflation pushes consumers to trade down and squeezes small-retailer margins. No quantified elasticities for small shops were found. | [RBI Bulletin](https://www.rbi.org.in/Scripts/BS_ViewBulletin.aspx?Id=21270), [RAI survey coverage](https://www.whalesbook.com/news/English/consumer-products/India-Retail-Sales-Grow-5percent-In-May-QSRs-Lead-As-Inflation-Persists/6a3aabb0a1c5bf084329ec3a) |

## The key distinction: known in advance, or not?

| Group | Examples | Use in the model |
|---|---|---|
| **Known ahead** | Calendar, festive season, paydays, school holidays, planned promotions, weather forecast (about 14 days) | Direct features. Festive and payday are already in; weather is added now as an optional feature |
| **Not known ahead** | Inflation prints (monthly, lagged), fuel, exchange rate, commodity prices, duty changes, export curbs | Not direct demand features. They act on **cost and price**, so they feed margin alerts, price-change features and scenarios, and the model's recent-data recalibration picks up their lasting effect |

## Data sources

| Signal | Source | Cost and caveats |
|---|---|---|
| Weather history and forecast | [Open-Meteo](https://open-meteo.com/) | No key. Free tier is **non-commercial** (CC BY 4.0, attribution); a paid plan or self-hosting is needed for a commercial product. Verify the current [terms](https://open-meteo.com/en/terms). IMD is an alternative. Only coordinates are sent, never customer data. |
| Food and general CPI | MoSPI CPI portal; copies on India Data Portal | No confirmed public API; monthly, lagged. Start with a monthly manual or scheduled import |
| Fresh-produce market prices | Agmarknet via data.gov.in | Free key; reference prices only |
| Duty, export-policy changes | Government notifications | Curated events list, entered by us, with effective dates |
| Festive and local events | Own dated table | Moves every year; maintained by us |

## How we will include them (layered)

1. **Now (Phase 4c): optional covariates in the engine.** The engine accepts daily covariates known for the forecast period (temperature, rain). It runs the backtest **with and without** them and keeps them only if the pooled error improves by at least 2 % (relative). The decision and both errors are stored in the model card.
2. **Cost and price shock monitor (Phase 14/15B).** Detect cost rises from purchase data and from curated events (duty change, CPI food spike); alert on margin leaks and suggest price moves. This is where inflation and trade matter most.
3. **Regime flags (later).** Slow macro signals only once a workspace has two or more years of history; with less, they cannot be learned.
4. **Scenario view (Phase 16).** "What if edible-oil cost rises 8 %?" using shop-specific elasticities once measured; not guessed.

## Pitfalls we design around

- **Leakage:** train on the forecast that existed at each origin (Open-Meteo's historical-forecast data), not on perfect hindsight weather.
- **Small data:** a shop with six months of history cannot learn yearly macro effects; the engine ignores such signals instead of overfitting.
- **Per-category effects:** weather may help beverages and not atta; selection is per run and reported.
- **Outage:** if the weather feed fails, fall back to the no-covariate model and say so.
- **Licensing and privacy:** use a commercial plan or self-host before launch; send coordinates only.

## Acceptance test

A covariate ships only if (a) a **positive control** (synthetic demand that truly depends on it) shows the pipeline uses it, (b) a **negative control** (random noise) does not make forecasts worse, and (c) on real data it improves the held-out WAPE by at least 2 % without worsening bias. Points (a) and (b) are automated tests; (c) needs real shop data and is run per workspace.

## Open decisions

- Weather provider and plan for commercial use (Open-Meteo paid vs self-hosted vs IMD).
- Which shop location to use (city centre, or a pincode if the owner provides it).
- Who maintains the curated events list (duty and export-policy changes).
