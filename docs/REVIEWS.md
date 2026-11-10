# Review intelligence

Import customer reviews and see what people say, in English, हिन्दी and Hinglish (Hindi in Roman letters).

## What it does

1. **Import** a CSV with a Review column (also Date, Product, Rating 1-5, Source). Column names are matched by synonyms; identical reviews are not added twice.
2. **Language**: Devanagari text is Hindi; Roman text with two or more Hindi marker words (hai, nahi, bahut...) is Hinglish; otherwise English.
3. **Sentiment** from -1 to +1: word lists we wrote, negation ("nahi", "not") that stops at the next opinion word, intensifiers ("bahut"), the clause after "but/lekin" counting more, and a few emoji.
4. **Themes**: delivery, quality, price, packaging, service, freshness, availability. Each hit keeps the short phrase it came from and its own mood.
5. **Shop model**: with 100+ reviews that have stars (and 25+ of each of 1-2 and 4-5 stars), a small logistic regression on hashed word features learns the shop's own words. It is used only if it scores at least 70% and beats the majority guess on reviews it did not train on. Where the word lists have no opinion it fills in; elsewhere it counts 35%.
6. **Alert**: a theme with 5+ mentions in 30 days, 40%+ negative and 15 points worse than the 30 days before (or no earlier data) raises "Customers are unhappy about ...".

## Honest limits

- No third-party dataset is bundled. Research found no Hinglish review set with a licence we could confirm for commercial use ([note](research/REVIEWS-NLP.md)). Tests use sets we wrote (CC0): `tests/data/reviews_gold.csv` and `reviews_dev.csv`.
- Those sets are small and written by the same person who wrote the word lists. `gold` scores 0.90-1.00 macro-F1 per language, which mostly shows the lists cover their author's phrasing. `dev` first scored about 65% before the vocabulary was widened, then about 92%; it is now a development set. **Real accuracy on unseen reviews is unmeasured**; published work on Hinglish sentiment reports roughly 0.55-0.75 weighted F1 for simple methods, and annotators themselves often disagree.
- Sarcasm, spelling the lists do not know, and reviews with no opinion words (shown as neutral; the page counts them) are the main failures.
- Stars that disagree with the words are counted, because they are often the interesting reviews.
- Themes are keyword-based. A word like "late" is read as delivery even if it describes opening hours.

## API

`POST /workspaces/{id}/reviews/import` · `GET .../reviews/summary?days=` · `GET .../reviews/products` · `GET .../reviews?label=&theme=&language=&product_id=&q=` · `POST .../reviews/try` · `POST .../reviews/reanalyse` · `GET .../reviews/template.csv`

## Next

Per-shop feedback ("this reading is wrong") to build a labelled set of the owner's own reviews, then measure accuracy on it.
