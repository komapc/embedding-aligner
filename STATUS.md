# Project Status - Ido-Esperanto Embedding Aligner

**Last Updated**: 2025-11-04

## Current Phase: Corpus Expansion Needed

### ✅ Completed

1. **Corpus Preparation**
   - ✅ Downloaded Ido Wikipedia XML dump
   - ✅ Parsed and cleaned corpus
   - ✅ 6M words, 361K sentences ready

2. **Baseline Training**
   - ✅ Trained initial Word2Vec model
   - ✅ Fixed tokenization (removed punctuation artifacts)
   - ✅ Vocabulary: 46,410 words

3. **Experimental Optimization**
   - ✅ Trained 6 experimental models
   - ✅ Compared different configurations
   - ✅ Identified best model: `combined-best`

4. **Quality Improvements**
   - ✅ Reduced proper noun pollution
   - ✅ Better semantic clustering
   - ✅ Cleaner vocabulary (18K words)

### 🔄 In Progress

- **Corpus Expansion**: Searching for additional Ido text sources
  - Target: 10M+ words (currently 6M)
  - Sources needed: Wikisource, Wiktionary, forums, translations

### ⏳ Pending

1. **Esperanto Corpus Preparation**
   - Download Esperanto Wikipedia
   - Parse and clean
   - Train Esperanto embeddings

2. **Cross-lingual Alignment**
   - Extract seed dictionary
   - Align Ido and Esperanto embedding spaces
   - Find translation candidates

3. **Validation & Integration**
   - Validate translation candidates
   - Export to Apertium format
   - Integrate into Ido-Esperanto language pair

## Current Best Model

**File**: `models/ido_exp_combined-best.model`

**Specifications**:
- Algorithm: Word2Vec Skip-gram
- Vocabulary: 18,178 words
- Vector size: 300 dimensions
- Training: 30 epochs on 6M words

**Configuration**:
- min_count: 15 (removes rare words)
- window: 5 (focused context)
- sample: 1e-5 (balances frequent words)
- Filters proper nouns (capitalized words)
- negative: 10 (more negative samples)

**Quality**:
- ✅ Good semantic clustering (hundo → kato, volfo, foxo)
- ✅ Reduced proper noun pollution
- ⚠️ Still some noise due to small corpus size

## Known Issues

1. **Proper Noun Pollution**: Some mythology names and tennis players still appear
   - **Cause**: Wikipedia-heavy corpus
   - **Solution**: Need more diverse Ido text

2. **Small Corpus**: 6M words is below optimal for Word2Vec
   - **Optimal**: 10M+ words
   - **Solution**: Corpus expansion

3. **Domain Bias**: Encyclopedia language dominates
   - **Solution**: Add forums, literature, translations

## Metrics

### Corpus Statistics
- **Total words**: 6,029,961
- **Sentences**: 361,272
- **Unique words**: 254,182 (before filtering)
- **Vocabulary (baseline)**: 46,410 words (min_count=5)
- **Vocabulary (best)**: 18,178 words (min_count=15)

### Model Comparison

| Model | Vocab Size | Quality | Notes |
|-------|-----------|---------|-------|
| baseline | 46,410 | ⭐⭐ | Mythology, tennis players |
| higher-mincount | 14,496 | ⭐⭐⭐ | Clean but small |
| subsampling | 47,117 | ⭐⭐ | Still has proper nouns |
| smaller-window | 47,117 | ⭐⭐ | Still has mythology |
| cbow | 47,117 | ⭐ | Poor results |
| no-proper-nouns | 47,117 | ⭐⭐⭐ | Better but incomplete |
| **combined-best** | **18,178** | **⭐⭐⭐⭐** | **Best overall** |

## Next Actions

### Immediate (Your Task)
1. Search for Ido corpus sources:
   - Ido Wikisource
   - Ido Wiktionary
   - Ido forums/mailing lists
   - Ido translations

### After Corpus Expansion
1. Retrain with combined-best settings on expanded corpus
2. Prepare Esperanto corpus
3. Train Esperanto embeddings
4. Implement cross-lingual alignment

### Long-term
1. Validate translation candidates
2. Export to Apertium format
3. Integrate into language pair
4. Publish results

## Resources

- **Corpus**: `data/processed/ido_corpus.txt`
- **Best Model**: `models/ido_exp_combined-best.model`
- **Scripts**: `scripts/` directory
- **Documentation**: `IMPROVEMENT_STRATEGIES.md`, `EXPERIMENT_SUMMARY.md`

## Timeline

- **2025-11-04**: Experimental models completed
- **Next**: Corpus expansion (waiting for sources)
- **Future**: Cross-lingual alignment and validation

---

**Status**: Waiting for corpus expansion before proceeding to next phase.
