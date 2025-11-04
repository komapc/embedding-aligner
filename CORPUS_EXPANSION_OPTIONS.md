# Corpus Expansion Options

## Current Situation
- **326K sentences** from Ido Wikipedia
- **6.6M tokens**
- This is **too small** for high-quality semantic embeddings

## The Real Solution: More Data

### Target: 1M+ sentences (3x current size)

## Data Sources for Ido

### 1. **Tatoeba Sentences** (Easy, ~10K sentences)
```bash
# Download Tatoeba Ido sentences
wget https://downloads.tatoeba.org/exports/sentences.tar.bz2
# Extract Ido sentences (language code: io)
```
**Pros**: Clean, natural sentences
**Cons**: Only ~10K sentences

### 2. **Ido Literature/Books** (Medium, varies)
- Project Gutenberg Ido texts
- Ido translations of classics
- Ido original literature

**Pros**: High quality, natural language
**Cons**: Need to find and process

### 3. **Ido Forums/Websites** (Medium, ~50-100K)
- idolisto.org archives
- Ido Facebook groups
- Ido blogs and articles

**Pros**: Modern, conversational language
**Cons**: Need web scraping, quality varies

### 4. **Ido-Esperanto Parallel Corpus** (Hard, very valuable)
- Side-by-side translations
- Can use for better alignment

**Pros**: Perfect for your translation task!
**Cons**: Hard to find

### 5. **Machine Translation** (Last resort)
- Translate Esperanto → Ido
- Use existing MT systems

**Pros**: Can generate millions of sentences
**Cons**: Quality issues, circular dependency

## Quick Wins

### Option A: Combine Multiple Sources
```bash
# 1. Current Wikipedia: 326K
# 2. Tatoeba: +10K  
# 3. Ido websites: +50K
# Total: ~400K (still small but better)
```

### Option B: Use Esperanto as Proxy
Since Ido and Esperanto are similar:
1. Train on large Esperanto corpus (millions of sentences available)
2. Use dictionary to bridge the gap
3. Fine-tune on Ido data

### Option C: Accept Limitations
- Use current embeddings for alignment task
- Trust that dictionary-supervised alignment will compensate
- Focus on high-frequency words only

## Recommended Approach

### Short-term (Now):
1. **Try optimized parameters** (I'll help you)
2. **Lower min_count to 5** (keep more words)
3. **Use Word2Vec** (best for small corpus)

### Medium-term (This week):
1. **Add Tatoeba sentences** (~10K more)
2. **Scrape Ido websites** (idolisto.org, etc.)
3. **Target: 400-500K sentences**

### Long-term (Future):
1. **Find Ido literature corpus**
2. **Create Ido-Esperanto parallel corpus**
3. **Target: 1M+ sentences**

## Realistic Expectations

With 326K sentences:
- **High-frequency words** (1000+ occurrences): Good quality
- **Medium-frequency words** (100-1000): Acceptable
- **Low-frequency words** (<100): Poor quality

This is why "hundo" (56 occurrences) gives poor results.

## Alternative: Focus on Translation Task

**Remember**: Your goal isn't perfect monolingual embeddings - it's **translation discovery**.

The alignment step using your dictionary will:
1. Provide semantic supervision
2. Correct for corpus limitations
3. Work even with imperfect embeddings

So the current approach might be "good enough" for your actual use case!

## Next Steps

Want me to:
1. **Run parameter optimization experiments** (30 min)
2. **Help you download Tatoeba** (5 min)
3. **Proceed with current embeddings** and trust alignment
4. **All of the above**

Choose based on your time/quality trade-off.
