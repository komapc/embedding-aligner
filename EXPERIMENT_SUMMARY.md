# Experiment Summary

## Status: 6 Models Training in Parallel

All experiments are currently training. Expected completion: 30-40 minutes per model.

## What's Running

| Experiment | Key Change | Expected Impact | Vocab Size |
|------------|------------|-----------------|------------|
| **higher-mincount** | min_count=20 | Remove rare words/proper nouns | ~14,500 |
| **subsampling** | sample=1e-5 | Balance frequent words | ~46,000 |
| **smaller-window** | window=5 | Focused context | ~46,000 |
| **cbow** | CBOW (sg=0) | Better for small corpus | ~46,000 |
| **no-proper-nouns** | Filter capitals | Remove tennis players/mythology | ~35,000 |
| **combined-best** | All best settings | Best overall quality | ~20,000 |

## How to Monitor Progress

```bash
# Check which models are complete
./scripts/check_training_status.sh

# View training logs (example for higher-mincount)
tail -f logs/higher-mincount.log  # if logging to file
```

## How to Compare Results

Once training completes, use the comparison script:

```bash
# Compare all models for a specific word
python3 scripts/compare_experiments.py hundo

# Compare with more results
python3 scripts/compare_experiments.py hundo 20

# Test multiple words
python3 scripts/compare_experiments.py kato
python3 scripts/compare_experiments.py linguo
python3 scripts/compare_experiments.py programo
python3 scripts/compare_experiments.py matematiko
```

## What to Look For

### Good Results ✅
- **hundo** → kato, cervo, foxo, animalo (animals)
- **kato** → hundo, felino, animalo (animals)
- **linguo** → dialekto, gramatiko, idiomo (language terms)
- **programo** → softwaro, aplikilo, komputero (computing)

### Bad Results ❌
- Tennis players: krejčíková, vesnina, barbora
- Mythology: ortros, kerberos, hesperi
- Random proper nouns: takaaki, viktorija
- Unrelated words: duopla (doubles), surtabla (table)

## Expected Winners

Based on the strategies:

1. **combined-best** - Should be the best overall
   - Filters proper nouns
   - Balances frequent words
   - Focused context
   - Removes rare noise

2. **no-proper-nouns** - Should remove tennis players
   - Cleaner semantic space
   - No mythology names

3. **higher-mincount** - Should be cleaner but smaller vocab
   - Only frequent words
   - Better statistics

## Next Steps

### Phase 1: Evaluate Experiments (Today)
1. ✅ Training started (6 models in parallel)
2. ⏳ Wait for completion (~30-40 min)
3. ⏳ Compare results
4. ⏳ Choose best model

### Phase 2: Corpus Expansion (Your Task)
While experiments run, search for:
1. **Ido Wikisource** - literature, documents
2. **Ido Wiktionary** - definitions, examples
3. **Ido forums** - natural language
4. **Ido translations** - parallel texts

Target: 10M+ words for high-quality embeddings

### Phase 3: Retrain with Expanded Corpus
1. Combine all Ido text sources
2. Use best experiment settings
3. Train final production model

## Files Created

- `scripts/train_experiments.py` - Train individual experiments
- `scripts/compare_experiments.py` - Compare all models
- `scripts/train_all_experiments.sh` - Train all at once
- `scripts/check_training_status.sh` - Monitor progress
- `IMPROVEMENT_STRATEGIES.md` - Detailed improvement guide
- `EXPERIMENTS_RUNNING.md` - Experiment details

## Estimated Timeline

- **Now**: Training started
- **+30-40 min**: First models complete
- **+1-2 hours**: All models complete
- **+2-3 hours**: Evaluation and comparison done
- **Meanwhile**: You search for more corpus sources
- **Tomorrow**: Retrain with expanded corpus

---

**Current Status**: 🔄 All 6 experiments training in parallel
**Next Action**: Wait for completion, then compare results
