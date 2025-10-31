# Ido Wikipedia Corpus - Ready for Embeddings

## ✓ Processing Complete

**Final Ido corpus successfully created and cleaned!**

### Statistics

- **Input**: `iowiki-latest-pages-articles.xml.bz2`
- **Output**: `data/processed/ido_corpus_final.txt`
- **Articles processed**: 60,324
- **Articles skipped**: 20,958 (special pages, redirects, etc.)
- **Total sentences**: 392,319 lines
- **Processing time**: 27.03 seconds
- **Speed**: 2,231 articles/second

### Cleaning Applied

**Removed:**
- ✓ All `{{Biografio}}` templates
- ✓ All `{{#ifexist:...}}` templates
- ✓ All images and file links
- ✓ Categories
- ✓ References sections
- ✓ HTML comments and tags
- ✓ Color codes (`{{#8888FF}}`)
- ✓ Math expressions (`{{#expr:...}}`)
- ✓ Wikidata properties (`{{#property:...}}`)
- ✓ Timeline tags (`{{#tag:timeline}}`)
- ✓ Country/region codes (`{{AUT-HUN}}`, `{{BR-PR}}`, etc.)
- ✓ Abbreviation templates (`{{Abbr}}`)
- ✓ Audio templates (`{{Audio}}`)
- ✓ DISPLAYTITLE templates
- ✓ Category markers (`{{Cienci}}`, `{{linguistiko}}`, etc.)
- ✓ List/navigation templates
- ✓ Editorial markers (`{{Citation needed}}`, `{{stub}}`, etc.)

**Extracted:**
- ✓ Numbers from `{{formatnum:123}}` → `123`
- ✓ Visible text from `[[wiki links]]`
- ✓ Clean sentences, lowercase

### Sample Output

```
ido esas "decendanto" di esperanto
pos sua komenco, ido recevis suporto di uli de la esperanto-komunitato
tamen, problemi eventis pos la subita morto en 1914 di un ek sua maxim influanta adepti, louis couturat
en 1928, otto jespersen abandonis ido-movado por developar sua propra linguo novial
```

## Next Steps

1. ✓ **Ido corpus ready** (392K sentences)
2. **Process Esperanto Wikipedia** (same approach)
3. **Train FastText embeddings** on both corpora
4. **Align embedding spaces** using VecMap with 45K seed dictionary
5. **Find translation candidates** with high precision

## Files

- **Corpus**: `projects/embedding-aligner/data/processed/ido_corpus_final.txt`
- **Size**: ~392K sentences, ready for FastText training
- **Format**: One sentence per line, lowercase, clean text

The corpus is production-ready for embedding training!
