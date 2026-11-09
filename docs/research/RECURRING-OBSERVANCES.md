# Recurring observances (Tier 3)

Many observances in India repeat on a fixed lunar or solar rhythm. They are too frequent to list as individual event rows, so this note describes them as rules. No specific dates are given here; generate them from a published almanac or a panchang library, and expect a one-day difference between regions and between sources.

## How the rhythms work

The Hindu lunar month has two halves of about 15 days each, one waxing (toward full moon) and one waning (toward new moon). Each half is divided into 15 lunar days called tithis, and a tithi does not match a civil day: it can start at any hour and may span two dates, or be skipped. That is why the same observance can fall on different dates in different cities and almanacs. A solar rhythm, by contrast, follows the sun's entry into a zodiac sign and shifts very little.

| Observance | Rhythm | Typical retail relevance | Main categories |
|---|---|---|---|
| Ekadashi | The 11th tithi of each half, so twice a month (about 24 a year) | Fasting households switch to fruit, milk, sabudana, kuttu and singhara flour, rock salt, potato; meat and onion-garlic items dip | fasting_foods; fruits_flowers; dairy; non_veg_dip |
| Pradosh | The 13th tithi of each half, observed at dusk | Small lift in fruit, milk and flowers | fasting_foods; fruits_flowers; dairy |
| Sankashti Chaturthi | The 4th tithi of the waning half, monthly; stronger variants when it falls on a Tuesday | Modak ingredients, flowers, fruit; mostly west and south | fruits_flowers; sweets_dryfruits |
| Amavasya | New moon, monthly | Puja goods; some avoid new purchases or travel; larger ones (Diwali, Mahalaya) are listed as events | fruits_flowers |
| Purnima | Full moon, monthly | Community pujas, sweets, fruit and flowers; Guru Purnima, Raksha Bandhan, Kartik Purnima and Holi sit on purnimas and are listed separately | sweets_dryfruits; fruits_flowers |
| Monthly Sankranti | Solar ingress, around the 13th-17th of each month | Minor; Makar Sankranti in January is a main event | sweets_dryfruits |
| Weekday observances | Mondays in Shravan, Tuesdays and Saturdays (meat avoidance in many north-Indian households), Thursdays in some traditions, Fridays for congregational prayers | Persistent weekday patterns for meat and fish shops and for footfall | non_veg_dip; fasting_foods |
| Month-long periods | Shravan, Pitru Paksha, Ramadan, Chaturmas | Whole-month shifts in meat, fasting food, dairy and dry-fruit demand | non_veg_dip; fasting_foods; dairy |

## What matters for retail and what is noise

Most of these matter only to a narrow set of shops and products. The effects that are real but small:

- **Fasting foods, fruit, milk and flowers.** Sabudana, kuttu and singhara flour, makhana, rock salt, potatoes, bananas and seasonal fruit rise on Ekadashi and during fasting festivals. A shop in an area with many observing households sees a visible lift; a mixed or non-vegetarian neighbourhood may see none.
- **Non-vegetarian dips.** Meat, fish and egg sales fall on observance days and sharply in months of widespread avoidance (Shravan in north India, Pitru Paksha, Navratri). The dip is stronger in vegetarian-majority areas and weaker in coastal, eastern and Muslim-majority areas. Ramadan and Eid al-Adha push the other way.
- **Flowers and puja items.** Daily demand with small bumps on purnima, amavasya and chaturthi; demand also changes with weekday.

Everything else (for example most pradosh days) is background noise for a general store and should not drive forecasts on its own.

## Regional differences

- Month naming differs: north India counts months from full moon to full moon, while Maharashtra, Gujarat, Karnataka and Andhra Pradesh count from new moon to new moon, so the same festival can sit in a differently named month.
- Observances shift by one day between almanacs because of local sunrise and tithi timing.
- Practices vary by community: Tuesday and Saturday meat avoidance is a north and central pattern; Thursday observances are more common in the south and west; Bengal and the East follow their own Durga Puja and fasting calendar.
- Islamic observances follow a separate lunar calendar and depend on moon sighting.

## How a forecasting model should use them

- Encode them as rules, not as hand-entered rows. Create boolean or categorical flags (for example `is_ekadashi`, `is_shravan_monday`, `fast_month`) from an almanac library or published panchang, computed per region where possible.
- Let the shop's own history decide the effect. Estimate lift or dip separately for the relevant categories (fasting foods, fruit, dairy, meat) instead of applying one global multiplier.
- Use day-of-week and month-of-year features for weekday and month-long patterns; these are often better learned from data than assumed.
- Allow a one-day tolerance by including the day before and after as soft features when the almanac dates are uncertain.
- Avoid double counting with the major events in `data/events/events.csv`, because several large festivals sit on these same tithis.
