# Embedding Aligner Tools Documentation

Complete guide to all tools for training Ido and Esperanto word embeddings and aligning them for translation discovery.

---

## Table of Contents

1. [Wikipedia Processing](#wikipedia-processing)
2. [Embedding Training](#embedding-training)
3. [Model Querying](#model-querying)
4. [Alignment and Translation Discovery](#alignment-and-translation-discovery)
5. [Utilities](#utilities)

---

## Wikipedia Processing

### parse_wikipedia_epo.py

Parses Esperanto Wikipedia XML dumps into clean text corpus for embedding training.

**Usage:**
```bash
python3 scripts/parse_wikipedia_epo.py \
  --input data/raw/eowiki-latest-pages-articles.xml.bz2 \
  --output data/processed/esperanto_corpus.txt \
  --limit 36000  # Optional: limit number of articles
```

**Parameters:**
- `--input`: Path to Wikipedia XML dump (.xml, .bz2, or .gz)
- `--output`: Output text file (one sentence per line)
- `--limit`: (Optional) Limit number of articles for testing

**Features:**
- Handles compressed files (.bz2, .gz) automatically
- Removes templates, references, markup
- Extracts main article content only
- Filters proper nouns (optional)
- Progress reporting every 1,000 articles
- Processes ~600-800 articles/second

**Example Output:**
```
Processing data/raw/eowiki-latest-pages-articles.xml.bz2...
  Processed 1,000 articles (27,293 sentences, 256 articles/sec)
  Processed 2,000 articles (53,702 sentences, 259 articles/sec)
  ...
Articles:        36,000
Sentences:       417,053
Words:           10,470,510
```

**For Ido:** Use the same script on Ido Wikipedia dumps (replace `eowiki` with `iowiki`).

---

## Embedding Training

### train_esperanto_embeddings.py

Trains Word2Vec embeddings on processed Esperanto corpus.

**Usage:**
```bash
python3 scripts/train_esperanto_embeddings.py \
  --corpus data/processed/esperanto_corpus.txt \
  --output models/esperanto.model \
  --config combined-best
```

**Parameters:**
- `--corpus`: Input text file (one sentence per line)
- `--output`: Output model file path
- `--config`: Configuration preset (see below)

**Configuration Presets:**

1. **combined-best** (Recommended):
```python
{
    'vector_size': 300,      # Embedding dimensions
    'window': 5,             # Context window
    'min_count': 15,         # Minimum word frequency
    'sg': 1,                 # Skip-gram algorithm
    'negative': 10,          # Negative samples
    'epochs': 30,            # Training epochs
    'sample': 1e-5,          # Subsampling threshold
    'filter_proper': True,   # Remove proper nouns
}
```

2. **baseline**: Standard configuration without filtering
3. **custom**: Modify parameters in the script

**Training Time:**
- 10% corpus (36K articles): ~15 minutes
- 100% corpus (344K articles): ~15-20 hours

**Example Output:**
```
Loading corpus from data/processed/esperanto_corpus.txt
Corpus loaded: 417,053 sentences, 10,470,510 words
Training Word2Vec model...
Starting epoch 1
...
Training completed in 896.23 seconds
Vocabulary size: 42,456 words
Model saved to: models/esperanto.model
```

**For Ido:** Works identically for Ido corpora. The configuration must match for alignment compatibility.

---

## Model Querying

### query_nearest_words.py

Query trained models to find semantically similar words.

**Usage:**
```bash
python3 scripts/query_nearest_words.py \
  models/esperanto.model \
  hundo \
  --topn 15
```

**Parameters:**
- `model_path`: Path to trained .model file
- `word`: Query word (lowercase)
- `--topn`: Number of nearest neighbors to return (default: 10)

**Example Output:**
```
Loading model from: models/esperanto_10pct.model
✅ Model loaded successfully!
   Vocabulary size: 42456
   Vector dimensions: 300

🎯 Nearest words to 'hundo':
============================================================
 1. ŝafhundo             │ ███████████████░░░░░░░░░░░░░ │ 0.3986
 2. terhundo             │ ███████████████░░░░░░░░░░░░░ │ 0.3770
 3. gepardo              │ ██████████████░░░░░░░░░░░░░░ │ 0.3505
 4. porko                │ █████████████░░░░░░░░░░░░░░░ │ 0.3416
 5. kuniklo              │ █████████████░░░░░░░░░░░░░░░ │ 0.3410
...
```

**Testing Model Quality:**
```bash
# Animals should cluster together
python3 scripts/query_nearest_words.py models/esperanto.model hundo
python3 scripts/query_nearest_words.py models/esperanto.model kato

# Colors should cluster
python3 scripts/query_nearest_words.py models/esperanto.model ruĝa
python3 scripts/query_nearest_words.py models/esperanto.model blua

# Actions should cluster
python3 scripts/query_nearest_words.py models/esperanto.model kuri
python3 scripts/query_nearest_words.py models/esperanto.model manĝi
```

**Works for both Ido and Esperanto models.**

---

## Alignment and Translation Discovery

### 04_extract_seed_dict.py

Extracts seed dictionary from Apertium bidix file.

**Usage:**
```bash
python3 scripts/04_extract_seed_dict.py \
  --bidix ~/apertium-dev/apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix \
  --output data/dictionaries/seed_ido_epo.txt
```

**Output Format:**
```
hundo hundo
kato kato
domo domo
...
```

### 05_align_embeddings.py

Aligns Ido and Esperanto embedding spaces using Procrustes alignment.

**Usage:**
```bash
python3 scripts/05_align_embeddings.py \
  --source-model models/ido.model \
  --target-model models/esperanto.model \
  --seed-dict data/dictionaries/seed_ido_epo.txt \
  --output-matrix data/alignment/W_ido_to_epo.npy
```

**Algorithm:**
1. Loads both embedding models
2. Finds transformation matrix W: `W = U·Vᵀ` (SVD-based)
3. Saves alignment matrix for translation

### 06_find_candidates.py

Finds translation candidates using aligned embeddings.

**Usage:**
```bash
python3 scripts/06_find_candidates.py \
  --source-model models/ido.model \
  --target-model models/esperanto.model \
  --alignment-matrix data/alignment/W_ido_to_epo.npy \
  --output data/candidates/ido_epo_candidates.json \
  --topk 5
```

**Output:** JSON file with translation candidates and confidence scores.

---

## Utilities

### check_training_status.sh

Monitor ongoing training processes.

**Usage:**
```bash
cd /home/mark/apertium-dev/projects/embedding-aligner
./check_training_status.sh
```

**Output:**
```
════════════════════════════════════════════════════════════════
  ESPERANTO EMBEDDING TRAINING STATUS
════════════════════════════════════════════════════════════════

✓ Training process: RUNNING
  PID: 56568
  CPU: 384%
  Memory: 2.6%
  Time: 51:02

⏳ Status: Training in progress...
   Expected time: 30-60 minutes total

✓ Model file detected:
  models/esperanto_10pct.model - 1.3M
  models/esperanto_10pct.model.wv.vectors.npy - 49M
  models/esperanto_10pct.model.syn1neg.npy - 49M
```

### 01_download_wikipedia.sh

Downloads Wikipedia dumps for both languages.

**Usage:**
```bash
bash scripts/01_download_wikipedia.sh
```

Downloads:
- Ido: `iowiki-latest-pages-articles.xml.bz2` (~40 MB)
- Esperanto: `eowiki-latest-pages-articles.xml.bz2` (~348 MB)

---

## Complete Workflow

### 1. Download Wikipedia Dumps
```bash
bash scripts/01_download_wikipedia.sh
```

### 2. Parse to Clean Text
```bash
# Esperanto (10% for testing)
python3 scripts/parse_wikipedia_epo.py \
  --input data/raw/eowiki-latest-pages-articles.xml.bz2 \
  --output data/processed/esperanto_10pct.txt \
  --limit 36000

# Esperanto (100% for production)
python3 scripts/parse_wikipedia_epo.py \
  --input data/raw/eowiki-latest-pages-articles.xml.bz2 \
  --output data/processed/esperanto_full.txt

# Ido (full)
python3 scripts/parse_wikipedia_epo.py \
  --input data/raw/iowiki-latest-pages-articles.xml.bz2 \
  --output data/processed/ido_full.txt
```

### 3. Train Embeddings
```bash
# Esperanto
nohup python3 scripts/train_esperanto_embeddings.py \
  --corpus data/processed/esperanto_full.txt \
  --output models/esperanto_full.model \
  --config combined-best > /tmp/train_epo.log 2>&1 &

# Ido (same script, different corpus)
nohup python3 scripts/train_esperanto_embeddings.py \
  --corpus data/processed/ido_full.txt \
  --output models/ido_full.model \
  --config combined-best > /tmp/train_ido.log 2>&1 &
```

### 4. Test Models
```bash
# Esperanto
python3 scripts/query_nearest_words.py models/esperanto_full.model hundo --topn 15

# Ido
python3 scripts/query_nearest_words.py models/ido_full.model hundo --topn 15
```

### 5. Align and Find Translations
```bash
# Extract seed dictionary
python3 scripts/04_extract_seed_dict.py \
  --bidix ~/apertium-dev/apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix \
  --output data/dictionaries/seed_ido_epo.txt

# Align embedding spaces
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

## Model Specifications

### Esperanto Models

| Model | Articles | Vocabulary | Corpus Size | Training Time | File Size |
|-------|----------|------------|-------------|---------------|-----------|
| test (1K) | 1,000 | 4,870 | 4.5 MB | < 5 min | 12 MB |
| 10% | 36,000 | 42,456 | 66 MB | ~15 min | 50 MB |
| full | 344,183 | ~150K-200K | 371 MB | ~15-20 hrs | ~150-200 MB |

### Ido Models

| Model | Articles | Vocabulary | Corpus Size | Training Time | File Size |
|-------|----------|------------|-------------|---------------|-----------|
| full | ~40,000 | ~18K-25K | 36 MB | ~2-3 hrs | ~50 MB |

---

## Corpus Quality Assessment

**Good Model Indicators:**
- Animals cluster together (hundo → kato, ĉevalo, bovo)
- Related concepts cluster (reĝo → princo, regno, imperiestro)
- Morphological variants appear (hundo → hundoj, hundaro)
- No excessive grammar jargon (sufikso, morfologio, etc.)

**Poor Model Indicators:**
- Unrelated words (hundo → sufikso, laŭvorte)
- Grammar terminology dominates
- Low vocabulary (<10K words)
- Corpus too small (<10M words)

**Solution:** Use larger, more diverse corpus (100% Wikipedia recommended).

---

## Troubleshooting

### Model file not found
```bash
# Check if all required files exist
ls -lh models/esperanto_full.model*

# Should see:
# esperanto_full.model (main file)
# esperanto_full.model.wv.vectors.npy (word vectors)
# esperanto_full.model.syn1neg.npy (negative sampling)
```

### Training killed / Out of memory
```bash
# Check available memory
free -h

# Reduce workers if needed (edit script):
'workers': 2,  # instead of 4
```

### Poor query results
- Corpus too small → Use full Wikipedia
- Corpus biased → Check for linguistics articles
- Min_count too high → Lower to 10 or 5
- Wrong configuration → Ensure Skip-gram (sg=1)

---

## Advanced Usage

### Custom Training Configuration

Edit `scripts/train_esperanto_embeddings.py`:

```python
configs = {
    'custom': {
        'vector_size': 300,
        'window': 10,        # Larger context window
        'min_count': 5,      # Include rarer words
        'workers': 4,
        'sg': 1,
        'negative': 15,      # More negative samples
        'epochs': 50,        # More training iterations
        'alpha': 0.05,
        'min_alpha': 0.0001,
        'sample': 1e-5,
        'filter_proper': False,  # Keep proper nouns
    }
}
```

### Parallel Training (Multiple Languages)

```bash
# Train both simultaneously on different cores
nohup python3 scripts/train_esperanto_embeddings.py \
  --corpus data/processed/esperanto_full.txt \
  --output models/esperanto_full.model &

nohup python3 scripts/train_esperanto_embeddings.py \
  --corpus data/processed/ido_full.txt \
  --output models/ido_full.model &
```

---

## Performance Tips

### Speed up parsing
- Use SSD storage
- Increase available RAM
- Run on multi-core CPU

### Speed up training
- Use more workers (4-8 on multi-core)
- Use BLAS-optimized NumPy
- Run on CPU with AVX2 support

### Reduce model size
- Increase min_count (15→25)
- Reduce vector_size (300→200)
- Filter more aggressively

---

## Citation

If you use these tools, please cite:

```
Apertium Ido-Esperanto Embedding Aligner
Word embedding training and alignment for Ido↔Esperanto translation discovery
https://github.com/apertium/
```

---

## License

Part of the Apertium machine translation platform.
All tools are open source and free to use.

