# Artifacts and Usage Guide

## Generated Artifacts

### 1. Trained Model Files (2.4 GB total)

Located in `models/`:

```
ido_fasttext.model                    1.4 MB  - Model metadata and configuration
ido_fasttext.model.syn1neg.npy         52 MB  - Negative sampling weights
ido_fasttext.model.wv.vectors_ngrams.npy  2.3 GB  - Character n-gram vectors
ido_fasttext.model.wv.vectors_vocab.npy   52 MB  - Word vocabulary vectors
```

**What they contain:**
- **45,301 words** in vocabulary
- **300-dimensional** vectors for each word
- **Character n-grams** (3-6 characters) for handling morphology
- Trained on **6.6M tokens** from Ido Wikipedia

### 2. Processed Corpus

Located in `data/processed/`:

```
ido_clean.txt    - 326,291 cleaned sentences
```

## How to Find Similar Words

### Quick Query Tool

Use the provided script:

```bash
# Activate virtual environment
source venv/bin/activate

# Find 10 most similar words
python3 scripts/query_similar_words.py <word>

# Find 20 most similar words
python3 scripts/query_similar_words.py <word> --topn 20
```

### Examples

```bash
# Language-related words
python3 scripts/query_similar_words.py linguo
# Output: lingui, lingua, idolinguo, linguaro, etc.

# Ido-related words
python3 scripts/query_similar_words.py ido
# Output: idolo, ido-revuo, esperantido, idolinguo, etc.

# Animal words
python3 scripts/query_similar_words.py hundo
# Output: fundo, mundo, pundo (similar endings)

# Verbs
python3 scripts/query_similar_words.py irar
# Output: tirar, ekirar, enirar (movement verbs)
```

### Python API Usage

```python
from gensim.models import FastText

# Load model
model = FastText.load('models/ido_fasttext.model')

# Find similar words
similar = model.wv.most_similar('hundo', topn=10)
for word, score in similar:
    print(f"{word}: {score:.3f}")

# Get word vector
vector = model.wv['hundo']  # 300-dimensional numpy array

# Check if word exists
if 'hundo' in model.wv:
    print("Word found!")

# Get word frequency
freq = model.wv.get_vecattr('hundo', 'count')
print(f"Frequency: {freq}")

# Works with out-of-vocabulary words (using character n-grams)
vector_oov = model.wv['hundeto']  # Even if not in training data
```

## Understanding Similarity Scores

- **0.9-1.0**: Very similar (variants, typos, inflections)
- **0.7-0.9**: Semantically related (synonyms, related concepts)
- **0.5-0.7**: Somewhat related (same domain)
- **< 0.5**: Weakly related or unrelated

## Model Statistics

- **Vocabulary**: 45,301 unique words
- **Training corpus**: 326,291 sentences (6.6M tokens)
- **Vector dimension**: 300
- **Character n-grams**: 3-6 characters
- **Training time**: ~8 minutes (4 CPU cores)
- **Model size**: 2.4 GB

## What Makes This Model Special

### 1. Character N-grams
The model can handle:
- **Morphological variants**: hundo → hundeto, hundino
- **Compound words**: ido-linguo, ido-movado
- **Out-of-vocabulary words**: Can generate vectors for unseen words

### 2. Skip-gram Architecture
- Better for rare words
- Captures semantic relationships
- Good for small corpora

### 3. Trained on Wikipedia
- Diverse vocabulary
- Natural language usage
- Domain coverage

## Use Cases

### 1. Dictionary Extension
Find translation candidates by comparing with Esperanto embeddings

### 2. Spell Checking
Find similar words for typo correction

### 3. Semantic Search
Find conceptually related words

### 4. Word Clustering
Group words by meaning

### 5. Morphological Analysis
Understand word formation patterns

## Next Steps

Once Esperanto embeddings are trained:
1. Align the two embedding spaces
2. Find translation candidates
3. Validate with existing dictionary
4. Discover new translations

## Technical Details

### FastText Parameters Used

```python
FastText(
    vector_size=300,      # Embedding dimension
    window=5,             # Context window (±5 words)
    min_count=5,          # Ignore words appearing < 5 times
    workers=4,            # Parallel processing
    sg=1,                 # Skip-gram (vs CBOW)
    min_n=3,              # Min character n-gram length
    max_n=6,              # Max character n-gram length
    epochs=10             # Training iterations
)
```

### Why These Parameters?

- **300d vectors**: Standard size, good balance
- **Window=5**: Captures local context
- **Min_count=5**: Filters noise, keeps meaningful words
- **Skip-gram**: Better for rare words and small corpora
- **N-grams 3-6**: Captures morphemes in Ido
- **10 epochs**: Sufficient convergence

## Troubleshooting

### Model Loading Error
If you get pickle errors, make sure the EpochLogger class is defined:
```python
from gensim.models.callbacks import CallbackAny2Vec

class EpochLogger(CallbackAny2Vec):
    def __init__(self):
        self.epoch = 0
    def on_epoch_end(self, model):
        self.epoch += 1
```

### Out of Memory
The model is 2.4 GB. Ensure you have at least 4 GB RAM available.

### Word Not Found
Use FastText's character n-gram feature - it can still generate vectors for OOV words.
