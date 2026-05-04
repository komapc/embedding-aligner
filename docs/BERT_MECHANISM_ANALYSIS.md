# BERT mechanism analysis — what went wrong, what to fix

Companion to `BIDIX_AS_SEED_FINDINGS.md`. Goes deeper into *why* the alignment is poor and where the leverage points are.

## TL;DR

Three independent failure modes, three independent fixes. They compose.

| Failure mode | Where | Impact (rough) | Fix difficulty |
|---|---|---|---|
| Vocabulary contamination | stage 14 input | ~10% of bidix is text-fragment junk | low (data hygiene) |
| Threshold doesn't discriminate | stage 20 / threshold flag | ~0% noise filtered at 0.80 | low (config) |
| Algorithm conflates topic-neighbor with translation | stage 13 / 15 | ~70% of clean-shape BERT-only translations wrong | high (different model) |

**The threshold is the single highest-ROI fix.** The current 0.80 keeps 100% of candidates. Tightening to 0.99 cuts to 18.4% of candidates with most-likely-correct ones retained.

---

## How the pipeline actually works

```
13_finetune_bert.py             models/bert-ido-finetuned-full/
  monolingual fine-tune of XLM-RoBERTa on Ido text (~11h GPU)
  learns: "which Ido words appear in similar contexts"
  
14_extract_bert_embeddings.py   embeddings/ido_bert_vocab5k.npz
  for each word in data/ido_vocab.txt, get its BERT embedding
  ↑ vocab is the issue: contains "!", "$18,750", "(białystok)," etc.

15_bert_crosslingual_alignment.py  results/.../translation_candidates.json
  (a) build seed dictionary of ~500 (Ido, EO) pairs from cognates
  (b) solve Procrustes: find rotation W s.t. W·X_seed ≈ Y_seed
  (c) for each Ido word: rotate, find top-K nearest EO words by cosine

20_convert_to_unified_format.py source_bert_embeddings.json
  threshold filter (default 0.80) + top-K (default 10) + JSON wrap
```

---

## Failure mode 1: Vocabulary contamination

The Ido vocab file (`data/ido_vocab.txt`) was built from io.wiktionary content but kept text fragments verbatim. The 5k vocab includes:

| "Ido" word | What BERT outputs as top-1 EO | similarity |
|---|---|---|
| `!` | `faka` | 0.972 |
| `!--` | `km-oj` | 0.978 |
| `"the` | `the` | 0.989 |
| `"la` | `lara` | 0.991 |
| `#` | `fox` | 0.971 |
| `$18,750` | `inventisto` | 0.977 |
| `(0.04` | `krei` | 0.973 |
| `%` | `cent` | 0.975 |
| `(białystok),` | `warszawa` | 0.974 |

The model is "translating" things that aren't Ido words. BERT has no signal to refuse — it confidently outputs whichever EO word's embedding happens to be closest after rotation.

**Fix**: prefilter `data/ido_vocab.txt` BEFORE stage 14. Drop entries that:
- Contain non-letter chars (digits, parens, `$`, `%`, quotes)
- Are length < 3 OR > 30
- Don't end in canonical Ido suffix (-o/-a/-e/-ar/-ir) for content words, OR aren't in the function-word allowlist

Estimated drop: ~10-15% of vocab. Cost: regenerate stage 14 embeddings (15-30 min, no GPU). Gain: removes 5,000+ confident-wrong (lemma, EO) pairs from final source.

PR #98 already does a downstream version of this (rejects junk-shaped lemmas at bidix-build time). Doing it upstream at the vocab file is cleaner and propagates everywhere automatically.

---

## Failure mode 2: Threshold is meaningless

Distribution of all 50,000 (lemma, EO-candidate) similarity scores:

| threshold | candidates kept | % kept |
|---|---:|---:|
| > 0.80 | 50,000 | **100.0%** |
| > 0.85 | 50,000 | 100.0% |
| > 0.90 | 50,000 | 100.0% |
| > 0.95 | 49,517 | 99.0% |
| > 0.97 | 46,419 | 92.8% |
| > 0.98 | 34,523 | 69.0% |
| > 0.99 | **9,205** | **18.4%** |

Mean similarity: 0.983 · median: 0.985

The default `--threshold 0.80` is filtering nothing. Even 0.95 keeps 99%. The threshold needs to be set in the **0.99-1.0** band to be a meaningful signal.

### Why all similarities are so high

After Procrustes rotation, embeddings live on a 768-dim unit hypersphere. Cosine similarity between any two normalized vectors in that space tends to be very high (>0.95) because they share many shallow features (capitalization patterns, length, character n-grams). Procrustes rotation makes Ido and EO embeddings close on average; the *signal* is in the small differences in the 4th decimal.

Identity-form pairs (e.g. `domo→domo`, where the EO is identical to the Ido) have median similarity **0.999**.
Non-identity pairs have median **0.984**.

Top-1 confidence distribution:
- ≥ 0.99: 2,265 lemmas (likely identity/cognate match)
- 0.95-0.99: 2,693 lemmas (mixed quality — true translations and false neighbors)
- 0.90-0.95: 42 lemmas (rare; something is unusual about the embedding)
- < 0.90: 0 lemmas

### Recommendation

Change default threshold from 0.80 → 0.99 (or 0.995). Keeps the ~2,265 high-confidence cognate-form translations; drops the noisy long tail.

That's a config change in stage 20 (`--threshold` flag in the Makefile). Trivial to implement; expected to remove most BERT-only noise.

**Trade-off**: bidix loses ~17,000 BERT-only entries for the lemmas that BERT only ever produced wrong translations for. This is exactly the loss we'd want.

---

## Failure mode 3: The algorithm conflates topic-neighbor with translation

This is the deep one and it's not fixable with thresholds or seed strategies.

### What the model learned

XLM-RoBERTa fine-tuned on **monolingual Ido** learns a distributional space where words appearing in similar contexts have similar embeddings. So:

- `bombo` (Ido for "bomb") sits near: `armilo` (weapon), `kolombio` (Colombia, a Spanish-name 1-letter-off cognate), `eksplodi` (explode), `terorismo`, `viktimaro`
- `kolombio` (Ido for Colombia) sits near: `lando`, `amerika`, `narkotismo`, `armilo`, `bombo`

The two are embedding-neighbors because they appear in similar conflict-related discussions.

### What happens at translation time

Procrustes rotates Ido space to align with EO space, using cognate seeds. After rotation:
- `bombo`-Ido lands close to BOTH `bombo`-EO and `kolombio`-EO
- The cosine similarity differs by like 0.003

Sample top-10 for Ido `bombo`:
```
cog: kolombio bombado aparato armilo bando grupo fenomeno misiisto monumento kolonelo
bid: grupo aparato bombado maso bando fenomeno simbolo kolombio armilo ritmo
```

The actual translation `bombo` (which exists in the EO vocab) is **not in either top-10**. Procrustes can't tell `kolombio` from `bombo` because their EO embeddings are nearly identical (both appear in conflict-context).

### Why neither seed strategy fixes this

- **Cognate seed** assumes cognates align. They mostly do, but the Procrustes rotation is solved on cognates, then applied to ALL Ido words. Non-cognate translations are aligned only by inference from the cognate basis.
- **Bidix seed** would in principle teach Procrustes that "non-cognate translation pairs should align." But Procrustes is a **single orthogonal rotation** — one matrix for the whole vocabulary. It can't handle "rotate cognates one way and non-cognates another way." The capacity isn't there.

### What would actually fix this

Three options, increasing in cost:

**A. Use a translation-aware embedding method.** Instead of Procrustes on monolingual embeddings, train embeddings on **parallel data** so that translations are explicitly close. For Ido↔EO, you'd need:
- Mine parallel sentences from the apertium-translated 25-article corpus
- Train a shared multilingual model on this parallel text
- Cost: ~2 days, GPU training
- Expected gain: dramatic — directly optimizes for translation, not co-occurrence

**B. Multi-anchor Procrustes (one rotation per topic cluster).** Cluster Ido vocab by topic (using monolingual embeddings), solve a separate Procrustes rotation per cluster. More degrees of freedom, can separate topical-neighbors from translations.
- Cost: ~1 day, no GPU
- Expected gain: medium — helps for words clearly belonging to one cluster, doesn't help for words spanning topics

**C. Drop BERT altogether.** Article audit shows the apertium pipeline already achieves 99.99% clean rate WITHOUT relying on BERT-derived translations. The bidix's BERT-only entries (~17k) are mostly the long tail of rare/technical words. Their main user is the **vortaro lookup tool**, not the translator.
- Cost: zero
- Expected gain: dictionary lookup quality jumps to near-Wiktionary level for the ~9k Wiktionary-confirmed entries; loses 17k entries with ~70% wrongness

---

## Concrete recommendation, ordered by ROI

1. **Tighten threshold to 0.99 (or 0.995).** Trivial config change. Reduces ~50k → ~9k candidates, keeping the most reliable ones. Expected to cut ~80% of BERT-only translation noise.

2. **Add lemma-shape pre-filter to `data/ido_vocab.txt` before stage 14.** Drop digit-containing, paren-containing, non-Ido-shape entries before BERT computes embeddings. Cleanest place to filter; PR #98's downstream filter becomes redundant.

3. **Decide if BERT is worth keeping at all.** Given 99.99% article-translation clean rate without BERT-only entries dominating, BERT's main value is for vortaro lookup of words that aren't in Wiktionary. If that's not a priority, removing BERT-only translations entirely simplifies the pipeline.

4. **(Stretch)** If you DO want BERT to genuinely help: pivot from Procrustes-on-monolingual to parallel-data fine-tuning. But that's a multi-day experiment with uncertain payoff.

I'd recommend (1) immediately — it's a 1-line change with measurable impact. Then revisit (3) once we see the (1) result.
