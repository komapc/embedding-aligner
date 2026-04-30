# Ido↔Esperanto Embedding Aligner

Generates Ido→Esperanto translation candidates using BERT cross-lingual alignment.
Output feeds into `extractor/data/sources/source_bert_embeddings.json` as a
low-priority source (Wiktionary wins on conflict).

## Pipeline

Four steps, driven by `make`:

```
13_finetune_bert.py        Fine-tune XLM-RoBERTa on Ido corpus (GPU, ~11h)
14_extract_bert_embeddings.py  Extract vocab embeddings from fine-tuned model
15_bert_crosslingual_alignment.py  Procrustes alignment + nearest-neighbor search
20_convert_to_unified_format.py    Export to extractor source JSON
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

Only needed when retraining from scratch. Requires a GPU instance (AWS EC2
`g4dn.xlarge` or similar). Takes ~11 hours. The trained model is stored in
`models/bert-ido-finetuned-full/` (gitignored, ~1 GB).

```bash
make finetune-bert
```

## Files

```
scripts/
  13_finetune_bert.py              Fine-tune XLM-RoBERTa on Ido corpus
  14_extract_bert_embeddings.py    Extract embeddings for Ido vocabulary
  15_bert_crosslingual_alignment.py  Align embedding spaces, find candidates
  20_convert_to_unified_format.py  Convert candidates to extractor source JSON
  validate_schema.py               Validate extractor source JSON schema
data/
  ido_corpus.txt                   Ido training corpus
  ido_vocab.txt                    Ido vocabulary list
embeddings/
  ido_bert_vocab5k.npz             Pre-computed Ido embeddings (gitignored)
models/
  bert-ido-finetuned-full/         Fine-tuned BERT model (gitignored)
  esperanto_clean__vocab.txt       Esperanto vocabulary (alignment input)
  esperanto_clean__300d.npy        Esperanto embeddings (alignment input, gitignored)
results/
  bert_ido_epo_alignment/
    translation_candidates.json    Raw alignment output
    alignment_stats.json           Pipeline statistics
```

## Integration with extractor

The output is consumed by `extractor/scripts/build_one_big_bidix_json.py` as
`source_bert_embeddings`. Priority: **Wiktionary > FR pivot > BERT**. If a
lemma has any Wiktionary coverage, BERT translations for that lemma are dropped.

To regenerate the extractor dictionaries after updating BERT output:

```bash
make                                    # update source_bert_embeddings.json
cd ../../extractor && make regenerate   # rebuild bidix → dix
```

## Dependencies

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```
