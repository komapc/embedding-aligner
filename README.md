# Ido-Esperanto Embedding Aligner

Cross-lingual word embedding alignment for discovering translations between Ido and Esperanto using Word2Vec and Procrustes alignment.

---

## Overview

This project trains word embeddings for Ido and Esperanto, then aligns them to discover new translation pairs for the Apertium machine translation platform.

**Key Features:**
- ✅ Wikipedia-based corpus extraction
- ✅ Word2Vec Skip-gram embedding training
- ✅ Procrustes alignment for cross-lingual mapping
- ✅ Translation candidate discovery
- ✅ Apertium bidix integration

---

## Quick Start

### 1. Download Wikipedia Dumps
```bash
bash scripts/01_download_wikipedia.sh
```

Downloads:
- **Esperanto**: 348 MB (~344K articles)
- **Ido**: 40 MB (~40K articles)

### 2. Parse to Clean Text
```bash
# Esperanto (full corpus)
python3 scripts/parse_wikipedia_epo.py \
  --input data/raw/eowiki-latest-pages-articles.xml.bz2 \
  --output data/processed/esperanto_full.txt

# Ido (full corpus)
python3 scripts/parse_wikipedia_epo.py \
  --input data/raw/iowiki-latest-pages-articles.xml.bz2 \
  --output data/processed/ido_full.txt
```

**Time:** ~7-10 minutes per language

### 3. Train Embeddings
```bash
# Esperanto (15-20 hours)
nohup python3 scripts/train_esperanto_embeddings.py \
  --corpus data/processed/esperanto_full.txt \
  --output models/esperanto_full.model \
  --config combined-best > /tmp/train_epo.log 2>&1 &

# Ido (2-3 hours)
nohup python3 scripts/train_esperanto_embeddings.py \
  --corpus data/processed/ido_full.txt \
  --output models/ido_full.model \
  --config combined-best > /tmp/train_ido.log 2>&1 &
```

**Monitor training:**
```bash
./check_training_status.sh
# or
tail -f /tmp/train_epo.log
```

### 4. Test Models
```bash
# Query Esperanto model
python3 scripts/query_nearest_words.py \
  models/esperanto_full.model hundo --topn 15

# Query Ido model
python3 scripts/query_nearest_words.py \
  models/ido_full.model hundo --topn 15
```

**Expected output:** Semantically related words (animals for "hundo", colors for "ruĝa", etc.)

### 5. Align and Discover Translations
```bash
# Extract seed dictionary from Apertium
python3 scripts/04_extract_seed_dict.py \
  --bidix ~/apertium-dev/apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix \
  --output data/dictionaries/seed_ido_epo.txt

# Align embedding spaces (Procrustes)
python3 scripts/05_align_embeddings.py \
  --source-model models/ido_full.model \
  --target-model models/esperanto_full.model \
  --seed-dict data/dictionaries/seed_ido_epo.txt \
  --output-matrix data/alignment/W_ido_to_epo.npy

# Find translation candidates
python3 scripts/06_find_candidates.py \
  --source-model models/ido_full.model \
  --target-model models/esperanto_full.model \
  --alignment-matrix data/alignment/W_ido_to_epo.npy \
  --output data/candidates/ido_epo_candidates.json
```

---

## Documentation

- **[TOOLS.md](TOOLS.md)** - Complete tool reference and usage guide
- **[ALIGNMENT_GUIDE.md](ALIGNMENT_GUIDE.md)** - Technical details on alignment methodology

---

## Project Structure

```
embedding-aligner/
├── README.md                    # This file
├── TOOLS.md                     # Complete tool documentation
├── ALIGNMENT_GUIDE.md           # Alignment methodology
│
├── scripts/
│   ├── 01_download_wikipedia.sh           # Download Wikipedia dumps
│   ├── parse_wikipedia_epo.py             # Parse XML to clean text
│   ├── train_esperanto_embeddings.py      # Train Word2Vec models
│   ├── query_nearest_words.py             # Test trained models
│   ├── 04_extract_seed_dict.py            # Extract Apertium dictionary
│   ├── 05_align_embeddings.py             # Procrustes alignment
│   ├── 06_find_candidates.py              # Translation discovery
│   └── 07_validate_candidates.py          # Validation
│
├── data/
│   ├── raw/                     # Wikipedia dumps (.xml.bz2)
│   ├── processed/               # Clean text corpora (.txt)
│   ├── dictionaries/            # Seed dictionaries
│   ├── alignment/               # Alignment matrices
│   └── candidates/              # Translation candidates
│
├── models/                      # Trained embedding models
│   ├── ido_full.model
│   ├── esperanto_full.model
│   ├── esperanto_10pct.model    # 10% corpus for testing
│   └── esperanto_test.model     # 1K articles (poor quality)
│
└── results/                     # Analysis and validation outputs
```

---

## Model Specifications

### Training Configuration

Both models use **identical parameters** for alignment compatibility:

```python
{
    'vector_size': 300,       # Embedding dimensions
    'window': 5,              # Context window size
    'min_count': 15,          # Minimum word frequency
    'sg': 1,                  # Skip-gram algorithm
    'negative': 10,           # Negative sampling
    'epochs': 30,             # Training iterations
    'sample': 1e-5,           # Subsampling threshold
    'filter_proper': True,    # Remove proper nouns
}
```

### Model Sizes

| Language | Articles | Vocabulary | Corpus Size | Training Time | Model Size |
|----------|----------|------------|-------------|---------------|------------|
| **Esperanto 100%** | 344,183 | ~150K-200K | 371 MB (59.5M words) | 15-20 hours | ~150-200 MB |
| **Esperanto 10%** | 36,000 | 42,456 | 66 MB (10.5M words) | 15 minutes | 50 MB |
| **Ido 100%** | ~40,000 | ~18K-25K | 36 MB (6M words) | 2-3 hours | ~50 MB |

---

## Quality Assessment

### Good Model Indicators

```bash
$ python3 scripts/query_nearest_words.py models/esperanto_10pct.model hundo

🎯 Nearest words to 'hundo':
============================================================
 1. ŝafhundo     (sheepdog)     │ 0.3986  ✓ Related breed
 2. terhundo     (terrier)      │ 0.3770  ✓ Related breed
 3. gepardo      (cheetah)      │ 0.3505  ✓ Related animal
 4. porko        (pig)          │ 0.3416  ✓ Related animal
 5. kuniklo      (rabbit)       │ 0.3410  ✓ Related animal
```

**✓ Good:** Animals cluster together, related terms, morphological variants

### Poor Model Indicators

```bash
$ python3 scripts/query_nearest_words.py models/esperanto_test.model hundo

🎯 Nearest words to 'hundo':
============================================================
 1. í            (suffix)       │ 0.5661  ✗ Grammar jargon
 2. laŭvorte     (literally)    │ 0.5604  ✗ Meta-language
 3. il           (tool suffix)  │ 0.5565  ✗ Morphology
 4. sufikso      (suffix)       │ 0.5518  ✗ Grammar term
```

**✗ Poor:** Corpus too small or biased toward linguistics articles

**Solution:** Use 10% or 100% corpus for production.

---

## Expected Results

### Translation Discovery

Using Procrustes alignment with a seed dictionary of 1,000-5,000 pairs:

- **Precision@1**: 60-75%
- **Precision@5**: 85-95%
- **New high-confidence pairs**: 1,000-3,000
- **Coverage**: Most common words + many mid-frequency terms

### Use Cases

1. **Dictionary Expansion**: Add discovered pairs to Apertium bidix
2. **Translation Validation**: Verify existing translations
3. **Coverage Analysis**: Identify missing translations
4. **Semantic Clustering**: Find related word groups

---

## Workflow Timeline

| Phase | Time | Attended? |
|-------|------|-----------|
| 1. Download Wikipedia | 5-10 min | No (wget) |
| 2. Parse corpus | 7-10 min | No |
| 3. Train Esperanto | 15-20 hours | No (background) |
| 4. Train Ido | 2-3 hours | No (background) |
| 5. Test models | 2 min | Yes |
| 6. Extract seed dict | 1 min | Yes |
| 7. Align embeddings | 5-10 min | No |
| 8. Find candidates | 10-30 min | No |
| **TOTAL** | **~18-24 hours** | Mostly unattended |

---

## Requirements

### System
- **OS**: Linux (tested on Ubuntu)
- **RAM**: 4 GB minimum, 8 GB recommended
- **Disk**: 2 GB free space
- **CPU**: Multi-core recommended (4+ cores)

### Python
- **Version**: Python 3.8+
- **Dependencies**: See `requirements.txt`

```bash
pip install -r requirements.txt
# Main dependencies:
# - gensim (Word2Vec)
# - numpy (numerical operations)
# - scipy (SVD for alignment)
```

---

## Advanced Usage

### Corpus Sampling for Testing

Test with 10% corpus before full training:

```bash
python3 scripts/parse_wikipedia_epo.py \
  --input data/raw/eowiki-latest-pages-articles.xml.bz2 \
  --output data/processed/esperanto_10pct.txt \
  --limit 36000
```

**Benefits:**
- Fast feedback (15 minutes vs 20 hours)
- Test configuration
- Verify data quality
- Debug issues quickly

### Custom Configuration

Edit `scripts/train_esperanto_embeddings.py` and add custom config:

```python
configs = {
    'my_config': {
        'vector_size': 200,      # Smaller, faster
        'window': 10,            # Larger context
        'min_count': 5,          # Include rarer words
        'epochs': 50,            # More training
        # ... other parameters
    }
}
```

Then run:
```bash
python3 scripts/train_esperanto_embeddings.py \
  --corpus data/processed/esperanto_full.txt \
  --output models/esperanto_custom.model \
  --config my_config
```

---

## Troubleshooting

### Training killed / Out of memory
```bash
# Check available memory
free -h

# Reduce workers in script:
'workers': 2,  # instead of 4

# Or use swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Poor query results
- **Corpus too small**: Use 10% or 100%, not test (1K)
- **Biased corpus**: Check for excessive linguistics articles
- **Wrong config**: Ensure `sg=1` (Skip-gram), not CBOW
- **Min_count too high**: Lower to 10 or 5 for smaller corpora

### Alignment fails
- **Different configurations**: Both models must use same parameters
- **Insufficient seed pairs**: Need 1,000+ translation pairs
- **Models not loaded**: Check file paths and .npy files

### Download errors
```bash
# Resume interrupted download
wget -c https://dumps.wikimedia.org/eowiki/latest/eowiki-latest-pages-articles.xml.bz2 \
  -O data/raw/eowiki-latest-pages-articles.xml.bz2
```

---

## References

### Papers
- Mikolov et al. (2013): "Exploiting Similarities among Languages for Machine Translation"
- Conneau et al. (2018): "Word Translation Without Parallel Data" (MUSE)
- Artetxe et al. (2018): "A robust self-learning method for fully unsupervised cross-lingual mappings"

### Related Projects
- **Apertium**: https://www.apertium.org/
- **Apertium Ido-Esperanto**: `~/apertium-dev/apertium/apertium-ido-epo/`
- **MUSE**: Facebook's multilingual embeddings (https://github.com/facebookresearch/MUSE)

---

## Contributing

This is part of the Apertium project. Contributions welcome!

1. Test with your own language pairs
2. Improve parsing or training
3. Add validation tools
4. Expand documentation

---

## License

Part of the Apertium machine translation platform.
Open source and free to use.

---

**Ready to start?** See [TOOLS.md](TOOLS.md) for detailed usage instructions.

**Questions?** Open an issue or check existing documentation.
