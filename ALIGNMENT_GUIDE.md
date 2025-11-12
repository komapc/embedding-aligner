# Cross-Lingual Alignment Guide - Ido ↔ Esperanto

**Date**: 2025-11-05  
**Method**: Procrustes Alignment (Orthogonal Transformation)  
**Goal**: Align Ido and Esperanto embedding spaces for translation discovery

---

## 🎯 Why Alignment is Needed

### The Problem

Even though we train Ido and Esperanto embeddings with **identical parameters**:
- **Vector size**: 300 dimensions
- **Algorithm**: Word2Vec Skip-gram
- **Window**: 5, **Min count**: 15, **Negative**: 10, etc.

**The embedding spaces are still incompatible!**

Why? Because:
1. Each model is trained independently
2. Random initialization creates different coordinate systems
3. `hundo` (Ido) and `hundo` (Esperanto) will be in different positions
4. Even though semantically equivalent words have similar contexts, they're in different spaces

### The Solution: Procrustes Alignment

**Procrustes alignment** finds an orthogonal transformation (rotation + reflection) that maps one embedding space to another while preserving distances.

**Key insight**: If we know some translation pairs (seed dictionary), we can learn how to rotate the Ido space to match the Esperanto space!

---

## 📊 Exact Parameter Matching (Critical!)

### Ido Model: `ido_exp_combined-best.model`

```python
{
    'vector_size': 300,        # ✅ MUST MATCH
    'window': 5,               # ✅ MUST MATCH
    'min_count': 15,           # ✅ MUST MATCH
    'workers': 4,
    'sg': 1,                   # ✅ Skip-gram (MUST MATCH)
    'negative': 10,            # ✅ MUST MATCH
    'epochs': 30,              # ✅ MUST MATCH
    'alpha': 0.05,
    'min_alpha': 0.0001,
    'sample': 1e-5,            # ✅ MUST MATCH
    'filter_proper': True,     # ✅ MUST MATCH
}
```

### Esperanto Model: `esperanto_exp_combined-best.model`

```python
{
    'vector_size': 300,        # ✅ MATCHES
    'window': 5,               # ✅ MATCHES
    'min_count': 15,           # ✅ MATCHES
    'workers': 4,
    'sg': 1,                   # ✅ MATCHES (Skip-gram)
    'negative': 10,            # ✅ MATCHES
    'epochs': 30,              # ✅ MATCHES
    'alpha': 0.05,
    'min_alpha': 0.0001,
    'sample': 1e-5,            # ✅ MATCHES
    'filter_proper': True,     # ✅ MATCHES
}
```

**Status**: ✅ **PERFECTLY MATCHED** - ready for alignment!

---

## 🔬 How Procrustes Alignment Works

### Step 1: Get Seed Dictionary

We need known translation pairs to learn the transformation.

**Source**: Existing Apertium `apertium-ido-epo` dictionary

Example seed pairs:
```
hundo (Ido) → hundo (Esperanto)
kato (Ido) → kato (Esperanto)
domo (Ido) → domo (Esperanto)
manĝar (Ido) → manĝi (Esperanto)
...
```

**Need**: ~1,000-5,000 high-quality translation pairs

### Step 2: Extract Vectors

For each pair `(ido_word, epo_word)`:
1. Get Ido embedding: `X_ido[i]` (300-dim vector)
2. Get Esperanto embedding: `Y_epo[i]` (300-dim vector)
3. Build matrices: `X` (Ido) and `Y` (Esperanto)

```
X = [x₁, x₂, ..., xₙ]ᵀ   # n × 300 matrix (Ido vectors)
Y = [y₁, y₂, ..., yₙ]ᵀ   # n × 300 matrix (Esperanto vectors)
```

### Step 3: Solve Procrustes Problem

Find orthogonal matrix `W` that minimizes:

```
min ||X·W - Y||²
```

**Solution** (using SVD):
```python
U, Σ, Vᵀ = SVD(Yᵀ · X)
W = U · Vᵀ
```

Properties of `W`:
- Orthogonal: `WᵀW = I` (preserves distances and angles)
- Rotates Ido space to align with Esperanto space
- Dimensions: 300 × 300

### Step 4: Transform Ido Embeddings

Apply transformation to ALL Ido words:

```python
X_aligned = X · W
```

Now `X_aligned` is in the same space as `Y` (Esperanto)!

### Step 5: Find Translation Candidates

For any Ido word `w_ido`:
1. Get aligned vector: `v_aligned = embedding_ido[w_ido] · W`
2. Find nearest Esperanto words: `nn = nearest_neighbors(v_aligned, embeddings_epo)`
3. Top candidates are likely translations!

Example:
```python
# Translate "kato" (Ido) to Esperanto
v_ido = ido_model['kato']
v_aligned = v_ido @ W
candidates = epo_model.most_similar([v_aligned], topn=10)

# Expected output:
# [('kato', 0.95),      # Perfect match!
#  ('katino', 0.82),    # Female cat
#  ('katido', 0.79),    # Kitten
#  ('felino', 0.76),    # Feline
#  ...]
```

---

## 🛠️ Implementation Plan

### Phase 1: Prepare Seed Dictionary

**Script**: `scripts/01_extract_seed_dict.py` (already exists)

```bash
cd /home/mark/apertium-dev/projects/embedding-aligner
source venv/bin/activate

python3 scripts/04_extract_seed_dict.py \
    --bidix /path/to/apertium-ido-epo.ido-epo.dix \
    --output data/dictionaries/seed_ido_epo.txt \
    --min-pairs 1000 \
    --max-pairs 5000
```

**Output**: Tab-separated file
```
hundo	hundo
kato	kato
domo	domo
manĝar	manĝi
...
```

### Phase 2: Align Embeddings

**Script**: `scripts/05_align_embeddings.py` (already exists)

```bash
python3 scripts/05_align_embeddings.py \
    --source-model models/ido_exp_combined-best.model \
    --target-model models/esperanto_exp_combined-best.model \
    --seed-dict data/dictionaries/seed_ido_epo.txt \
    --output-matrix data/alignment/W_ido_to_epo.npy \
    --validate
```

**What it does**:
1. Loads both models
2. Loads seed dictionary
3. Extracts paired vectors
4. Computes Procrustes transformation matrix `W`
5. Validates alignment quality
6. Saves `W` for future use

**Output**:
- `W_ido_to_epo.npy` - 300×300 transformation matrix
- Alignment quality metrics (accuracy, precision@k)

### Phase 3: Find Translation Candidates

**Script**: `scripts/06_find_candidates.py` (already exists)

```bash
python3 scripts/06_find_candidates.py \
    --source-model models/ido_exp_combined-best.model \
    --target-model models/esperanto_exp_combined-best.model \
    --alignment-matrix data/alignment/W_ido_to_epo.npy \
    --output data/candidates/ido_epo_candidates.json \
    --top-k 10 \
    --min-score 0.5
```

**What it does**:
1. For each Ido word in vocabulary
2. Transform to Esperanto space: `v_aligned = v_ido @ W`
3. Find k-nearest Esperanto neighbors
4. Score by cosine similarity
5. Filter by threshold

**Output**: JSON with candidates
```json
{
  "hundo": [
    {"word": "hundo", "score": 0.95},
    {"word": "kato", "score": 0.72},
    {"word": "besto", "score": 0.68}
  ],
  "kato": [
    {"word": "kato", "score": 0.94},
    {"word": "katino", "score": 0.81}
  ],
  ...
}
```

### Phase 4: Validate Candidates

**Script**: `scripts/07_validate_candidates.py` (already exists)

```bash
python3 scripts/07_validate_candidates.py \
    --candidates data/candidates/ido_epo_candidates.json \
    --seed-dict data/dictionaries/seed_ido_epo.txt \
    --output data/validated/ido_epo_validated.json \
    --threshold 0.7
```

**What it does**:
1. Compare candidates against seed dictionary
2. Calculate precision, recall, F1
3. Identify high-confidence new translations
4. Flag suspicious/conflicting translations

### Phase 5: Export to Apertium

**Script**: `scripts/08_export_to_apertium.py` (create this)

```bash
python3 scripts/08_export_to_apertium.py \
    --candidates data/validated/ido_epo_validated.json \
    --output data/export/new_entries.dix \
    --format apertium \
    --min-score 0.8
```

**Output**: Apertium `.dix` format
```xml
<e><p><l>novo_vorto</l><r>nova_vorto</r></p></e>
...
```

---

## 📊 Expected Results

### Alignment Quality

**Metrics** (on seed dictionary):
- **Precision@1**: 70-80% (top-1 candidate is correct)
- **Precision@5**: 85-95% (correct translation in top-5)
- **Precision@10**: 90-98% (correct translation in top-10)

**Why not 100%?**
- Polysemy (words with multiple meanings)
- Corpus differences (Ido vs Esperanto usage patterns)
- Rare words (low-quality embeddings)
- One-to-many mappings (Ido `manĝar` → Epo `manĝi`, `nutri`, `vori`)

### New Translation Candidates

**Expected discovery**:
- **High confidence** (score > 0.8): 1,000-3,000 new pairs
- **Medium confidence** (score 0.6-0.8): 5,000-10,000 pairs
- **Low confidence** (score 0.4-0.6): 10,000-20,000 pairs (review needed)

**Categories**:
- Exact cognates: `hundo → hundo`, `kato → kato`
- Systematic derivations: `manĝar → manĝi` (Ido -ar → Epo -i)
- Semantic neighbors: `domo → loĝejo` (house → dwelling)
- Compound words: `sunfloro → sunfloro` (sunflower)

---

## 🎯 Alignment Quality Factors

### What Helps Alignment

✅ **Identical training parameters** (✓ we have this!)
✅ **Large seed dictionary** (need 1,000-5,000 pairs)
✅ **High-quality embeddings** (large corpora help)
✅ **Related languages** (✓ Ido and Esperanto are very similar!)
✅ **Systematic vocabulary** (✓ both are constructed languages with regular patterns)

### What Can Hurt Alignment

⚠️ **Different corpus domains** (Wikipedia may differ between languages)
⚠️ **Spelling variations** (Ido `ch` vs Esperanto `ĉ`)
⚠️ **Grammatical differences** (Ido `manĝar` vs Epo `manĝi`)
⚠️ **Rare words** (poor embeddings due to low frequency)
⚠️ **Polysemy** (words with multiple meanings)

---

## 🚀 Execution Timeline

After Esperanto embeddings are trained:

| Phase | Time | Action |
|-------|------|--------|
| **1. Extract seed dict** | 5 min | Run on existing Apertium dictionary |
| **2. Align embeddings** | 10 min | Compute Procrustes transformation |
| **3. Find candidates** | 30 min | Find nearest neighbors for all words |
| **4. Validate** | 10 min | Check against seed dictionary |
| **5. Manual review** | 2-4 hours | Review high-confidence candidates |
| **6. Export** | 5 min | Generate Apertium `.dix` entries |
| **TOTAL** | **3-5 hours** | (mostly manual review) |

---

## 📋 Prerequisites for Alignment

Before running alignment:

- [ ] ✅ Ido embeddings trained (`ido_exp_combined-best.model`)
- [ ] ⏳ Esperanto embeddings trained (`esperanto_exp_combined-best.model`)
- [ ] ✅ Both models use **identical parameters**
- [ ] ✅ Seed dictionary extracted from Apertium
- [ ] ✅ Alignment scripts available
- [ ] ✅ Validation framework ready

---

## 🔬 Advanced: Why Procrustes Works

**Mathematical intuition**:

1. **Word2Vec learns semantic spaces**: Similar words are close together
2. **Languages share semantic structure**: "dog" and "hundo" have similar contexts
3. **Spaces are isomorphic**: Same structure, different coordinates
4. **Orthogonal transformation**: Rotates one space to match the other

**Analogy**: 
- Imagine two maps of the same city, but rotated differently
- If you know a few landmarks on both maps, you can figure out the rotation
- Once aligned, all other locations match up!

**Why orthogonal?**
- Preserves distances (semantic similarity)
- Preserves angles (semantic relationships)
- No stretching or skewing (maintains structure)

---

## 📖 References

**Papers**:
- Mikolov et al. (2013): "Exploiting Similarities among Languages for Machine Translation"
- Smith et al. (2017): "Offline Bilingual Word Vectors, Orthogonal Transformations and the Inverted Softmax"
- Conneau et al. (2018): "Word Translation Without Parallel Data" (MUSE)

**Code**:
- Our implementation: `scripts/05_align_embeddings.py` (based on Procrustes)
- Gensim: No built-in, we implement from scratch
- Facebook MUSE: Reference implementation (but we use simpler Procrustes)

---

## ✅ Summary

**What we're doing**:
- Training Ido and Esperanto embeddings with **identical parameters** ✅
- Using Procrustes alignment to map Ido → Esperanto space
- Finding translation candidates via nearest neighbors
- Validating and exporting to Apertium

**Why it works**:
- Both languages share semantic structure
- Word2Vec captures this structure in embeddings
- Procrustes finds the rotation between spaces
- Similar words end up close together after alignment

**Expected outcome**:
- 1,000-3,000 high-confidence new translation pairs
- 85-95% accuracy on known translations (Precision@5)
- Ready to integrate into `apertium-ido-epo`

---

**Next step**: Train Esperanto embeddings on EC2, then run alignment! 🚀

