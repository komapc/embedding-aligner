# BIDIX_AS_SEED — Experiment findings (2026-05-04)

This is the empirical follow-up to `BIDIX_AS_SEED_DICT.md`. **TL;DR: bidix-as-seed didn't help.**

## What was implemented

`scripts/15_bert_crosslingual_alignment.py` got a new function `create_seed_dictionary_from_bidix()` and `--seed-source {cognate,bidix}` CLI flag. With `--seed-source bidix`, it loads pairs from `extractor/dist/bidix_big.json`, filters to Wiktionary-confirmed translations only, and feeds them as Procrustes anchors instead of cognate matches.

## Results

Three runs:

| run | Ido vocab | seed source | seed pairs |
|---|---:|---|---:|
| baseline | 5k (Wiktionary-derived) | cognate | 500 |
| bidix-5k | 5k | bidix | **987** |
| bidix-15k | 15k (Wikipedia-derived) | bidix | 37 ← too few, excluded |

The 15k vocab from `ido_bert_wiki15k.npz` is built from Wikipedia frequency, not Wiktionary, so its overlap with the bidix is tiny. The 5k vocab comes from io.wiktionary, which gave the bidix-seed a fair shot at being useful.

## Held-out evaluation

Test set: 65 pairs from `bidix_big.json` (Wiktionary-confirmed) where:
- Ido lemma is in the 5k BERT vocab
- The pair is NOT in EITHER seed dictionary (truly held-out for both methods)

| k | cognate p@k | bidix p@k | delta |
|---|---:|---:|---:|
| 1 | 9.2% | 7.7% | −1.5% |
| 3 | 9.2% | 9.2% | ±0.0% |
| 5 | 12.3% | 9.2% | −3.1% |
| 10 | 13.8% | 10.8% | −3.1% |

(Used relaxed matching: candidate matches if surface form matches gt or differs only by trailing `-o`/`-a`/`-e`/`-i`/`-n` — accounts for vocab containing `daniel` but ground truth being `danielo`. Strict matching gave 0% for both, dominated by EO `-o` suffix vocabulary mismatches.)

**Bidix-seed BERT is marginally WORSE on the held-out set than cognate-seed.**

## Why the experiment didn't pay off

### (1) BERT vocab is contaminated
The 5k Ido vocab from `ido_bert_vocab5k.npz` includes obvious junk: `!`, `!--`, `"la`, `"the`, `#`, `$18,750`, `(0.04`, `%`, etc. BERT tries to translate these to Esperanto, producing nonsense. Neither cognate nor bidix seed can fix vocab-level junk. The downstream PR #98 BERT pre-filter handles this by dropping the junk from the bidix entirely, after the fact.

### (2) Embedding quality, not seed quality, is the bottleneck
Sample top-10 candidates for `bombo` (Ido for "bomb"):
```
cog: kolombio bombado aparato armilo bando grupo fenomeno misiisto monumento kolonelo
bid: grupo aparato bombado maso bando fenomeno simbolo kolombio armilo ritmo
```
Both methods retrieve embedding-neighbors of `bombo` rather than its translation. The correct answer (`bombo` itself, identical-form) IS in the EO vocab but isn't the nearest neighbor under either Procrustes rotation. The fine-tuned XLM-RoBERTa learned that `bombo` and `kolombio` co-occur in similar contexts (both appear in conflict/nationality discussions in the Ido corpus). Better seeds don't fix that.

### (3) Held-out set is hard by construction
The held-out pairs are exactly the ones where:
- BERT vocab contains both Ido and EO sides
- Wiktionary has a translation for them
- Neither cognate-similarity nor bidix-curated lists captured them

These are non-cognate translations that the embedding alignment is poorly equipped to find. The "easy" pairs (cognates) ARE captured by both methods and dominate the training/seed set.

### (4) Top-1 disagreement is high (47.5%) but neither is reliably better
Across all 5000 vocab words, cognate and bidix BERT produce different top-1s 47.5% of the time. The methods substantially differ — they just don't reliably differ in a way that's better. Neither is calibrated against an external truth signal beyond the seed.

## What I'd actually do for BERT quality

Not seed strategy. The wins would come from (in priority order):

1. **Drop BERT-only translations entirely from `source_bert_embeddings.json`.**
   Keep only entries where BERT corroborates an existing Wiktionary translation. Loss: ~17k entries from the bidix. Gain: ~70% wrong-translation rate from BERT-only is gone. The 17k loss is mostly low-value (rare words with bad translations).

2. **Confidence threshold filter.**
   BERT outputs cosine similarity scores. Drop entries below some threshold (e.g. 0.85 vs current 0.80). Tighter threshold = fewer entries but higher precision.

3. **Train BERT on parallel data.**
   Currently the model is fine-tuned on monolingual Ido. To learn cross-lingual translation specifically, would need parallel Ido↔EO sentences. We could mine them from the existing 25-article corpus (using the apertium translator's output as silver-standard) but this is a multi-day project.

## Recommendation

Close out `BIDIX_AS_SEED_DICT.md` as "tried; didn't move the needle." Pursue option 1 above for next BERT-quality work.

The artifacts (`results/bert_cognate_baseline/`, `results/bert_ido_epo_alignment_bidix/`) are kept on disk for reproducibility. The live `source_bert_embeddings.json` was not modified.

## What this experiment did confirm

- The `--seed-source` CLI flag works correctly; cognate path is unchanged.
- Bidix loading and filtering logic is sound (987 valid Wiktionary-confirmed seeds extracted).
- Pipeline is reproducible — re-running would give the same results.

Code is left in `15_bert_crosslingual_alignment.py` for anyone who wants to revisit. Not enabled by default.
