# Ido↔Esperanto Embedding Aligner

Generates Ido→Esperanto translation candidates using BERT cross-lingual alignment.
Output feeds into `extractor/data/sources/source_bert_embeddings.json` as a
low-priority source (Wiktionary wins on conflict).

## Pipeline

Four steps, driven by `make`:

```
13_finetune_bert.py                   Fine-tune XLM-RoBERTa on Ido corpus (GPU, ~11h)
14_extract_bert_embeddings.py         Extract vocab embeddings from fine-tuned model
15_bert_crosslingual_alignment.py     Procrustes alignment + nearest-neighbor search
20_convert_to_unified_format.py       Export to extractor source JSON
```

### Run

```bash
# Build and export BERT source (steps 14-20, skips fine-tuning)
make

# Force full pipeline including fine-tuning (GPU required)
make finetune-bert && make
```

`make` writes directly to `../../extractor/data/sources/source_bert_embeddings.json`.

### Fine-tuning (step 13)

Only needed when retraining from scratch. Requires a GPU (Google Colab T4 or
better). Takes ~11 hours. Two trained models exist:

- `models/bert-ido-finetuned-full/` — fine-tuned on Ido Wikipedia + Wiktionary corpus
- `models/bert-ido-lemma-30k/` — fine-tuned on lemmatized forms (30k vocab); newer,
  not yet used for the current candidate set

Both are gitignored (~1 GB each).

```bash
make finetune-bert
```

## Current stats

The committed candidate set (`results/bert_ido_epo_alignment/`) was generated with
`bert-ido-finetuned-full` against 32,163 Ido vocabulary forms and 10,000 Esperanto
forms (Procrustes threshold 0.8, top-10):

| Metric | Value |
|--------|-------|
| Ido vocab | 32,163 |
| Esperanto vocab | 10,000 |
| Raw candidate pairs | 321,630 |
| Seed pairs | 500 |

The extractor applies two additional filters when consuming this source:

1. **Threshold 0.99** — only the highest-confidence pairs are kept (pass `--bert-threshold 0.99` to `build_one_big_bidix_json.py`).
2. **Cognate guard** — BERT-only translations are dropped unless the Esperanto term shares the first 4 letters with the Ido lemma (prevents distributional noise like `mortala→serioza`).

After both filters: ~4,607 pairs retained in the extractor bidix.

## Files

```
scripts/
  13_finetune_bert.py                  Fine-tune XLM-RoBERTa on Ido corpus
  14_extract_bert_embeddings.py        Extract embeddings for Ido vocabulary
  15_bert_crosslingual_alignment.py    Align embedding spaces, find candidates
  20_convert_to_unified_format.py      Convert candidates to extractor source JSON
  validate_schema.py                   Validate extractor source JSON schema
data/
  ido_corpus.txt                       Ido training corpus
  ido_vocab.txt                        Ido vocabulary list (5k baseline)
  ido_vocabulary_filtered.txt          Filtered 32k vocabulary (current alignment input)
  ido_vocab_wiki15k.txt                io.wikipedia vocabulary (15k)
embeddings/
  ido_bert_vocab5k.npz                 Pre-computed Ido embeddings (gitignored)
models/
  bert-ido-finetuned-full/             Fine-tuned BERT model (gitignored)
  bert-ido-lemma-30k/                  Lemma-focused fine-tuned model (gitignored)
  esperanto_clean__vocab.txt           Esperanto vocabulary (alignment input)
  esperanto_clean__stats.json          Esperanto vocabulary statistics
results/
  bert_ido_epo_alignment/
    translation_candidates.json        Raw alignment output
    alignment_stats.json               Pipeline statistics
    seed_dictionary.txt                Seed pairs used for alignment
```

## Integration with extractor

The output is consumed by `extractor/scripts/build_one_big_bidix_json.py` as
`source_bert_embeddings`. Priority: **Wiktionary > langlinks > FR pivot > EN pivot > BERT**.
BERT translations for a lemma are dropped if any higher-priority source covers it.

To regenerate the extractor dictionaries after updating BERT output:

```bash
make                                        # update source_bert_embeddings.json
cd ../../extractor
python3 scripts/build_one_big_bidix_json.py
python3 scripts/export_apertium.py
python3 scripts/export_vortaro.py
```

## Dependencies

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```
