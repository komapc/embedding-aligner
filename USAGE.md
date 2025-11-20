# Quick Usage Guide - BERT Translation Discovery

**Date:** November 21, 2025  
**Status:** Production Ready ✅

---

## 🎯 What You Have

**Result:** 4,787 high-quality Ido-Esperanto translation pairs  
**Quality:** Both Ido and Esperanto embeddings cleaned (no punctuation)  
**Threshold:** 0.60 (excellent quality)  
**File:** `results/bert_aligned_clean_0.60/bert_candidates.json`

---

## 🚀 Quick Test

### Option 1: Use Test Script (Easiest)

```bash
./test_translations.sh
```

Tests default words: hundo, krear, obediar, refuzar, euro, britaniana, generala, saluto

**Custom words:**
```bash
./test_translations.sh vorti manjar bela urbo
```

### Option 2: Direct Command

```bash
source sourceme.sh

python scripts/find_nearest_words.py \
    --ido-embeddings results/bert_aligned_clean_0.60/ido_bert_aligned.npy \
    --ido-vocab models/ido_bert_vocab_clean.txt \
    --epo-embeddings results/bert_aligned_clean_0.60/epo_w2v_aligned.npy \
    --epo-vocab models/esperanto_clean__vocab.txt \
    --words hundo krear obediar
```

### Option 3: Check Discovered Pairs File

```bash
# See all translations for a word
cat results/bert_aligned_clean_0.60/bert_candidates.json | jq '.hundo'

# Count total pairs
cat results/bert_aligned_clean_0.60/bert_candidates.json | jq 'to_entries | length'

# Get statistics
cat results/bert_aligned_clean_0.60/bert_alignment_stats.json
```

---

## 📊 Expected Results

### Good Matches (Similarity ≥ 0.60):

```bash
hundo → hundo (1.000)          ✅ Perfect
krear → krei (1.000)           ✅ Perfect
obediar → obei (1.000)         ✅ Perfect
refuzar → rifuzi (1.000)       ✅ Perfect
euro → eŭro (1.000)            ✅ Perfect
saluto → saluto (1.000)        ✅ Perfect
```

### Poor Matches (Below 0.60):

```bash
vorti → ceremoniaj (0.216)     ❌ Not in discovered pairs
hundi → praepoka (0.220)       ❌ Not in discovered pairs
```

These are correctly **filtered out** from the 4,787 pairs.

---

## ✅ What's Clean

**NO punctuation in results:**
- ❌ No `romano"` or `vesperon"`
- ❌ No `:enira` or `salutado)`
- ❌ No `volkmann,` or `volgogrado)`
- ✅ Only clean alphabetic words

**Files:**
```
results/bert_aligned_clean_0.60/
├── bert_candidates.json          ← THE RESULT (4,787 pairs)
├── bert_alignment_stats.json     ← Statistics
├── ido_bert_aligned.npy          ← 58 MB
└── epo_w2v_aligned.npy           ← 492 MB
```

---

## 🔧 Troubleshooting

### Issue: "File not found"
```bash
# Check you're in the right directory
cd /home/mark/apertium-dev/projects/embedding-aligner

# Activate venv
source sourceme.sh
```

### Issue: "Word not found in vocabulary"
```bash
# Check if word exists in Ido vocab
grep -i "yourword" models/ido_bert_vocab_clean.txt

# If not found, it's not in the corpus
```

### Issue: "Low similarities"
This is expected! Not every word has a good translation match.
Only words with similarity ≥ 0.60 are in the discovered pairs.

---

## 📁 File Locations

### Input Files:
- Ido embeddings (clean): `models/ido_bert_clean_300d.npy`
- Ido vocabulary: `models/ido_bert_vocab_clean.txt`
- Esperanto embeddings (clean): `models/esperanto_clean__300d.npy`
- Esperanto vocabulary: `models/esperanto_clean__vocab.txt`
- Seed dictionary: `data/seed_dictionary.txt`

### Output Files:
- **Discovered pairs:** `results/bert_aligned_clean_0.60/bert_candidates.json` ⭐
- Statistics: `results/bert_aligned_clean_0.60/bert_alignment_stats.json`
- Aligned embeddings: `results/bert_aligned_clean_0.60/*.npy`

---

## 📈 Statistics

```bash
cat results/bert_aligned_clean_0.60/bert_alignment_stats.json
```

Shows:
- Total Ido words: 2,608
- Total pairs: 4,787
- Threshold used: 0.60
- Seed pairs: 2,610
- Final similarity: 0.9999

---

## 🎯 Next Steps

1. **Manual validation:** Review top 500 pairs
2. **Format as .dix:** Convert to Apertium dictionary format
3. **Deploy:** Integrate into apertium-ido-epo
4. **Test:** Verify translations work

See `SESSION_HANDOFF.md` for detailed deployment guide.

---

**Questions?** Run `./test_translations.sh` to see it working!

