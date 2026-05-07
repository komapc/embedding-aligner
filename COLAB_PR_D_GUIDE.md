# PR D Colab Experiment Guide

Train an XLM-RoBERTa model on **lemmatized Ido text** (30k sentences) on
Google Colab's free T4 GPU. ~10 minutes wall-clock. Tests whether
training on lemmas improves cross-lingual alignment without committing
to the full 11h training run.

## Step 1 — files prepared locally

You already have:
```
data/processed/ido_corpus_lemma_30k.txt   2.6 MB · 30,000 sentences (lemmatized)
data/processed/ido_corpus_surface_30k.txt 2.6 MB · same sentences (surface forms — control)
```

## Step 2 — open Colab

1. Go to https://colab.research.google.com
2. New notebook
3. Runtime → Change runtime type → **T4 GPU** → Save
4. Verify GPU: paste in a cell and run:
   ```
   !nvidia-smi
   ```
   Should show "Tesla T4" with ~15GB VRAM.

## Step 3 — upload the corpus

In the Colab left sidebar (folder icon), click "Upload to session storage" and upload:
- `ido_corpus_lemma_30k.txt`
- `ido_corpus_surface_30k.txt`

Or use a single cell:
```python
from google.colab import files
uploaded = files.upload()  # opens browser file picker
```

## Step 4 — install dependencies

Paste in a cell:
```python
!pip install -q transformers==4.46.3 datasets accelerate
```

## Step 5 — fine-tune on the lemmatized corpus

Paste in a cell. Takes ~8–12 min on T4.

```python
import os
import torch
from transformers import (
    XLMRobertaTokenizer, XLMRobertaForMaskedLM,
    DataCollatorForLanguageModeling, Trainer, TrainingArguments
)
from datasets import Dataset

CORPUS = "ido_corpus_lemma_30k.txt"   # ← change to surface_30k.txt for control run
OUTPUT = "bert-ido-lemma-30k"
BASE   = "xlm-roberta-base"

# Load corpus
with open(CORPUS, encoding="utf-8") as f:
    lines = [l.strip() for l in f if l.strip()]
print(f"Corpus: {len(lines):,} sentences")

# Tokenizer + model
print("Loading XLM-RoBERTa base...")
tokenizer = XLMRobertaTokenizer.from_pretrained(BASE)
model = XLMRobertaForMaskedLM.from_pretrained(BASE)

# Tokenize
def tok(b): return tokenizer(b["text"], truncation=True, max_length=64, padding=False)
ds = Dataset.from_dict({"text": lines}).map(tok, batched=True, remove_columns=["text"])

# Trainer
collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=True, mlm_probability=0.15)
args = TrainingArguments(
    output_dir=OUTPUT,
    num_train_epochs=1,
    per_device_train_batch_size=32,
    save_steps=500,
    logging_steps=50,
    fp16=True,                         # T4 supports fp16 — ~2x speedup
    save_total_limit=1,
    report_to="none",
)
trainer = Trainer(model=model, args=args, train_dataset=ds, data_collator=collator)
trainer.train()

# Save final model
trainer.save_model(OUTPUT)
tokenizer.save_pretrained(OUTPUT)
print(f"✅ Saved to {OUTPUT}")
```

## Step 6 — download trained model

Single-file zip + download:

```python
!tar czf bert-ido-lemma-30k.tar.gz bert-ido-lemma-30k
from google.colab import files
files.download("bert-ido-lemma-30k.tar.gz")  # ~1 GB
```

## Step 7 — back on your laptop, test it

Extract into the project:
```bash
cd ~/projects/apertium-dev/projects/embedding-aligner
mkdir -p models/bert-ido-lemma-30k
tar xzf ~/Downloads/bert-ido-lemma-30k.tar.gz -C models/
```

Run stage 14 + 15 with the new model:
```bash
venv/bin/python3 scripts/14_extract_bert_embeddings.py \
  --model models/bert-ido-lemma-30k \
  --vocab data/ido_vocabulary_filtered.txt \
  --output embeddings/ido_bert_lemma30k.npz

venv/bin/python3 scripts/15_bert_crosslingual_alignment.py \
  --bert-model models/bert-ido-lemma-30k \
  --ido-embeddings embeddings/ido_bert_lemma30k.npz \
  --epo-vocab models/esperanto_clean__vocab.txt \
  --epo-model models/esperanto_clean__300d.npy \
  --output-dir results/bert_lemma30k_alignment
```

## Step 8 — compare against current production model

Stage 15 prints `precision@1` against the seed dictionary. Compare:
```
results/bert_ido_epo_alignment/alignment_stats.json   ← current (full surface 361k)
results/bert_lemma30k_alignment/alignment_stats.json  ← experiment (lemma 30k)
```

**Decision gate:** if the lemma-30k model's top-1 ≥ the surface-361k baseline, the lemmatization idea is working — commit to a full 11h run. If it's significantly worse, the idea doesn't pay off.

## Optional — control run

To do the apples-to-apples comparison (same data scope, different preprocessing):
1. Re-run Step 5 with `CORPUS = "ido_corpus_surface_30k.txt"` and `OUTPUT = "bert-ido-surface-30k"`.
2. Test it the same way as Step 7-8.
3. Compare lemma-30k vs surface-30k.

This is the cleanest test of "does lemmatizing the training data help?"

## Tips

- **Don't close the tab.** Colab disconnects after ~90s of inactivity.
- If the runtime dies mid-training, your last `save_steps=500` checkpoint is in `bert-ido-lemma-30k/checkpoint-500/`. Restart and use `Trainer.train(resume_from_checkpoint=True)`.
- For a SMALLER faster test (3 min instead of 10), reduce to first 5000 lines:
  `lines = lines[:5000]`
