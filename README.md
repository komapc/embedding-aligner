# Ido-Esperanto Embedding Aligner

Cross-lingual word embedding alignment for discovering translation candidates between Ido and Esperanto.

## Project Status

✅ **Phase 1 Complete**: Ido corpus prepared and embeddings trained
✅ **Phase 2 Complete**: Experimental models trained and evaluated
⏳ **Phase 3 Pending**: Corpus expansion (need more Ido text)
⏳ **Phase 4 Pending**: Cross-lingual alignment with Esperanto

## Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt
```

### Test Embeddings
```bash
# Query similar words using best model
python3 scripts/query_similar_words.py hundo --model models/ido_exp_combined-best.model

# Compare all experimental models
python3 scripts/compare_experiments.py hundo
```

## Current Best Model

**Model**: `ido_exp_combined-best.model`
- **Vocabulary**: 18,178 words
- **Algorithm**: Word2Vec Skip-gram
- **Settings**: min_count=15, window=5, sample=1e-5, filters proper nouns
- **Quality**: Best semantic similarity, reduced proper noun pollution

**Example Results**:
- `hundo` (dog) → kato (cat), volfo (wolf), foxo (fox), porko (pig)
- `linguo` (language) → lingui (languages), parolata (spoken), ortografio (orthography)

## Project Structure

```
embedding-aligner/
├── data/
│   ├── raw/              # Raw Wikipedia XML dumps
│   ├── processed/        # Cleaned corpus files
│   └── dictionaries/     # Seed dictionaries
├── models/               # Trained embedding models
├── scripts/              # Training and evaluation scripts
├── results/              # Alignment results
└── docs/                 # Documentation
```

## Key Scripts

### Training
- `train_experiments.py` - Train experimental models with different configurations
- `train_optimized.py` - Train with optimized parameters
- `train_all_experiments.sh` - Train all experiments at once

### Evaluation
- `query_similar_words.py` - Query similar words from a model
- `compare_experiments.py` - Compare all experimental models
- `compare_metrics.py` - Compare different similarity metrics
- `check_training_status.sh` - Monitor training progress

### Corpus Preparation
- `parse_wikipedia_xml.py` - Parse Wikipedia XML dumps
- `01_prepare_corpora.py` - Prepare corpus for training

## Experimental Models

We trained 6 experimental models to optimize embedding quality:

1. **baseline** - Original model (min_count=5, window=10)
2. **higher-mincount** - Remove rare words (min_count=20)
3. **subsampling** - Balance frequent words (sample=1e-5)
4. **smaller-window** - Focused context (window=5)
5. **cbow** - CBOW algorithm instead of Skip-gram
6. **no-proper-nouns** - Filter capitalized words
7. **combined-best** - Best settings combined ⭐

**Winner**: `combined-best` provides the best semantic quality.

## Current Corpus

- **Source**: Ido Wikipedia
- **Size**: 6M words, 361K sentences
- **Vocabulary**: 46K unique words (baseline), 18K (combined-best)

## Next Steps

### Corpus Expansion Needed

Current corpus is Wikipedia-heavy (encyclopedic language, proper nouns). Need more diverse Ido text:

**Priority Sources**:
1. Ido Wikisource (literature, documents)
2. Ido Wiktionary (definitions, examples)
3. Ido forums/mailing lists (natural language)
4. Ido translations (parallel texts)

**Target**: 10M+ words for production-quality embeddings

See `IMPROVEMENT_STRATEGIES.md` for detailed expansion plan.

### Future Work

1. Expand Ido corpus to 10M+ words
2. Prepare Esperanto corpus
3. Train Esperanto embeddings
4. Implement cross-lingual alignment
5. Extract translation candidates
6. Validate and integrate into Apertium

## Documentation

- `IMPROVEMENT_STRATEGIES.md` - Detailed improvement strategies
- `EXPERIMENT_SUMMARY.md` - Experimental results summary
- `CORPUS_EXPANSION_OPTIONS.md` - Corpus expansion options
- `INSTALL_DEPENDENCIES.md` - Installation guide

## Model Training Details

All models are trained **from scratch** (not fine-tuned) using:
- **Algorithm**: Word2Vec (Gensim implementation)
- **Vector size**: 300 dimensions
- **Training**: 30 epochs
- **Corpus**: Ido Wikipedia (6M words)

See inline documentation for parameter details.

## License

Part of the Apertium machine translation platform.

## Contact

For questions about this project, refer to the Apertium Ido-Esperanto language pair documentation.
