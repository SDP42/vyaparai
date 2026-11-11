# ADR 0008: Benchmark data

Status: accepted, 2026-11-11

## Context

Metrics and forecasts need data with known answers, and the product needs a believable demo. Public retail
datasets exist (see [RESEARCH.md](../RESEARCH.md#3-starter-datasets)) but their licences, geography and
language do not match an Indian kirana or garment shop, and real customer data must never enter the repository.

## Decision

1. **Synthetic first.** `scripts/generate_demo_data.py` writes seeded sales exports with known totals, so metric
   tests assert exact numbers. It is the only dataset committed to the repository.
2. **No public dataset is bundled.** UCI Online Retail II (CC BY 4.0) is the one candidate that is both
   permissive and has returns, and may be used for a one-off forecasting benchmark run outside the repository,
   with attribution in the report. Olist (CC BY-NC-SA) and M5 (competition terms) are excluded.
3. **Real accuracy is measured on real shops.** Every accuracy figure in the docs that comes from synthetic or
   self-written sets says so, and the plan is to measure on a consenting shop's own export.

## Consequences

- Demo numbers are illustrative and labelled as such.
- Forecast and review claims stay modest until a real shop's data has been through them.
