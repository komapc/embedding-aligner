# Embedding Quality Improvement Strategies

## Current Status
- **Corpus size**: 6M words, 361K sentences
- **Vocabulary**: 46,410 words (min_count=5)
- **Vector size**: 300
- **Window**: 10
- **Model**: Word2Vec Skip-gram

## Problems Observed
1. **"ludo" → "duopla"** - tennis doubles, not semantic match
2. **"hundo" → "kaudo", "ortros"** - body parts and mythology, not animals
3. **"kato" → "takaaki", "felis"** - person names and Latin, not semantic
4. Results show **proper nouns dominating** (tennis players, mythology)

## Root Cause Analysis

### Issue 1: Wikipedia Bias
Wikipedia is **encyclopedia-heavy**, containing:
- Lots of proper nouns (people, places, mythology)
- Technical/specialized vocabulary
- Less common everyday language
- Unbalanced topic distribution

### Issue 2: Small Corpus for Rare Words
- 6M words is small for Word2Vec
- Rare words (freq < 20) have poor embeddings
- Need 10M+ words for good quality

### Issue 3: Proper Noun Pollution
- Names cluster together (tennis players, mythological figures)
- They dominate similarity results
- Need filtering or different corpus

---

## Strategy 1: Improve Current Corpus (No New Data)

### A. Filter Proper Nouns
**Goal**: Remove or downweight proper nouns

```python
# Add to preprocessing
import re

def is_proper_noun(word):
    """Detect proper nouns (capitalized words)."""
    return word[0].isupper() and len(word) > 1

def filter_proper_nouns(sentence):
    """Remove proper nouns from sentence."""
    return [w for w in sentence if not is_proper_noun(w)]
```

**Impact**: ✅ Removes tennis players, mythology names
**Tradeoff**: ❌ Loses legitimate capitalized words

### B. Increase Min Count
**Goal**: Keep only frequent words with good statistics

```python
# Current: min_count=5
# Try: min_count=10 or min_count=20
```

**Impact**: 
- ✅ Better quality for remaining words
- ✅ Removes rare proper nouns
- ❌ Smaller vocabulary (30K-35K words)

### C. Subsampling Frequent Words
**Goal**: Reduce impact of very common words (la, di, por)

```python
# Add to Word2Vec training
model = Word2Vec(
    sample=1e-5,  # Subsample frequent words
    ...
)
```

**Impact**: ✅ Better balance, less common word dominance

### D. Increase Training Epochs
**Goal**: Better convergence for small corpus

```python
# Current: epochs=30
# Try: epochs=50 or epochs=100
```

**Impact**: 
- ✅ Better embeddings for existing data
- ⚠️ Longer training time
- ⚠️ Risk of overfitting

### E. Adjust Window Size
**Goal**: Capture different context patterns

```python
# Current: window=10 (very large)
# Try: window=5 (more focused context)
```

**Impact**: 
- ✅ More precise semantic relationships
- ❌ Less broad context

### F. Use CBOW Instead of Skip-gram
**Goal**: Better for small corpus

```python
# Current: sg=1 (Skip-gram)
# Try: sg=0 (CBOW)
```

**Impact**: 
- ✅ CBOW works better with small data
- ✅ Faster training
- ❌ Slightly lower quality for rare words

---

## Strategy 2: Corpus Expansion (Recommended)

### Priority 1: Ido Literature & Texts
**Sources**:
- Ido Wikipedia (already have)
- **Ido Wiktionary** - definitions, examples
- **Ido Wikisource** - literature, documents
- **Ido Wikiquote** - quotations
- **Ido Wikibooks** - educational content

**How to get**:
```bash
# Download Ido Wikisource
wget https://dumps.wikimedia.org/iowikisource/latest/iowikisource-latest-pages-articles.xml.bz2

# Download Ido Wiktionary
wget https://dumps.wikimedia.org/iowiktionary/latest/iowiktionary-latest-pages-articles.xml.bz2
```

**Expected gain**: +2-5M words

### Priority 2: Ido Forums & Discussions
**Sources**:
- Ido mailing lists archives
- Ido forum posts
- Ido social media (if available)

**Why**: Natural, conversational language (not encyclopedia)

**Expected gain**: +1-3M words

### Priority 3: Ido Translations
**Sources**:
- Translated literature (public domain)
- Bible translations in Ido
- UN documents in Ido
- Parallel corpora (Ido-Esperanto, Ido-English)

**Expected gain**: +5-10M words

### Priority 4: Synthetic Data
**Sources**:
- Back-translate from Esperanto using existing dictionary
- Generate sentences using grammar rules
- Use existing Ido-Esperanto dictionary to create examples

**Expected gain**: +10-50M words (but lower quality)

---

## Strategy 3: Model Architecture Changes

### A. Use FastText with Character N-grams
**Already tried, but worth revisiting with clean corpus**

```python
from gensim.models import FastText

model = FastText(
    vector_size=300,
    window=5,
    min_count=10,
    min_n=3,  # Character n-gram min
    max_n=6,  # Character n-gram max
    ...
)
```

**Impact**: 
- ✅ Better for morphologically rich language (Ido)
- ✅ Handles rare words better
- ✅ Can infer vectors for OOV words

### B. Use Larger Vectors
```python
# Current: vector_size=300
# Try: vector_size=500 or vector_size=1000
```

**Impact**: 
- ✅ More capacity for semantic information
- ❌ Requires more data
- ❌ Slower training

### C. Negative Sampling Adjustment
```python
# Current: negative=5
# Try: negative=10 or negative=20
```

**Impact**: ✅ Better discrimination between similar/dissimilar words

---

## Strategy 4: Post-Processing

### A. Filter Results by POS Tags
**Goal**: Only show nouns when querying nouns

**Requires**: POS tagger for Ido (doesn't exist yet)

### B. Frequency-Based Filtering
**Goal**: Exclude very rare words from results

```python
def filter_by_frequency(results, min_freq=20):
    return [(w, s, f) for w, s, f in results if f >= min_freq]
```

**Impact**: ✅ Removes rare proper nouns and noise

### C. Blacklist Proper Nouns
**Goal**: Manually exclude known problematic words

```python
BLACKLIST = {'krejčíková', 'vesnina', 'barbora', 'ortros', 'kerberos', ...}

def filter_blacklist(results):
    return [(w, s, f) for w, s, f in results if w not in BLACKLIST]
```

---

## Recommended Action Plan

### Phase 1: Quick Wins (Current Corpus)
1. ✅ **Increase min_count to 10-20** - removes rare noise
2. ✅ **Add subsampling (sample=1e-5)** - balances frequent words
3. ✅ **Reduce window to 5** - more focused semantics
4. ✅ **Try CBOW (sg=0)** - better for small corpus
5. ✅ **Filter proper nouns** - remove capitalized words

**Expected improvement**: 20-30% better semantic quality

### Phase 2: Corpus Expansion (Your Task)
1. 🔍 **Download Ido Wikisource** - literature
2. 🔍 **Download Ido Wiktionary** - definitions
3. 🔍 **Find Ido forums/mailing lists** - natural language
4. 🔍 **Find Ido translations** - parallel texts

**Expected improvement**: 50-100% better (with 10M+ words)

### Phase 3: Advanced (If Needed)
1. Use FastText with character n-grams
2. Implement POS-based filtering
3. Train on combined Ido+Esperanto with alignment

---

## Corpus Sources to Explore

### Wikimedia Projects
- ✅ Wikipedia (already have)
- 🔍 Wikisource: https://io.wikisource.org/
- 🔍 Wiktionary: https://io.wiktionary.org/
- 🔍 Wikiquote: https://io.wikiquote.org/
- 🔍 Wikibooks: https://io.wikibooks.org/

### Ido Community
- 🔍 Ido mailing lists: http://groups.yahoo.com/group/idolisto/
- 🔍 Ido forums: http://www.idolinguo.org.uk/forum/
- 🔍 Ido Facebook groups
- 🔍 Ido Telegram channels

### Literature & Translations
- 🔍 Project Gutenberg (Ido translations)
- 🔍 Bible in Ido
- 🔍 Ido literature archives
- 🔍 Translated novels/stories

### Parallel Corpora
- 🔍 Tatoeba sentences (Ido-Esperanto pairs)
- 🔍 OpenSubtitles (if Ido subtitles exist)
- 🔍 OPUS corpus (multilingual parallel texts)

---

## Next Steps

1. **I'll implement Phase 1 improvements** (quick wins with current corpus)
2. **You find more Ido text** (Wikisource, forums, translations)
3. **We retrain with expanded corpus**
4. **Evaluate and iterate**

Would you like me to implement Phase 1 improvements now?
