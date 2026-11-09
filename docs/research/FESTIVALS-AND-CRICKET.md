# Festivals and Cricket as Retail Demand Drivers

Research note for Vyapar AI. Prepared 2026-11-09. Forward period 2026-11-09 to 2028-12-31, extended backwards to 2024-01-01 so models can learn from past years. The dated dataset is in `data/events/events.csv` (320 rows: 129 forward, 191 historical); recurring monthly observances are in `data/events/recurring_observances.md`.

## 1. Why something is "on" almost every day

India runs several calendars at once, and almost every day carries some observance for some community.

- **Lunar-solar (Hindu) calendar.** Months follow the moon, with an extra month added about every three years, so festival dates move across the Gregorian calendar (Diwali has fallen between mid-October and mid-November). Two month conventions exist: north India usually counts months from full moon to full moon, while Maharashtra, Gujarat, Karnataka and Andhra Pradesh count from new moon to new moon. The same festival can therefore fall in a differently named month, and regional almanacs sometimes differ by a day.
- **Solar festivals.** Makar Sankranti (about 14-15 January), Baisakhi (13-14 April), Vishu, Puthandu and Pohela Boishakh (14-15 April) follow the sun and shift very little.
- **Islamic calendar.** Purely lunar, about 11 days earlier each year, and the exact day depends on moon sighting, so any date can move by a day.
- **Fixed-date holidays.** Republic Day, Independence Day, Gandhi Jayanti, Christmas.
- **Recurring monthly observances.** Ekadashi (twice a month), Pradosh, Sankashti and other fasting days, Amavasya and Purnima, monthly Sankranti, and weekday observances such as Monday fasts in Shravan or Thursday and Saturday customs. These recur every 14-15 days but are small events.
- **Regional and community festivals.** Dozens of state-level festivals (Bihu, Onam, Durga Puja, Ganeshotsav, Rath Yatra, Lohri) and community days (Guru Nanak Jayanti, Mahavir Jayanti, Parsi New Year).

**What matters to retail.** Only a small share moves sales. An observance matters when it (a) involves buying things (gifts, new clothes, gold, sweets, puja goods), (b) changes what a household eats for several days, or (c) closes shops or changes footfall. Most monthly observances do none of these for most shops and should be treated as background noise unless the shop sells fasting foods or serves a community that observes them.

## 2. Tier system

| Tier | Meaning | Examples in the dataset |
|---|---|---|
| 1 | National or very large multi-day peaks, strong effect across most categories | Diwali season (Dhanteras to Bhai Dooj), Holi, Eid al-Fitr, Eid al-Adha, Navratri/Dussehra/Durga Puja, Ganesh Chaturthi, Raksha Bandhan, Onam, Pongal/Makar Sankranti, Baisakhi, Ugadi/Gudi Padwa, Akshaya Tritiya, Karwa Chauth, Bhai Dooj, Chhath, Christmas and New Year, wedding-season windows, IPL and World Cup windows |
| 2 | Large regional or category-specific | Maha Shivaratri, Ram Navami, Janmashtami, Chaitra Navratri, Lohri, Rath Yatra, Guru Nanak Jayanti, Govardhan Puja, Ramadan, Shravan month, India Test series |
| 3 | Small recurring observances with product-specific effects | Ekadashi, Pradosh, Sankashti, Vasant Panchami, Pitru Paksha, public holidays that create long weekends, individual lower-profile matches |

Tiers are a prior, not a measurement. A tier-3 day can matter a lot for a fasting-food shop and nothing for a hardware shop.

## 3. Category effects, lead times and tails

Sizes here are qualitative. For scale, the traders' body CAIT estimated Diwali 2025 trade at about Rs 5.4 lakh crore in goods plus Rs 65,000 crore in services, roughly 85% of it through traditional markets, which is why small shops are the right place to model this. These are survey estimates by an industry body, not audited data.

| Category | Pattern | Lead | Peak | After |
|---|---|---|---|---|
| Sweets and dry fruits | Gift boxes, mithai, sugar/ghee/khoya; strongest for Diwali, Raksha Bandhan, Bhai Dooj, Eid, Holi | 7-14 days (Raksha Bandhan 7-10; Diwali 14-21) | Day before and day of | Sharp drop within 1-2 days |
| Gifting | Dry-fruit packs, small gifts, crockery; builds with Diwali, Rakhi, weddings, Christmas | 10-21 days | Last 3 days | Lull |
| Apparel | New clothes for Diwali, Eid, Durga Puja, Onam, Pongal, weddings, Navratri (garba outfits) | 15-30 days (Durga Puja about 30) | Final week | Dip, then clearance sales |
| Jewellery and gold | Dhanteras, Akshaya Tritiya, wedding season, Dussehra | 3-7 days | Festival day | Mild lull |
| Staples; oil, ghee, sugar, flour | Bulk stock-up before Diwali, Eid al-Adha, Baisakhi, Onam, Pongal; community feasts | 7-14 days | Final 3-5 days | Normalises |
| Dairy and paneer | Milk, curd, ghee, paneer for sweets, Janmashtami, Maha Shivaratri, Eid, weddings; also fasting days | 1-3 days | Eve and day | Quick return |
| Fruits and flowers | Puja flowers, garlands, fruit for fasting, Chhath (fruit, sugarcane), Navratri | 1-3 days | Day before | Immediate fall |
| Fasting foods | Sabudana, kuttu and singhara flour, rock salt, makhana, potatoes, fruit, milk during Navratri, Shivaratri, Ekadashi, Shravan Mondays | 2-5 days | First fast days | Falls on completion |
| Non-vegetarian dip | Meat, fish and egg demand falls during Navratri (north/west), Shravan (north), Pitru Paksha (many families), Maha Shivaratri, Ram Navami, and around Jain holidays. Counter-effect: Eid al-Adha and, after dusk, Ramadan spike meat demand | Starts at day 0 | Whole period | Rebound afterwards |
| Firecrackers | Concentrated in the last few days before Diwali, subject to local bans | 5-7 days | Final 2 days | Falls to near zero |
| Cleaning and household | Detergents, paints, brooms, utensils; begin 2-3 weeks before Diwali | 14-21 days | One week before | Falls abruptly |
| Beverages and snacks | Holi, Diwali parties, New Year, cricket evenings, summer | 1-3 days | Event evening | Immediate |
| Electronics | Dhanteras, Dussehra, Akshaya Tritiya, Ugadi, big matches and tournaments (TVs) | 7-14 days | Festival day | Lull |
| Travel | Diwali/Chhath/Holi homecoming, Christmas, long weekends | 14-45 days | Days around holiday | Return peak |
| Personal care | Karwa Chauth, Bhai Dooj, Eid, Holi, weddings | 3-7 days | Day before | Mild dip |

**Post-festival lull.** After the main day, demand typically falls below normal for several days because households have stocked up. For Diwali, the first week afterwards (Govardhan Puja and Bhai Dooj aside) is the weakest. Model it with a tail window.

**Regional differences.**
- *North:* Diwali, Dussehra, Holi, Karwa Chauth, Raksha Bandhan, Lohri, Baisakhi; Navratri is largely about fasting.
- *West:* Ganeshotsav, Gudi Padwa, Navratri-garba, and Diwali with Gujarati new year the day after Lakshmi Puja.
- *South:* Pongal, Ugadi, Onam, Vishu, Ganeshotsav, Deepavali (earlier in the day, often oil bath); Diwali weighs less than in the north.
- *East:* Durga Puja is the biggest event (shopping starts about a month before), Kali Puja around Diwali, Chhath in Bihar and eastern UP, Pohela Boishakh.

## 4. Other seasonal drivers

- **Wedding season.** Almanac windows for 2026-27 run roughly from the day after Dev Uthani Ekadashi (21 Nov 2026) to mid-December, pause for about a month, and resume mid-January to mid-March, then mid-April to early July. Dates are not uniform; use them as windows only. Dates beyond March 2027 in the dataset are estimates.
- **Harvest and monsoon.** Harvest festivals (Pongal, Baisakhi, Bihu) coincide with rural cash inflow; monsoon months slow footfall and shift sales to staples and umbrellas/rain gear. Sources on shop-level effects were thin.
- **School exams and holidays.** Board exams in February-March and summer vacations from mid-May to June change stationery, snack and travel demand. Exact calendars are set by state boards and were not researched here.
- **Payday cycles.** Many salaried shoppers buy larger baskets in the first week of the month; the effect varies by area. No reliable public source was found, so the model should detect it from the shop's data.

## 5. Cricket

**Why it matters.** Cricket produces concentrated evening demand: snacks, cold drinks, ice, party packs, takeaway and quick-commerce orders. Reports from delivery apps mention order spikes during match hours, with brands forecasting roughly 25% more orders for IPL 2026 and reports of food orders up about 30% during matches in an older Swiggy season; these are company claims and not audited. Large matches also lift TV and set-top purchases in the days before a tournament.

**Match days vs tournament windows.** A tournament window (IPL, World Cup) creates a diffuse seasonal lift; an individual match creates a sharp same-day effect. Evening matches (7:30 pm IST for most IPL games and T20Is) move shopping to the late afternoon and shift deliveries into the evening; the day after can see a small morning effect. Daytime Tests and 2 pm ODIs mostly matter on weekends.

### Confirmed and unconfirmed schedule

| Event | Dates | Status |
|---|---|---|
| IPL 2026 | Final on 31 May 2026, Ahmedabad; Royal Challengers Bengaluru won | Finished, outside forecast period |
| India in New Zealand (5 ODIs, 2 Tests) | ODIs 4, 7, 10, 13, 15 Nov; Tests 19-23 Nov and 27 Nov-1 Dec 2026 | Published by NZC; played in the IST morning |
| India v Sri Lanka (3 ODIs, 3 T20Is) | ODIs 13, 16, 19 Dec; T20Is 22, 24, 27 Dec 2026 | BCCI published; first ODI venue reportedly moved from Delhi |
| India v Zimbabwe (3 ODIs) | 3, 6, 9 Jan 2027 | BCCI published |
| India v Australia (5 Tests) | 21 Jan to 3 Mar 2027 | BCCI published |
| IPL 2027 | Reported plan 10 Mar to 15 May 2027; an earlier announcement said 14 Mar to 30 May | Not final |
| ICC Men's World Cup 2027 | 2 Oct to 21 Nov 2027; India v Australia 7 Oct, v Pakistan 10 Oct; semi-finals 17-18 Nov; final 21 Nov | ICC schedule published |
| IPL 2028 | No dates found | Estimated March to May only |
| ICC Men's T20 World Cup 2028 | Reported 21 Oct to 19 Nov 2028 (Australia and New Zealand) | Not confirmed from an official page |
| 2027-28 India home season; Asia Cup; India in England 2027 | Not found | Not announced as of this research; the ICC's 2027-2031 touring programme was due in November 2026 |

**Key interaction.** The 2027 World Cup overlaps Navratri, Dussehra, Karwa Chauth and Diwali in India, so cricket effects and festival effects will overlap and should not be double counted. South African matches reach India in the afternoon and evening.

## 6. Limits and how a model should use this

- **Known in advance:** event dates, durations, and (for cricket) match days. These are features a model can use well ahead of time.
- **Uncertain:** magnitude. The same festival can lift sweets 3x in one shop and 1.2x in another depending on location, neighbourhood, community and stock.
- **Learn from the shop.** Effect sizes (lead, peak and tail) must be estimated from the shop's own history with the event table as input features, not hard-coded. With less than a full year of data, use hierarchical or shrinkage estimates by category and tier rather than trusting a single observed festival.
- **Use windows, not just dates.** `lead_days` and `tail_days` in the dataset are priors for window shapes; the model should adjust them.
- **Do not double count.** Overlaps (Navratri with a World Cup, Diwali with Dhanteras) need interaction handling.
- **Moon-based dates can slip a day;** treat low-confidence rows as soft features.
- **Source caveats.** Many calendar sites are commercial and copy each other; gazette lists are Delhi-centric and published only up to about a year ahead; effects here are largely qualitative, with few audited numbers; trade body figures (CAIT) are survey-based.

## Verification notes

**Anchors checked.** Diwali (Lakshmi Puja) 2026 is 8 Nov 2026 in both the gazetted 2026 holiday list and a festival calendar. Diwali 2027 (29 Oct) matches the DoPT 2027 gazetted list and an almanac. Dussehra 2027 (9 Oct), Holi 2027 (see below), Eid al-Fitr 2027 (10 Mar), Eid al-Adha 2027 (17 May), Raksha Bandhan 2027 (17 Aug), Ganesh Chaturthi 2027 (4 Sep), Onam 2027 (12 Sep), Karwa Chauth 2027 (18 Oct) and Chhath 2027 (4 Nov) agree between the DoPT lists and an almanac. 2028 dates come from almanac and calendar sites only, because no government list exists yet.

**Confidence counts, forward rows (129).** High 80, medium 31, low 18. See the historical section below for the 191 rows covering 2024-01-01 to 2026-11-08.

**High confidence:** most 2026-27 dates backed by both the DoPT gazetted/restricted lists and an almanac; BCCI-published India home fixtures (Dec 2026 to Mar 2027); the ICC World Cup 2027 window, India matches vs Australia and Pakistan, semi-finals and final; most 2028 main festivals where three calendar sources agree (Holi, Diwali, Dussehra, Ganesh Chaturthi, Raksha Bandhan, Onam, Chhath, Bhai Dooj).

**Medium confidence:** Holi 2027 (gazette says 23 Mar, almanac 22 Mar; row spans 21-23 Mar); Dhanteras 2027 and 2028 (one almanac differs by a day); Eid dates for 2028 (moon sighting); Karwa Chauth 2028 (6 or 7 Oct); Navratri/Durga Puja 2028; Janmashtami 2028 (12 or 13 Aug); Makar Sankranti/Pongal 2028 (14 or 15 Jan); New Zealand tour dates (matching sources but no BCCI page); Shravan 2027 bounds; wedding windows for Nov 2026 to Mar 2027 (almanac lists vary by city); Dev Uthani Ekadashi 2026.

**Low confidence (estimated):** IPL 2027 window (reports conflict; not announced officially) and IPL 2028; T20 World Cup 2028 window; wedding windows after March 2027; Ramadan start dates; Guru Nanak Jayanti 2028; Lohri 2028; Muharram, Milad-un-Nabi and Buddha Purnima 2028; Vishu/Puthandu/Bihu 2028; Shravan 2028; New Year Eve 2028.

**Could not confirm:** IPL 2027 and 2028 official dates; India's 2027-28 home season and any India tour of England in 2027; India's other World Cup 2027 Super 7 fixtures and kick-off times in IST; official 2028 gazette; start-of-fast dates (Ramadan) that depend on moon sighting; exact wedding muhurat lists beyond March 2027; whether the Sri Lanka first ODI moved to Visakhapatnam and on what date.

**Method note.** Effect notes are written in neutral language from general retail knowledge, supported where possible by a handful of public reports (CAIT, quick-commerce coverage). Category magnitudes are not measured in any public source consulted.


### Historical rows (2024-01-01 to 2026-11-08, 191 rows)

**Counts.** Festival 93, cricket 56, holiday 25, observance 9, season 8. Confidence: high 113, medium 69, low 9. Whole file: 320 rows, ids unique.

**Sources.** Gazetted and restricted holiday lists for 2024, 2025 and 2026 come from the DoPT orders as reproduced on StaffNews (Delhi/New Delhi offices), cross-checked against the Drik Panchang yearly festival lists. Dhanteras, Sharad Navratri and Akshaya Tritiya use separate almanac pages. Cricket windows come from Wikipedia season pages, BCCI and ICC releases, and news reports.

**High confidence:** most festival and holiday dates where a gazette or restricted list and an almanac agree; IPL 2024, 2025 and 2026 windows and finals (2024: 22 Mar to 26 May, Kolkata won; 2025: 22 Mar to 3 Jun with a pause 9-16 May, RCB won; 2026: 28 Mar to 31 May, RCB won); T20 World Cup 2024 window and final (29 Jun); T20 World Cup 2026 window, USA match and final (8 Mar); Champions Trophy 2025 window and final (9 Mar); Asia Cup 2025 window and final (28 Sep); Women's World Cup 2025 window and final (2 Nov); Border-Gavaskar Trophy 2024-25.

**Medium confidence:** holidays with a single source (Buddha Purnima, Mahavir Jayanti, Good Friday, Muharram, Milad-un-Nabi, Guru Purnima); Lohri 2024 (13 or 14 Jan); Eid al-Fitr 2024 (10 or 11 Apr) and 2026 (20 or 21 Mar); Vasant Panchami 2025 (2 Feb in the almanac, 14 Feb with a mismatched weekday in the restricted list); Baisakhi 2025 (13 or 14 Apr); Chhath 2025 (27 or 28 Oct); Dhanteras 2024 and 2025 (one almanac fetched, dates match common reporting); Naraka Chaturdashi (single list or conflicting); Diwali 2024 is recorded as 31 Oct to 1 Nov because the gazette and the almanac differ; Wedding windows for Nov-Dec 2025 and Feb-Mar 2026 (partial regional lists); most individual bilateral series and India matches inside ICC events, where only one detailed source was read (Wikipedia schedule pages), and the T20 World Cup 2026 Super 8 and semi-final entries, which use scheduled dates rather than match reports.

**Low confidence (estimated):** Ramadan start dates 2024-2026 (derived from Eid); wedding windows for Jan-Jul 2024, Nov-Dec 2024, Jan-Jul 2025 and Apr-Jul 2026 (derived from solar ingress and Ekadashi dates, not from published muhurat lists).

**Corrections to forward rows.** `govardhan-puja-2026` now ends 2026-11-10 because an almanac gives 10 Nov while the gazette restricted list gives 9 Nov. `holi-2027` and `dhanteras-2027` had only their effect notes updated (dates unchanged), see below.

**Settled or not.**
- Holi 2027: three almanac sources (Drik Panchang, Hindutone, Vrindavan tourism) agree Holika Dahan is 21 Mar and Rangwali Holi is 22 Mar; the full-moon tithi runs from the evening of 21 Mar to the afternoon of 22 Mar. The gazette shows Holi as 23 Mar, so the row keeps the span 21-23 Mar at medium confidence. Colour-play day is most likely 22 Mar; the government holiday is 23 Mar.
- Dhanteras 2027: one almanac lists 27 Oct, another (Drik puja page) lists 26 Oct, and a calendar site contradicts itself. Not settled; the row stays at 27 Oct with medium confidence and a note that the peak window is 26-27 Oct.

**Could not confirm (historical).** Pitru Paksha dates for 2024-2026 (not searched); India's 2023-24 South Africa tour in January 2024; India's mid-2024 tours (Zimbabwe, Sri Lanka); the Bangladesh tour mentioned for August 2025; India's June 2026 Afghanistan Test, August 2026 Sri Lanka Tests and September 2026 Bangladesh and Afghanistan T20Is (scheduled in a single pre-season article, no confirmation they were played); results and exact dates of India's individual T20 World Cup 2024 and 2026 group matches beyond those listed; whether any IST start times differ from the typical ones given in notes; match-level IPL fixtures (only seasons and finals are listed).
