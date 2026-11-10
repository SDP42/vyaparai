# Review intelligence: Hinglish / Hindi / English NLP research notes

Scope: CPU only, no paid APIs, no runtime model downloads, permissive licences only.
Legend: [V] = read on the source page this session; [U] = unverified / secondary source only.

## 1. What works for Hinglish sentiment with simple methods

- SemEval-2020 Task 9 (SentiMix), Hinglish tweets, ~20K examples, 3 classes, metric weighted F1.
  Source: https://arxiv.org/pdf/2008.04277 (paper CC BY 4.0) [V].
  - Winner 75.0 F1; top 15 teams 68.6-75.0. Baseline (multilingual BERT) ~70.7 F1; 44 of 61 teams beat it, 17 did not [V].
  - Organisers: BERT-like models and ensembles dominate. Inter-annotator agreement on Hinglish was only 55 percent [V]
    (so the ceiling on noisy 3-class labels is low).
- TueMix (https://preview.aclanthology.org/setup/2020.semeval-1.178): logistic regression on TF-IDF n-grams + sentiment
  lexicons + surface features, weighted F1 0.685, reportedly beating their own neural net [U: via search summary only].
  Takeaway: linear + lexicon is within ~5-7 points of the winners on this task.
- HinglishNLP (https://github.com/NirantK/Hinglish, MIT [V]): fine-tuned transformers on a Hinglish set,
  test acc 0.63-0.71 (BERT-multilingual 0.688, DistilBERT 0.693, ensemble 0.714) [V]. Dataset provenance/licence of the
  Google Drive data is not stated on the repo page: do not use it.
- Realistic ranges to expect (our judgement, not from one source): 3-class macro-F1 on short Hinglish social text about
  0.55-0.70 for lexicon or TF-IDF+LR; 0.65-0.75 for fine-tuned transformers. Reviews with star ratings are easier than
  tweets (stronger polarity words, rating as a noisy label); 2-class (neg vs non-neg) on English reviews is typically
  0.80-0.90 accuracy for TF-IDF+LR [U: general experience]. Large transformers buy maybe +3-8 macro-F1 points: not
  worth breaking the CPU/no-download constraint.
- Spelling normalisation helps: a Hindi word dictionary mapping romanised variants to one form improved sentiment and POS
  in code-mixed text (https://arxiv.org/pdf/1804.00804) [U: search summary]. dhvani (https://pypi.org/project/dhvani/)
  generates ~10 romanised variants per Hindi word and claims +1.2 macro-F1 [U, own claims; licence not checked].
  Cheaper alternative for us: character n-grams (2-5) in TF-IDF absorb most spelling variation without a dictionary.

## 2. Datasets for evaluation or lexicon seeding (licence status)

| Dataset | Content | Licence | Status |
|---|---|---|---|
| SemEval-2020 SentiMix Hinglish (https://ritual-uh.github.io/sentimix2020/ , paper above) | ~20K Hinglish tweets, pos/neu/neg | Paper is CC BY 4.0 [V]. Dataset licence not stated in paper; tweets crawled via Twitter API [V], so redistribution is restricted by Twitter terms | Do NOT bundle. Local, manual evaluation only, if at all. Unverified. |
| AI4Bharat IndicSentiment (https://huggingface.co/datasets/ai4bharat/IndicSentiment) | Product/service reviews, Hindi + 9 other langs, pos/neg/neu, Devanagari (translated) | HF card states no licence [V]. AI4Bharat says IndicXTREME packaging is CC0 and it does not own the source text [U: search summary of their page]. | Likely usable for Devanagari evaluation; confirm licence in writing before shipping any rows. No Hinglish. |
| dhruv0808/indic_sentiment_analyzer (HF) | Derived from IndicSentiment | Header says CC-BY-4.0, body says CC BY-NC 4.0 [U: search snippet] | Treat as NON-COMMERCIAL. Avoid. |
| mteb/SentimentAnalysisHindi (HF) | Hindi sentiment | cc-by-nc-sa-4.0 in metadata [U: snippet] | NON-COMMERCIAL. Avoid. |
| L3Cube HingCorpus / HingLID (https://github.com/l3cube-pune/code-mixed-nlp) | Hinglish corpus, LID | CC BY-NC-SA 4.0 [V] | NON-COMMERCIAL. Avoid. HingSent not listed on that page; not verified. |
| IIT Patna Hindi ABSA (https://aclanthology.org/L16-1429/) | Hindi product review sentences | No licence found [U] | Do not use. |
| NirantK/Hinglish data | see above | Repo MIT, data licence unknown [V] | Do not use. |

Conclusion: no clearly permissive Hinglish (Latin-script) review set was found. Plan to build our own small gold set:
author ~300-500 reviews (own wording, plus consented real reviews from pilot shops), label by two people, release under
CC0 or CC-BY in-repo. This also seeds lexicons legitimately. English: check candidate sets individually (many Amazon/Yelp
sets are non-commercial or ToS-restricted): unverified, not researched here.

## 3. Hinglish patterns and pitfalls

(Authored from general knowledge of the language; not sourced. Treat as lexicon seeds to be validated on our gold set.)
- Spelling variation is the main problem: nahi / nahin / nhi / nai / nahee; accha / acha / achha / acchha / ache / achcha;
  bekar / bekaar / bakar; bahut / bohot / bahot / bhut / boht; kharab / kharaab / kharb; ghatiya / gatiya; badhiya / badiya /
  bdiya / bhadiya; zyada / jyada / jada; paisa / paise / pese. Normalise: lowercase, collapse repeats (soooo, mastttt) to
  max 2, strip diacritics, then map variants via a small table, plus char n-grams as a fallback.
- Positive seeds: accha/badhiya/mast/zabardast/shandar/lajawab/best/sahi/perfect/tasty/fresh/value for money,
  "paisa vasool", "recommend", "shukriya". Negative seeds: bekar/bakwas/ghatiya/kharab/faltu/dhokha/fraud/loot/ " mehnga",
  "kharaab nikla", "toota hua", "sad gaya/sadi hui", "expired", "basi" (stale).
- Multiword phrases must be matched before single tokens ("paisa vasool", "time pe", "late aaya", "der se", "wapas karna",
  "money back", "value for money", "ek dum fresh").
- Negation: nahi/nhi/na/mat/bina/kabhi nahi, plus English not/no/never/n't. Hindi is SOV, so negator usually FOLLOWS the
  predicate ("accha nahi hai", "pasand nahi aaya", "time pe nahi aaya"): use a window of ~3 tokens on BOTH sides, stopped by
  punctuation or "lekin/par/but". Not every "na" negates ("accha na", "kya na" are tag particles); restrict "na" to
  clear contexts or exclude it. "Nahi" before a negative word is not always positive ("kharab nahi hai" is mild positive
  but "bekar nahi" ok, while "nahi mila" is a complaint about availability). Double negation: flip once per negator, cap at 2.
- Theme cues are also negation-sensitive: "late aaya"/"der se" = delivery negative, "time pe aaya" = delivery positive.
- Pitfalls: sarcasm ("wah kya service hai, 3 baar chakkar lagwaye"); contrastive "lekin/par/magar" (weight the clause after
  it); questions and neutral facts; code-mixed named brands; emoji and ratings-only rows; Devanagari vs Latin of the same
  word (map both to one token); Hindi script text with English product names; very short reviews ("ok", "nice").
- Rating/text mismatch: 5-star with a complaint or 1-star accidental taps are common. Treat star rating as a NOISY label:
  train on ratings 1-2 vs 4-5, drop 3 (or map to neutral), and report a "disagreement" flag when text score and rating
  differ strongly; never silently overwrite either.

## 4. Evaluating honestly with small data

- Hold out a test set FIRST (stratified by language and class, split by shop/reviewer to avoid leakage); never tune
  lexicons on it. Use it once. Keep a dev set for lexicon tuning.
- Report macro-F1, per-class precision/recall, confusion matrix, and per-language numbers (English / Devanagari / Hinglish
  separately). Accuracy alone hides class imbalance (reviews skew positive).
- With <=500 labelled rows, give confidence intervals (bootstrap 95 percent CI over 1000 resamples); a 300-row test set gives
  roughly +/-5 points. Use stratified k-fold (5x) CV for the logistic regression, and compare against trivial baselines
  (majority class, rating-only, lexicon-only).
- Theme extraction: evaluate precision of evidence snippets by manual review of ~100 samples and recall on a labelled
  subset; report per-theme.
- Two annotators on at least a 20 percent overlap, report Cohen's kappa. SemEval's Hinglish agreement was only 55 percent,
  so expect label noise to cap scores.
- Disclose: labels derived from ratings are noisy; small and domain-skewed gold set (retail, few cities, shop types);
  no sarcasm handling; code-mixing and spelling coverage limited to our lexicon; language detection is heuristic (script
  ratio plus Hinglish word list) and short texts are unreliable; results from other domains (tweets) do not transfer;
  not an audit tool: scores are indicative, show evidence and let users override. Do not claim accuracy numbers from papers.

## Recommended design (10 lines)

1. Pipeline: normalise (NFKC, lowercase, collapse repeats, map variant spellings) -> script detect -> tokenise.
2. Language: Devanagari ratio > 0.3 -> hi; else Latin text containing >= 2 Hinglish stopwords/lexicon hits -> hinglish; else en.
3. Single Hinglish-aware lexicon (en + hi Devanagari + Latin variants + phrases), authored by us under the repo licence.
4. Negation: bidirectional 3-token window, clause-bounded, "na" excluded unless in a negation-phrase list.
5. Features for logistic regression (numpy, L2): word 1-2 grams + char 2-5 grams (hashed), lexicon score, negation count.
6. Train on rating-labelled reviews (1-2 neg, 4-5 pos, drop 3), class-weighted; final label = blend of LR probability and lexicon score.
7. Themes: authored keyword lexicons per theme (en/hi/Hinglish) with phrase matching; evidence = the sentence containing the hit.
8. Flag rating/text mismatch and low-confidence rows rather than forcing a label; always show evidence snippets.
9. Gold set: author + label ~400 rows in-repo (CC0), split once, report macro-F1 with bootstrap CIs per language.
10. Licences: do not bundle SentiMix, L3Cube, HF-NC sets; IndicSentiment only after written licence confirmation; ship a LIMITS note.
