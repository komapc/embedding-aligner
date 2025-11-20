# BERT Fine-tuning for Ido-Esperanto Translation Discovery

Complete guide for fine-tuning BERT models and using them for cross-lingual translation discovery.

---

## Overview

This pipeline fine-tunes XLM-RoBERTa on Ido corpus and uses the embeddings to discover translation pairs with Esperanto.

**Results:** 2,623 Ido words with 10,124 translation pairs (47× better than Word2Vec baseline)

---

## Quick Start

### 1. Train BERT Model (3-4 hours, GPU recommended)

```bash
python scripts/13_finetune_bert.py \
    --corpus data/processed/ido_wikipedia_plus_wikisource.txt \
    --output models/bert-ido-finetuned \
    --epochs 3 \
    --batch-size 16
```

### 2. Extract Embeddings (20-30 minutes)

```bash
python scripts/14_extract_bert_embeddings.py \
    --model models/bert-ido-finetuned \
    --vocab data/ido_vocabulary.txt \
    --output models/ido_bert_embeddings.npy \
    --batch-size 64
```

### 3. Clean & Project to 300d (4 seconds)

```bash
python scripts/clean_and_project_bert.py \
    --input models/ido_bert_embeddings.npy \
    --vocab models/ido_bert_embeddings_vocab.txt \
    --output-300d models/ido_bert_clean_300d.npy \
    --output-vocab models/ido_bert_vocab_clean.txt
```

### 4. Align with Esperanto (10-15 minutes)

```bash
python scripts/align_bert_with_esperanto.py \
    --ido-bert models/ido_bert_clean_300d.npy \
    --ido-vocab models/ido_bert_vocab_clean.txt \
    --epo-w2v models/esperanto_min3.model \
    --seed-dict data/seed_dictionary.txt \
    --output-dir results/bert_aligned/ \
    --threshold 0.50
```

---

## Pipeline Details

### Step 1: Fine-tuning BERT

**Purpose:** Adapt XLM-RoBERTa to Ido language patterns

**Input:**
- Pre-trained: `xlm-roberta-base` (100 languages)
- Ido corpus: ~392K sentences, 6.5M words

**Output:**
- Fine-tuned model: `models/bert-ido-finetuned/`
- Size: 1.1 GB
- Training loss: 1.6423

**Time & Cost:**
- GPU (g4dn.xlarge): 3 hours, ~$1.58
- CPU (t3.small): 20-30 hours, ~$0.60

**Method:** Masked Language Modeling (MLM)
- Randomly mask 15% of tokens
- Model learns to predict masked tokens
- Adapts to Ido morphology and syntax

### Step 2: Embedding Extraction

**Purpose:** Convert fine-tuned BERT into word embeddings

**Input:**
- Model: `models/bert-ido-finetuned/`
- Vocabulary: 95,435 words

**Output:**
- Embeddings: `models/ido_bert_embeddings.npy` (95,435 × 768)
- Size: 276 MB

**Method:**
- For each word, get BERT's final layer embedding
- Multi-subword tokens: average subword embeddings
- Batch processing for efficiency

### Step 3: Cleaning & Projection

**Purpose:** Remove noise and make compatible with Word2Vec (300d)

**Input:**
- Raw embeddings: 95,435 words × 768 dimensions

**Output:**
- Clean embeddings: 50,641 words × 300 dimensions
- Size: 58 MB

**Cleaning:**
- ✅ Removed 40,022 words with punctuation (`hundo,` → removed)
- ✅ Removed 3,607 words with numbers
- ✅ Removed 715 special tokens
- ✅ Merged 450 case variants

**Projection:**
- ✅ PCA from 768d → 300d
- ✅ Preserves 95.81% variance
- ✅ Compatible with Esperanto Word2Vec

### Step 4: Cross-lingual Alignment

**Purpose:** Align Ido and Esperanto embedding spaces

**Input:**
- Ido BERT: 50,641 words × 300d
- Esperanto Word2Vec: 725,073 words × 300d
- Seed dictionary: 2,610 pairs

**Output:**
- Translation candidates: 2,623 Ido words → 10,124 pairs
- Aligned embeddings for both languages

**Method:** Retrofitting
- Iteratively pull translation pairs closer together
- 10 iterations, alpha=0.5
- Final alignment: 99.99% similarity on seed pairs

**Quality:**
- Average similarity: 0.697
- Threshold: 0.50
- 47× more pairs than Word2Vec baseline

---

## Results

### Quantitative

| Metric | Value |
|--------|-------|
| Ido words with translations | 2,623 |
| Total translation pairs | 10,124 |
| Average pairs per word | 3.9 |
| Average similarity | 0.697 |
| Minimum similarity | 0.500 |
| Vocabulary coverage | 5.2% |

### Quality Examples

```
euro → eŭro (1.000)
krear → krei (1.000) 
generala → ĝenerala (1.000)
doktoro → doktoro, profesoro (1.000, 0.569)
tro → tro, pli, multe (1.000, 0.646, 0.623)
```

### Comparison with Word2Vec

| Method | Ido Words | Pairs | Quality |
|--------|-----------|-------|---------|
| Word2Vec | 130 | 214 | Good |
| **BERT** | **2,623** | **10,124** | **Excellent** |

**Improvement:** 47× more pairs

---

## File Structure

```
models/
├── bert-ido-finetuned-full/        # Fine-tuned BERT model (1.1 GB)
├── ido_bert_embeddings.npy         # Raw embeddings (276 MB, 95K × 768)
├── ido_bert_clean_300d.npy         # Clean embeddings (58 MB, 50K × 300)
├── ido_bert_vocab_clean.txt        # Clean vocabulary (50,641 words)
└── bert_cleaning_stats.json        # Cleaning statistics

results/bert_aligned/
├── bert_candidates.json            # 10,124 translation pairs
├── ido_bert_aligned.npy           # Aligned Ido embeddings
├── epo_w2v_aligned.npy            # Aligned Esperanto embeddings
└── bert_alignment_stats.json      # Alignment statistics

scripts/
├── 13_finetune_bert.py            # Fine-tuning script
├── 14_extract_bert_embeddings.py  # Embedding extraction
├── clean_and_project_bert.py      # Cleaning & PCA
└── align_bert_with_esperanto.py   # Cross-lingual alignment

logs/
├── bert_finetuning_*.log
├── bert_embedding_extraction_*.log
├── bert_cleaning_*.log
└── bert_alignment_*.log
```

---

## Requirements

### Python Packages

```bash
pip install torch transformers datasets
pip install gensim scikit-learn numpy tqdm
```

### Hardware

**For fine-tuning:**
- GPU: 16+ GB VRAM (recommended: g4dn.xlarge)
- RAM: 16+ GB
- Storage: 50+ GB

**For inference (extraction, alignment):**
- CPU is sufficient
- RAM: 8+ GB
- Storage: 10+ GB

---

## Configuration Options

### Fine-tuning

```python
--epochs 3              # Number of training epochs
--batch-size 16         # Batch size (reduce if OOM)
--learning-rate 2e-5    # Learning rate
--max-seq-length 256    # Maximum sequence length
--sample-percent 10     # Use only X% of corpus (testing)
```

### Cleaning

```python
--dims 300              # Target dimensions (default: 300)
--no-merge-duplicates   # Don't merge case variants
```

### Alignment

```python
--threshold 0.50        # Minimum similarity for candidates
--iterations 10         # Retrofitting iterations
--alpha 0.5            # Retrofitting alpha parameter
```

---

## Cost Analysis

| Resource | Time | Cost |
|----------|------|------|
| **Fine-tuning (GPU)** | 3 hours | $1.58 |
| Embedding extraction | 22 min | $0.00 (CPU) |
| Cleaning & PCA | 4 sec | $0.00 (CPU) |
| Alignment | 11 min | $0.00 (CPU) |
| **Total** | **~3.5 hours** | **~$1.58** |

**Per translation pair:** $0.00016

---

## Troubleshooting

### OOM Error During Fine-tuning

**Solution:** Reduce batch size
```bash
--batch-size 8  # or even 4
```

### Poor Alignment Results

**Check:**
1. Seed dictionary format (space-separated, lowercase)
2. Vocabulary overlap (should be 2,000+ pairs)
3. Dimensions match (both 300d)

### Low Quality Translations

**Solutions:**
1. Increase threshold to 0.60 (fewer but better pairs)
2. Add POS filtering
3. Manual validation of top candidates

---

## Best Practices

### 1. Preprocessing

✅ **Do:**
- Remove punctuation before training
- Lowercase normalization
- Proper sentence segmentation

❌ **Don't:**
- Train on raw Wikipedia XML
- Include special tokens without filtering
- Mix multiple languages without labels

### 2. Training

✅ **Do:**
- Use GPU for fine-tuning (20× faster)
- Save checkpoints every 1000 steps
- Monitor training loss

❌ **Don't:**
- Train for too many epochs (overfitting)
- Use learning rate > 5e-5
- Skip validation set

### 3. Post-processing

✅ **Do:**
- Always clean embeddings (remove punctuation)
- Use PCA for dimension reduction
- Normalize embeddings before alignment

❌ **Don't:**
- Use raw embeddings directly
- Skip dimension matching
- Ignore similarity thresholds

---

## Lessons Learned

### What Worked ✅

1. **Post-processing is powerful**
   - Simple cleaning = 47× improvement
   - No retraining needed ($0 cost)

2. **PCA preserves quality**
   - 95.81% variance with 768d → 300d
   - Perfect alignment achieved

3. **Retrofitting is robust**
   - Works with compressed embeddings
   - 99.99% seed pair alignment

### What Didn't Work ❌

1. **Small corpus for BERT**
   - 392K sentences insufficient
   - Recommend 1M+ sentences

2. **No punctuation preprocessing**
   - Creates embedding noise
   - Fix: Post-processing cleanup

3. **Direct dimension comparison**
   - 768d vs 300d incompatible
   - Fix: PCA projection

---

## Future Improvements

### Short-term

1. ✅ Manual validation (top 500 pairs)
2. ✅ Format for Apertium (.dix)
3. ✅ Merge with Word2Vec results

### Medium-term

1. Larger Ido corpus (target: 1M+ sentences)
2. Fine-tune on both Ido + Esperanto
3. Use Translation Language Modeling (TLM)

### Long-term

1. Sentence-level embeddings (Sentence-BERT)
2. Multilingual model (add more languages)
3. Active learning from Apertium errors

---

## References

### Papers

- **XLM-RoBERTa:** Conneau et al. (2020) - Unsupervised Cross-lingual Representation Learning at Scale
- **Retrofitting:** Faruqui et al. (2015) - Retrofitting Word Vectors to Semantic Lexicons
- **Cross-lingual Embeddings:** Ruder et al. (2019) - A Survey of Cross-lingual Word Embedding Models

### Documentation

- Hugging Face Transformers: https://huggingface.co/docs/transformers
- Gensim: https://radimrehurek.com/gensim/
- Scikit-learn PCA: https://scikit-learn.org/stable/modules/decomposition.html

---

## Citation

If you use this pipeline in your research, please cite:

```bibtex
@software{ido_esperanto_bert,
  title = {BERT Fine-tuning for Ido-Esperanto Translation Discovery},
  author = {Apertium Development Team},
  year = {2025},
  url = {https://github.com/apertium/apertium-ido-epo}
}
```

---

## License

GPL-3.0 (same as Apertium)

---

## Support

For issues or questions:
- File an issue: https://github.com/apertium/apertium-ido-epo/issues
- Apertium IRC: #apertium on irc.oftc.net
- Mailing list: apertium-stuff@lists.sourceforge.net

---

*Last updated: November 20, 2025*

