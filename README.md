# Ido-Esperanto Dictionary Expansion via Cross-Lingual Embeddings

## Goal

Expand the existing 50K Ido↔Esperanto dictionary by finding missing translations using cross-lingual word embeddings with high precision.

## Approach

1. Train monolingual FastText embeddings on Ido and Esperanto Wikipedia
2. Align embedding spaces using VecMap with supervised learning (45K seed pairs)
3. Find translation candidates for unknown words using CSLS nearest neighbor search
4. Filter for high precision (similarity > 0.7, mutual nearest neighbors)
5. Validate and integrate new translations

## Project Structure

```
embedding-aligner/
├── data/                    # Wikipedia dumps and processed corpora
│   ├── raw/                # Raw Wikipedia XML dumps
│   ├── processed/          # Cleaned text corpora
│   └── dictionaries/       # Seed and output dictionaries
├── scripts/                # Python scripts for pipeline
│   ├── 01_download_wikipedia.sh
│   ├── 02_preprocess.py
│   ├── 03_train_embeddings.sh
│   ├── 04_align_embeddings.sh
│   └── 05_find_candidates.py
├── models/                 # Trained embeddings and alignments
│   ├── ido_vectors.vec
│   ├── epo_vectors.vec
│   ├── ido_aligned.vec
│   └── epo_aligned.vec
├── results/                # Output candidates and validation
└── requirements.txt        # Python dependencies
```

## Prerequisites

- Python 3.8+
- FastText
- VecMap
- 50K Ido-Esperanto seed dictionary
- ~10GB disk space for Wikipedia dumps and embeddings

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Download Wikipedia dumps
bash scripts/01_download_wikipedia.sh

# 3. Preprocess corpora
python scripts/02_preprocess.py

# 4. Train FastText embeddings
bash scripts/03_train_embeddings.sh

# 5. Align embedding spaces
bash scripts/04_align_embeddings.sh

# 6. Find translation candidates
python scripts/05_find_candidates.py
```

## Expected Results

With high precision threshold (similarity > 0.7):
- **New translation pairs**: 200-800
- **Precision**: 90-95%
- **Processing time**: 1-2 days (mostly training)

## Technical Details

### Embeddings
- **Model**: FastText skipgram
- **Dimensions**: 300
- **Window size**: 5
- **Min count**: 5
- **Epochs**: 5

### Alignment
- **Method**: VecMap supervised with orthogonal constraint
- **Seed dictionary**: 45K pairs (90% of existing dictionary)
- **Validation set**: 5K pairs (10% held out)

### Candidate Generation
- **Retrieval**: CSLS (Cross-domain Similarity Local Scaling)
- **Threshold**: 0.7 (high precision)
- **Filters**: Mutual nearest neighbors, frequency checks

## References

1. **VecMap**: Artetxe et al. (2018) "A robust self-learning method for fully unsupervised cross-lingual mappings of word embeddings"
2. **FastText**: Bojanowski et al. (2017) "Enriching Word Vectors with Subword Information"
3. **CSLS**: Conneau et al. (2018) "Word Translation Without Parallel Data"

## Status

- [ ] Setup complete
- [ ] Wikipedia downloaded
- [ ] Corpora preprocessed
- [ ] Embeddings trained
- [ ] Alignment completed
- [ ] Candidates generated
- [ ] Manual validation done
- [ ] Integration complete
