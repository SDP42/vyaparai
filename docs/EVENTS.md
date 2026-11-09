# Festivals, holidays and cricket: how the product uses them

Research and sources: [research/FESTIVALS-AND-CRICKET.md](research/FESTIVALS-AND-CRICKET.md) and
[research/RECURRING-OBSERVANCES.md](research/RECURRING-OBSERVANCES.md).

## The table

`apps/api/app/data/events.csv`: 320 dated events from 2024-01-01 to 2028-12-31 (past dates teach the model, future ones
warn the shop). Columns: id, name, date_start, date_end, category (festival, holiday, observance, cricket, season),
tier (1 big peak, 2 regional peak, 3 smaller effect), scope, regions, lead_days, tail_days, demand_categories,
effect_notes, date_basis (gazette, panchang, published_schedule, estimated), confidence, sources.
Dates are certain or carry a confidence label; **effect sizes are never hard-coded**, they are learned from each shop.

## Regions

Some festivals belong to certain states or zones. Each shop has a state (set directly on the Festivals page, or from
its city). An event is **core** for the shop when its state is named (or the event lists only zones and the shop is in
one), **zone** when other states are named but the shop is in a listed zone (weaker, weight 0.5), and hidden otherwise.
With no state set, only national-scope events show. Some states belong to two zones (Rajasthan, Uttar Pradesh).

## How it is used

| Where | How |
|---|---|
| Forecast | Two daily signals (festival intensity, 0 to 1 with a build-up and fade; cricket window flag) are tried as a group and kept only if the backtest improves by 2 %. Distance to the nearest big festival is a model feature. Warnings name the festival. |
| Festive boost | The owner can add 10 to 50 % on tier-1 festival days; labelled as their assumption |
| Festivals page | Upcoming events for the shop's region, the products each touches, stock cover and risk, and what past events did to the shop's sales |
| Alerts | "Diwali starts in 9 days: 3 of your products may run out" (festivals of tier 1 or 2 only) |
| Observed effect | Average daily sales in an event's window against the 28 days before it, overall and for the products it touches, shown only with a quiet month before it |

Overlapping events do not stack: the strongest one counts on each day.

## Keeping the table current

1. Once a year (and when the government publishes the next gazetted list), add the new year's rows with sources.
2. Re-check low and medium confidence dates close to their date; lunar dates can shift by a day, cricket schedules change.
3. Keep ids unique and `date_end >= date_start`; the test suite checks the table's consistency and key anchors.
4. Do not copy source text; describe effects in your own words.

## Known gaps

IPL 2028 and the 2027-28 India home season were not announced when the table was built; some wedding-season windows and
Ramadan starts are estimates; match-level IPL fixtures are not included, only seasons and finals.
