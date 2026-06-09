# Embedding-Aligner — Findings & Status (2026-06)

A record of what was tried to grow the Ido→Esperanto dictionary from
distributional embeddings, what was measured, and what's a dead end — so nobody
re-runs the dead ends or trusts the wrong metric.

## The goal (and the one metric that matters)

The build keeps only ~4,607 BERT pairs because `build_one_big_bidix_json.py:403`
applies a **first-4-char cognate guard** (drop any BERT-only pair whose EO term
doesn't share the Ido lemma's first 4 chars). So the *only* payoff of embedding
work is **NON-cognate pairs** — cognates are already kept.

**Therefore the only metric that matters is NON-cognate top-1 precision** on
held-out Wiktionary gold. Watch out:
- Overall P@1 is dominated by cognates → misleadingly high.
- The MT gates (`eval_translation` chrF on 147 sentences, `eval_vortaro`
  precision@1 holding out io_wiktionary) are **structurally blind** to these
  BERT-only long-tail lemmas. They will rubber-stamp a noisy BERT source.
  Use the harness below, not the gates, to judge embedding output.

## Harness — run locally (CPU, minutes) BEFORE any GPU

Run with `venv/bin/python` (has torch CPU 2.9 + transformers 4.57 + gensim 4.4):

- `experiments/eval_bli_csls_goldseed.py` — BERT bi-encoder ablation on 400
  held-out gold pairs: {cognate, gold} seed × {raw-NN, CSLS} × {raw, whitened},
  reported with a cognate/NON-cognate split, frequency terciles, and
  matched-coverage RAW-vs-WHITENED. Uses the cached Nov model + cached EO
  embeddings (no GPU, no re-finetune). Caches io embeddings to
  `experiments/gold_io_emb.npz` so reruns are instant.
- `experiments/eval_bli_fasttext.py` — the "done-correctly" alternative:
  fastText (Ido, subword) + the 430k-word `esperanto_clean__300d.npy` (EO),
  aligned by gold-seed Procrustes, same cognate split. Caches the trained
  fastText model.

## Results

| Method | overall P@1 | **NON-cognate P@1** | verdict |
|---|---|---|---|
| Cross-encoder re-ranker (run-1, Kaggle, **trained WITHOUT surface negatives**) | — | 29% gold, confident antonyms (`fina→komenca`@0.998) | not shippable; config was crippled |
| BERT bi-encoder + Procrustes, cognate seed, raw-NN | 51% | ~6% | — |
| + gold seed (#3) | 54% (+3%) | ~6% | marginal |
| + CSLS (#6) | ~0 change | ~6% | no help |
| + whitening, all-but-the-top D=10 (#anisotropy) | 53% | non-cog coverage → **0%** at usable thresholds | calibration only |
| fastText(Ido)+word2vec(EO) Procrustes (#5) | 2.4% | **1%** | worse — Ido space is degenerate (see below) |
| morpheme/root word2vec(Ido) + word2vec(EO) | 3.6% | **2%** | source space now SEMANTIC, but root↔word alignment fails (see below) |
| symmetric root↔stem + Procrustes | 9.0% (P@5 19.3%) | **6%** | best overall; matching granularity bridged the spaces — but lands at the SAME ~6% ceiling as BERT |
| symmetric root↔stem + self-learning (VecMap-style) | 8.3% | 5% | iterative refinement drifted; no gain |

### The convergent ceiling — final conclusion of the embedding thread
Two fully independent, principled pipelines — (a) fine-tuned XLM-R bi-encoder,
(b) symmetric root↔stem word2vec + VecMap self-learning — **both converge to ~6%
non-cognate top-1 precision.** The climb was instructive (whole-word fastText 1%
→ morpheme/root fixes source degeneracy → symmetric granularity bridges the
spaces → 6%), but the ceiling did not move. P@5 ≈19% means the right answer is
often in the top-5, so embeddings could *rank/validate* candidates from other
sources, but cannot *generate* non-cognate pairs at shippable precision. The
binding constraints are structural and won't change: small Ido corpus + Ido≈EO
(non-cognate pairs are rare) + ~zero non-cognate demand in real text (see
translation proof). **Embedding-based non-cognate dictionary expansion is closed
at ~6%.**

### Morpheme/root-level (word2vec on lemmatized corpus) — the nuanced result
`experiments/eval_bli_morpheme.py`: lemmatize the corpus to ROOTS via
`ido.automorf` (urbo/urbeto/urbano→urb, multiplying root counts), train word2vec
(no subword) on roots. **This FIXED the source-space degeneracy** —
NN(`hund`)=`volf, strig, karnivor, cerv` (animals!), NN(`urb`)=`urbet, vilajet,
metropol` (settlements!), vs fastText's rhymes. Root-level distributional
semantics genuinely works for frequent roots on this corpus size. **But
translation precision stayed ~2% non-cognate** because the bottleneck MOVED to
cross-lingual alignment: aligning an Ido-ROOT space to the EO-WORD space
(`hund` vs `hundo`, different granularity + different training corpora) with one
linear Procrustes map fails (cognate precision also dropped to 48%). Lesson:
"word parts vs words" helps the monolingual representation a lot, but doesn't by
itself bridge the two languages. The principled continuation (untried) is
SYMMETRIC root-level — lemmatize EO too (eowiki dump + apertium-epo analyzer),
train EO-root vectors, align root↔root with iterative VecMap. Note: lt-proc does
NOT preserve input newlines and unescaped `^$/\\<>[]{}@` truncate the stream —
`lemmatize_lines` escapes them + uses a sentinel token (a 5000-line-chunk run
that ignored this silently kept only 67k of 6.7M tokens).

### fastText root cause — THE earlier whole-word finding
The EO side (`esperanto_clean__300d.npy`, trained on a big corpus) is excellent
and semantic: NN(`hundo`)=`rotvejla, pudelo, ĉivava` (dog breeds), NN(`urbo`)=
`distrikto, vilaĝo, urbeto, ĉefurbo`. But the **Ido fastText** trained on the
6.5M-word corpus is **degenerate — orthographic, not semantic**:
NN(`hundo`)=`abundo, fundo, pundo, mundo` (rhymes), NN(`domo`)=`homo, pomo`.
On a small corpus fastText's subword (char-ngram) component dominates and
collapses to spelling similarity. **This is the real reason every embedding
method hits the non-cognate wall: the Ido corpus is too small to learn meaning,
so Ido vectors encode ORTHOGRAPHY — and orthographic similarity ≈ cognates,
which the guard already keeps.** No alignment trick (VecMap/iterative/whitening)
fixes a degenerate source space; the binding constraint is monolingual Ido data
volume, which Wikipedia-scale Ido cannot supply.

### Key diagnoses
- **Anisotropy.** The aligned BERT space crams all cosines near 1.0 → cosine
  carries *no* confidence signal (precision flat ~54% at every threshold).
  Whitening (remove top-D principal directions) makes cosine *readable* but adds
  **no ranking signal**: at matched coverage (top-20%/50%/100% by confidence)
  RAW and WHITENED precision are identical (98/94/54 ≡ 98/94/53). The "94%
  precision slice" after whitening is **100% cognates**.
- **The non-cognate signal is essentially absent (~6%).** Seed/CSLS/whitening/
  cross-encoder all hit the same wall. When the model ventures a non-cognate
  guess it is ~94% wrong.

### Root cause
- Ido training corpus is small (~6.5M words) → weak content-word vectors.
- Ido and Esperanto are so close that genuinely non-cognate pairs are the rare,
  hard cases — exactly where distributional alignment is weakest.

## The translation-bottleneck proof (2026-06-09)

Translated the featured iowiki **"Usa"** article (1389 tokens) locally
(`apertium -d apertium-ido-epo ido-epo`), classifying every failure by running
the pipeline stages manually (`*`=monodix-unknown, `@`=bidix-gap,
`#`=gen-fail; the deployed mode strips these markers):

- ~96% fully translated.
- 52 `*` unknowns — **21/25 distinct are proper nouns**; only 4 content words
  (`indijeni, centre, nord, rinomizesis`), all cognate/derivable.
- 6 `@` bidix gaps — **all cognate stems** (`habit, sucesoz, reprezenter, …`).
- **ZERO non-cognate content-word gaps embeddings could fix.**
- The readability damage is GRAMMAR, invisible to markers (valid-but-wrong
  forms): number-agreement transfer (`kelka leĝoj`→`kelkaj`, `socioj
  organizita`→`organizitaj`, `unuaj Brita`→`Britoj`) and closed-class errors
  (`Pos`→`Par`, should be `Post`). ~12 grammar errors vs 0 vocab gaps.

This both confirms grammar ≫ vocabulary as the translator bottleneck and
explains the 6% wall: there is barely any non-cognate vocabulary *demand* to
capture.

## Guidance

- **Do not** re-run BERT seed/CSLS/whitening/cross-encoder variants — measured
  dead ends. The cognate guard is essentially optimal for what BERT delivers.
- Measure any new embedding idea in the harness (NON-cognate precision) before
  spending a minute of GPU. The whole Kaggle saga would have been avoided by
  running the harness first.
- `notebooks/{bert_rerun,cross_encoder_only,cross_encoder_only_kaggle}.ipynb`
  work end-to-end but drive the dead-end BERT pipeline; keep only as scaffolding
  if pursuing a different embedding.
- For translation *quality*, the lever is the closed-class / transfer grammar
  (parent `FLOW_REVIEW.md`), not this directory.
