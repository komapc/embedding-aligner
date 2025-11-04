# Cross-Lingual Word Embedding Alignment Plan

## Overview

This document describes the plan for extending the Ido-Esperanto dictionary using cross-lingual word embedding alignment (bilingual lexicon induction).

## Approach

**Method**: Cross-Lingual Word Embedding Alignment with Supervised Seed Dictionary

**Core Idea**: 
1. Train monolingual word embeddings for Ido and Esperanto independently
2. Use existing dictionary as seed translations to learn alignment mapping
3. Apply mapping to find new translation candidates based on vector similarity

**References**:
- Mikolov et al. (2013): "Exploiting Similarities among Languages for Machine Translation"
- Smith et al. (2017): "Offline bilingual word vectors, orthogonal transformations and the inverted softmax"

## Pipeline Steps

### Step 1: Prepare Corpora
**Input**: 
- Raw Ido corpus (300K phrases) - READY
- Raw Esperanto corpus (need to obtain)

**Output**: 
- `data/processed/ido_clean.txt`
- `data/processed/epo_clean.txt`

**Tasks**:
- Tokenization
- Lowercasing (optional, preserve for morphology)
- Remove noise and duplicates
- Sentence segmentation

**Time**: 5-10 minutes

### Step 2: Train Ido Embeddings
**Input**: `data/processed/ido_clean.txt`

**Output**: `models/ido_fasttext.model`

**Method**: FastText (handles morphology via character n-grams)

**Parameters**:
```python
vector_size = 300      # Embedding dimension
window = 5             # Context window
min_count = 5          # Minimum word frequency
epochs = 10            # Training iterations
sg = 1                 # Skip-gram (better for small corpora)
min_n = 3              # Min character n-gram
max_n = 6              # Max character n-gram
```

**Time**: 10-20 minutes (CPU), 3-5 minutes (GPU)

### Step 3: Train Esperanto Embeddings
**Input**: `data/processed/epo_clean.txt`

**Output**: `models/epo_fasttext.model`

**Method**: FastText with same parameters as Ido

**Time**: 15-30 minutes (CPU), 5-10 minutes (GPU)

### Step 4: Extract Seed Dictionary
**Input**: `terraform/extractor-results/20251025-222952/vortaro_dictionary.json`

**Output**: `data/seed_dictionary.txt`

**Tasks**:
- Load dictionary JSON
- Extract word pairs (lemma forms)
- Filter pairs where both words exist in embedding vocabularies
- Remove low-frequency pairs
- Format: one pair per line "ido_word esperanto_word"

**Quality Filters**:
- Both words must be in vocabulary
- Minimum frequency threshold (e.g., 5 occurrences)
- Remove multi-word expressions (optional)
- Prefer 1:1 mappings

**Expected Size**: 5K-50K pairs (depends on dictionary and corpus overlap)

**Time**: 1-2 minutes

### Step 5: Learn Alignment Mapping
**Input**: 
- `models/ido_fasttext.model`
- `models/epo_fasttext.model`
- `data/seed_dictionary.txt`

**Output**: `models/alignment_matrix.npy`

**Method**: Orthogonal Procrustes Alignment

**Algorithm**:
```
Given seed dictionary pairs (x_i, y_i):
- X = matrix of Ido embeddings for source words
- Y = matrix of Esperanto embeddings for target words
- Find orthogonal matrix W that minimizes: ||W * X - Y||^2
- Solution via SVD: W = U * V^T where Y^T * X = U * Σ * V^T
```

**Alternative Methods** (if Procrustes insufficient):
- RCSLS (Relaxed Cross-domain Similarity Local Scaling)
- VecMap (self-learning framework)

**Time**: 2-5 minutes

### Step 6: Find Translation Candidates
**Input**:
- `models/ido_fasttext.model`
- `models/epo_fasttext.model`
- `models/alignment_matrix.npy`
- `data/seed_dictionary.txt` (to exclude known pairs)

**Output**: `results/candidate_translations.json`

**Algorithm**:
```
For each Ido word not in seed dictionary:
  1. Get Ido embedding vector: v_ido
  2. Apply alignment: v_aligned = W * v_ido
  3. Find k-nearest neighbors in Esperanto space (k=10)
  4. Compute cosine similarity for each neighbor
  5. Store candidates with similarity scores
```

**Format**:
```json
{
  "ido_word": [
    {"translation": "epo_word1", "similarity": 0.85},
    {"translation": "epo_word2", "similarity": 0.78},
    ...
  ]
}
```

**Time**: 5-15 minutes (depends on vocabulary size)

### Step 7: Validate and Filter Candidates
**Input**: `results/candidate_translations.json`

**Output**: `results/high_confidence_translations.json`

**Filters**:

1. **Similarity Threshold**: Keep only pairs with cosine similarity > 0.5

2. **Mutual Nearest Neighbors**: 
   - Check if Esperanto word also maps back to Ido word
   - Bidirectional verification increases precision

3. **Frequency Consistency**:
   - Compare word frequencies in both corpora
   - Rare words shouldn't map to very common words

4. **POS Tag Consistency** (if available):
   - Nouns should map to nouns, verbs to verbs, etc.

5. **Edit Distance Check**:
   - Ido and Esperanto are similar languages
   - Very different strings might be errors

**Confidence Levels**:
- **High**: similarity > 0.7, mutual NN, frequency match
- **Medium**: similarity > 0.6, passes 2+ filters
- **Low**: similarity > 0.5, passes 1+ filter

**Time**: 2-5 minutes

## Expected Results

### Quality Metrics

**Precision@1**: 30-50%
- Top candidate is correct translation

**Precision@5**: 50-70%
- Correct translation appears in top 5 candidates

**Precision@10**: 60-80%
- Correct translation appears in top 10 candidates

**Coverage**: 80-90%
- Percentage of vocabulary for which we can propose translations

### Output Size Estimates

Assuming:
- Ido vocabulary: 20K-50K words
- Seed dictionary: 10K-30K pairs
- New candidates: 10K-30K words

Expected new translations:
- High confidence: 2K-5K pairs
- Medium confidence: 5K-10K pairs
- Low confidence: 3K-15K pairs

## Time Estimates

| Step | Task | CPU Time | GPU Time |
|------|------|----------|----------|
| 1 | Prepare corpora | 5-10 min | 5-10 min |
| 2 | Train Ido embeddings | 10-20 min | 3-5 min |
| 3 | Train Epo embeddings | 15-30 min | 5-10 min |
| 4 | Extract seed dictionary | 1-2 min | 1-2 min |
| 5 | Learn alignment | 2-5 min | 1-2 min |
| 6 | Find candidates | 5-15 min | 2-5 min |
| 7 | Validate candidates | 2-5 min | 2-5 min |
| **Total** | **40-87 min** | **19-39 min** |

## Project Structure

```
projects/embedding-aligner/
├── ALIGNMENT_PLAN.md              # This document
├── README.md                      # Project overview
├── SETUP.md                       # Installation instructions
│
├── scripts/
│   ├── 01_prepare_corpora.py      # Clean and tokenize
│   ├── 02_train_ido_embeddings.py # FastText for Ido
│   ├── 03_train_epo_embeddings.py # FastText for Esperanto
│   ├── 04_extract_seed_dict.py    # From vortaro_dictionary.json
│   ├── 05_align_embeddings.py     # Learn mapping matrix
│   ├── 06_find_candidates.py      # Nearest neighbor search
│   └── 07_validate_candidates.py  # Filter and rank
│
├── data/
│   ├── raw/
│   │   ├── ido_corpus.txt         # 300K phrases (READY)
│   │   └── epo_corpus.txt         # Need to obtain
│   ├── processed/
│   │   ├── ido_clean.txt          # Cleaned Ido
│   │   └── epo_clean.txt          # Cleaned Esperanto
│   └── seed_dictionary.txt        # Extracted pairs
│
├── models/
│   ├── ido_fasttext.model         # Ido embeddings
│   ├── epo_fasttext.model         # Esperanto embeddings
│   └── alignment_matrix.npy       # Learned mapping
│
└── results/
    ├── candidate_translations.json      # All candidates
    ├── high_confidence_translations.json # Filtered results
    └── evaluation_metrics.json          # Quality metrics
```

## Dependencies

```
gensim>=4.0.0          # FastText implementation
numpy>=1.20.0          # Matrix operations
scipy>=1.7.0           # SVD for Procrustes
scikit-learn>=1.0.0    # Cosine similarity
```

## Key Considerations

### Corpus Quality
- **Size matters**: Larger corpora produce better embeddings
- **Domain coverage**: Diverse text improves generalization
- **Cleaning**: Remove noise, duplicates, non-linguistic content

### Seed Dictionary Quality
- **Size**: Minimum 5K pairs recommended, 10K+ ideal
- **Coverage**: Should cover common vocabulary
- **Accuracy**: Errors in seed dictionary propagate to alignment

### Embedding Parameters
- **Dimension**: 300 is standard, 100 works for smaller corpora
- **Window size**: 5 is typical, larger for topic modeling
- **Min count**: Balance between vocabulary size and quality

### Alignment Method
- **Procrustes**: Simple, fast, works well with good seed dictionary
- **RCSLS**: Better handles hubness problem (some words are NN of many)
- **VecMap**: Self-learning, can improve with unlabeled data

### Validation Strategy
- **Manual review**: Sample high-confidence candidates
- **Cross-validation**: Hold out part of seed dictionary for testing
- **Linguistic checks**: Verify morphological consistency

## Next Steps

1. **Obtain Esperanto corpus**
   - Wikipedia dump
   - Tatoeba sentences
   - Literature/news corpora
   - Target: 300K+ phrases (similar to Ido)

2. **Implement pipeline scripts**
   - Start with steps 1-4 (can run without Esperanto initially)
   - Test on small sample first

3. **Evaluate results**
   - Manual review of top candidates
   - Compare with existing dictionaries
   - Measure precision/recall

4. **Iterate and improve**
   - Tune parameters based on results
   - Try different alignment methods
   - Expand seed dictionary

5. **Integration**
   - Add high-confidence translations to main dictionary
   - Document linguistic patterns discovered
   - Update Apertium translation rules

## Success Criteria

**Minimum Viable**:
- Pipeline runs end-to-end
- Produces 1K+ high-confidence candidates
- Precision@5 > 40%

**Target**:
- 5K+ high-confidence candidates
- Precision@5 > 60%
- Manual review confirms quality

**Stretch**:
- 10K+ candidates
- Precision@5 > 70%
- Discover systematic translation patterns
