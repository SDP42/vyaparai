# Document intelligence

Add a shop's own papers (return policy, supplier terms, SOPs, GST notes) and ask questions in English, हिन्दी or Hinglish. The answer is a quoted passage with its source, never newly written text.

## Pipeline

1. **Read** PDF (text layer, with page numbers), DOCX (headings kept), TXT and Markdown. Caps: 15 MB, 200 PDF pages, about 2M characters. Scanned PDFs are refused with a clear message (photograph bills on the Bills page instead).
2. **Chunk** into passages of about 90 to 170 words that keep their heading and page; long sections are cut at sentence ends with a 25-word overlap. The heading is part of the passage text.
3. **Embed** each passage with a pretrained multilingual model run locally on CPU through ONNX (fastembed): `paraphrase-multilingual-MiniLM-L12-v2`, Apache-2.0, 384 dimensions, about 220 MB, 50+ languages including Hindi. Vectors are stored with the passage.
4. **Search**: permission filter first (a passage the asker's role may not read is never scored), then a fused score `0.3 x BM25 keywords + 0.7 x embedding similarity` (each min-max normalised).
5. **Answer**: the best one or two sentences of the best passage (two only when nearly tied), plus up to 4 passages with document, page and section. Confidence is "high", "possible" (shown with a warning) or "none" (nothing returned).
6. **Assistant fallback**: on the Ask page, a question the numbers cannot answer, or a policy-style question ("return", "rules", "limit"...), is searched in the documents using the asker's role.

## Why this model and this fusion (measured, not assumed)

Retrieval was compared on 57 labelled questions over the 12 passages of our sample documents (41 "easy" that reuse the document's words, 16 "hard" paraphrases; 6 more questions have no answer in the documents).

| Method | Easy R@3 / MRR | Hard R@3 / MRR |
|---|---|---|
| Keywords only (BM25) | 1.00 / 1.00 | 0.50 / 0.50 |
| MiniLM multilingual, embeddings only | 0.93 / 0.84 | 0.94 / 0.86 |
| bge-small-en, embeddings only (English model) | 0.95 / 0.95 | 0.94 / 0.82 |
| Rank-fusion (RRF) of both | 0.98 to 1.00 / 0.92 to 0.98 | 0.81 to 0.94 / 0.67 to 0.76 |
| **Normalised score fusion, keyword weight 0.3 (chosen)** | **0.98 / 0.96** | **1.00 / 0.91** |

Keywords alone are perfect when the question reuses the document's words and collapse on paraphrases; embeddings alone are the reverse; the weighted fusion keeps both. The English-only model is no better on this set and cannot read Hindi.

## Honest limits

- **Tiny, self-written evaluation.** 12 passages from documents we wrote. The keyword weight was tuned on these same questions, so the scores are optimistic. Real shops have longer, messier files; accuracy there is unmeasured.
- Refusal is imperfect: similarity alone cannot tell an off-topic question from a weak match. On our 6 out-of-scope questions one still got a "high" answer ("kal ka mausam..."). Low-confidence matches are labelled "possible".
- Hinglish is matched through a multilingual model that saw little romanised Hindi; it worked on our questions but is the weakest path.
- No generative model is used. That is a limit (no summaries across documents) and a safeguard: text inside a document, such as "ignore previous instructions", can only be quoted back as data. A test covers it.
- Embeddings are loaded per workspace into memory for each search; fine for up to a few thousand passages (index capped at 20,000 passages and 200 documents).

## Security

Access levels (everyone, analysts, admins, owners) are set at upload and cannot exceed the uploader's own role. Search and the passage view filter on them before any scoring; a document you cannot read looks the same as a missing one (404).

## API

`POST /workspaces/{id}/documents` (multipart: file, min_role) · `GET .../documents` · `GET .../documents/{doc}` · `DELETE .../documents/{doc}` (admin) · `POST .../documents/search` `{query, k}`
