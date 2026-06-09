> ⛔ **SUPERSEDED (2026-06-09) — this plan was executed and the approach is a measured DEAD END.**
> The BERT bi-encoder/cross-encoder path cannot retain non-cognate Ido↔Esperanto
> pairs (~6% precision); the existing cognate guard is essentially optimal. See
> **`experiments/FINDINGS.md`** for the evidence and the local harness. Kept only
> as a record of the pipeline. Do not re-run without a fundamentally different
> embedding measured first in the harness.

# BERT rerun — full pipeline run plan (2026-06-08)

Goal: increase the Ido→Esperanto dictionary by rerunning the BERT path end to
end — **re-finetune → re-extract → re-align → cross-encoder re-rank** — then
gate the new pairs before they ship.

This plan reflects the user decision to run **all three levers**. Ordering
matters: the model determines the embeddings → candidates → the cross-encoder's
hard negatives, so finetuning must come first and the cross-encoder is trained
on the *new* candidates.

---

## What is already prepped (CPU, done — no GPU burned)

| Artifact | State |
|----------|-------|
| Fresh finetune corpus `data/processed/ido_finetune_corpus.txt` | **432,114 sentences / 6.52M words** from the May-1 io.wikipedia dump (vs Nov corpus 392k sentences / 6.70M words). Fresher, **0.00% markup junk** (vs old 0.7%), correctly sentence-per-line (15.1 w/l) for `13_finetune.load_corpus`. Built by new `scripts/build_ido_corpus.py` (File/ref-link stripping + sentence split; the corpus had no build script before — now regeneratable). |
| Refreshed BERT vocab `data/ido_vocabulary_filtered_refreshed.txt` | 32,419 entries re-filtered vs Jun-4 Wiktionary + Jun-7 automorf (+588/−332 vs committed; additions mostly derivable participles — small lever). |
| Cross-encoder training data | Verified end-to-end via `16_train_cross_encoder.py --dump-only`: 41,315 positives (38,578 wikt + 2,737 langlink), 39,630 train / 200 heldout. |
| Colab input tarball | Rebuilt with Jun-4 `bilingual_raw.json` + `io_eo_langlinks.json`, **uploaded** to release `cross-encoder-inputs` (asset now Jun-8). |
| `scripts/17_apply_cross_encoder.py` | NEW — applies the trained cross-encoder to candidates (closes the train→consume gap; was missing). |
| Eval gate | `extractor/scripts/{dict_diff,eval_translation,conflict_winner_diff,eval_vortaro}.py` all present — same harness that gated the last round. |

---

## GPU session (Colab T4 or better) — ordered

> Decision still open before kicking off: whether the fresher+cleaner corpus
> (May-1, 0.00% junk, 432k sentences) is worth the long finetune, or whether to
> reuse the existing `bert-ido-finetuned-full` model and only redo steps 2–4. The
> corpus is a modest, same-domain improvement — a reasonable but not dramatic
> finetune justification. If reusing the model, **skip step 1** and the existing
> candidates can drive the cross-encoder.

**1. Re-finetune XLM-RoBERTa (MLM)** — GPU, longest step
```bash
python3 scripts/13_finetune_bert.py \
  --corpus data/processed/ido_finetune_corpus.txt \
  --output models/bert-ido-finetuned-full --epochs 3 --batch-size 16
```
Docstring says 3–4 h; the committed model ran 146,787 steps, so budget more.
Confirm the corpus path is the new one.

**2. Re-extract embeddings** — GPU forward pass (~20–30 min for ~32k vocab)
```bash
python3 scripts/14_extract_bert_embeddings.py \
  --model models/bert-ido-finetuned-full \
  --vocab data/ido_vocabulary_filtered_refreshed.txt \
  --output embeddings/ido_bert_filtered.npz
```
(Promote the refreshed vocab to `data/ido_vocabulary_filtered.txt` first if we
decide to ship it — see open question below.)

**3. Re-align** — GPU (extracts EO embeddings via BERT) + CPU (Procrustes/NN)
```bash
python3 scripts/15_bert_crosslingual_alignment.py \
  --bert-model models/bert-ido-finetuned-full \
  --ido-embeddings embeddings/ido_bert_filtered.npz \
  --epo-vocab models/esperanto_clean__vocab.txt \
  --output-dir results/bert_ido_epo_alignment
```
Note: 15 embeds the EO vocab (default `--max-epo-words 10000`) through the SAME
BERT model so both sides live in one 768-d space for Procrustes — so it needs
the GPU for that forward pass, then aligns + nearest-neighbours on CPU. Pass only
`--epo-vocab` (the tracked 4 MB `esperanto_clean__vocab.txt`); the 515 MB
`--epo-model` npy is NOT needed (it's only an alternate word-list source).
Produces the new `translation_candidates.json`.

**4. Train the cross-encoder on the NEW candidates** — GPU (~25 min)
```bash
python3 scripts/16_train_cross_encoder.py \
  --candidates results/bert_ido_epo_alignment/translation_candidates.json \
  --model-out models/cross-encoder-io-eo --epochs 3 --batch-size 32
```
Record held-out F1 / AUC / precision — these set the apply threshold in step 5.
(Inputs `bilingual_raw.json`/`io_eo_langlinks.json` come from the release tarball
per the notebook.)

**5. Apply the cross-encoder** — GPU inference (~minutes)
```bash
python3 scripts/17_apply_cross_encoder.py \
  --model models/cross-encoder-io-eo \
  --candidates results/bert_ido_epo_alignment/translation_candidates.json \
  --output results/bert_ido_epo_alignment/translation_candidates_ce.json \
  --threshold <set from step-4 precision> --top-k 3
```

Pull back to the laptop: the new `bert-ido-finetuned-full`, `cross-encoder-io-eo`,
`translation_candidates.json`, and `translation_candidates_ce.json`.

---

## Post-GPU (CPU, on laptop)

**6. Convert to extractor source**
```bash
python3 scripts/20_convert_to_unified_format.py \
  --input results/bert_ido_epo_alignment/translation_candidates_ce.json \
  --output ../../extractor/data/sources/source_bert_embeddings.json \
  --min-similarity 0.0          # CE already did the filtering
```

**7. ⚠ Relax the cognate guard for cross-encoder pairs (extractor change)**
`extractor/scripts/build_one_big_bidix_json.py:403` currently drops every
BERT-only pair whose EO term doesn't share the first 4 chars with the Ido lemma.
That guard exists *because* the un-reranked bi-encoder is ~70% wrong. With the
cross-encoder doing principled filtering, this guard would re-discard exactly the
non-cognate true pairs we trained it to keep. Gate the guard on whether a
cross-encoder score is present/absent (keep it for any legacy un-scored BERT
pairs; bypass it for `ce_score`-bearing pairs). **Tune against the gate, do not
loosen blindly** — the project's recurring failure is dumping noisy pairs.

**8. Rebuild + gate (ship only if all hold)**
```bash
cd ../../extractor
python3 scripts/build_one_big_bidix_json.py
python3 scripts/export_apertium.py     # pipeline may skip — run explicitly
python3 scripts/export_vortaro.py
python3 scripts/dict_diff.py            # only additions / no real words dropped
python3 scripts/eval_translation.py    # chrF + coverage flat-or-up
python3 scripts/conflict_winner_diff.py
python3 scripts/eval_vortaro.py         # precision@1 not regressed
```
Ship via `bash core/deploy.sh` + regen PRs only if no guardrail regresses.

---

## Open questions to settle before the GPU session
1. **Finetune or reuse?** +8.7% fresher corpus vs a multi-hour run. Reuse skips step 1.
2. **Ship the refreshed vocab?** +588 are mostly derivable participles; may add noise. Decide before step 2.
3. **Cross-encoder threshold** — set from step-4 held-out precision; controls how aggressively non-cognate pairs are admitted.
