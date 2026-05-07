# PR D experiment findings — lemmatized fine-tuning didn't pay off

Companion to `BERT_MECHANISM_ANALYSIS.md`. Records the outcome of the
gated PR D experiment so it isn't repeated unnecessarily.

## Hypothesis

Surface forms `kreas/kreis/kreado/krear` waste embedding capacity. Training
XLM-RoBERTa on a **lemmatized** Ido corpus would let all four forms share
the same context distribution → stronger per-lemma embeddings → better
cross-lingual alignment.

## Experiment (2026-05-06)

- Lemmatized 30k sentences from `data/raw/ido_corpus.txt` via lt-proc
  against `apertium-ido/ido.automorf.bin`
- Trained XLM-RoBERTa base for 1 epoch on the lemmatized corpus in Google
  Colab (T4 GPU, ~7:36 wall-clock, max_length 64, batch 32, fp16)
  - Loss converged 3.79 → 2.0 across 938 steps (clean MLM convergence)
- Ran stages 14 + 15 with the new model
- Compared against production model (surface forms, 361k sentences, 3 epochs)

## Result: inconclusive at best, likely no win

Top-1 disagreement vs production: 146 of 200 sampled words (73%). Looking
at the disagreements, **neither model produces correct translations** for
the BERT-only long tail (which is by definition the words Wiktionary
doesn't cover, i.e., rare/technical):

| io_word     | surface 361k (prod) | lemma 30k        |
|-------------|---------------------|------------------|
| `omega`     | baja (✗)            | alian (✗)        |
| `religioza` | religia (✓)         | religioj (✗ POS) |
| `fasono`    | fero (✗)            | faraono (✗)      |
| `aldonoj`   | fabeloj (✗)         | aldona (✗)       |

Many disagreements are equally wrong; production has marginal edge on
clear-cognate cases (`religioza → religia`).

## Why no win

Failure mode 3 from `BERT_MECHANISM_ANALYSIS.md` is the dominant bottleneck:
**Procrustes alignment of monolingual embeddings can't separate
topic-neighbor from translation.** `bombo` (bomb) and `kolombio` (Colombia)
end up nearly identical because both occur in conflict-related Ido text.
A single orthogonal rotation cannot separate "appears in similar contexts"
from "is a translation." Lemmatization addresses a different concern
(training-data efficiency for inflected morphology) — irrelevant when the
limit is the algorithm.

The high-leverage BERT improvement was the threshold tightening (0.85 → 0.99)
already implemented in PR #29. That removes ~50% of low-confidence BERT
candidates and accounts for most of the dictionary-quality gain BERT can
deliver under the current Procrustes-on-monolingual approach.

## Decision: don't pursue

- Skipping the full 11h re-fine-tune (~$3 GPU rental).
- Closing the gated PR D task.

To genuinely improve BERT translation quality further would require a
different algorithm (e.g., parallel-corpus alignment via mUNMT or
back-translation, not Procrustes on monolingual embeddings) — a multi-day
project with uncertain payoff.

## Reproducibility

Should anyone want to revisit:
- `scripts/12b_lemmatize_corpus_sample.py` — produces 30k surface + 30k
  lemmatized samples from the full corpus
- `COLAB_PR_D_GUIDE.md` — step-by-step Colab walkthrough of the training
  + extraction + alignment chain
