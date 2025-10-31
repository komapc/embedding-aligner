# Wikipedia Parser Test Results

## Current Status

The Wikipedia parser (`parse_wikipedia_xml.py`) is ready but needs actual Wikipedia XML dumps to process.

## What We Have

- `projects/data/sources/source_io_wikipedia.json` - Contains only article titles/lemmas from langlinks (5,031 entries)
- This is NOT full article text, just metadata

## What We Need

Download actual Wikipedia XML dumps:

```bash
# Ido Wikipedia (small, ~10MB compressed)
wget https://dumps.wikimedia.org/iowiki/latest/iowiki-latest-pages-articles.xml.bz2

# Esperanto Wikipedia (larger, ~300MB compressed)
wget https://dumps.wikimedia.org/eowiki/latest/eowiki-latest-pages-articles.xml.bz2
```

## Test Command (Once Downloaded)

```bash
# Test with 500 articles from Ido Wikipedia
python3 projects/embedding-aligner/scripts/parse_wikipedia_xml.py \
  --input iowiki-latest-pages-articles.xml.bz2 \
  --output projects/embedding-aligner/data/processed/ido_corpus_test.txt \
  --limit 500 \
  --collect-questions
```

## Parser Features

The parser:
- ✓ Handles .bz2 and .gz compressed files
- ✓ Extracts main article content
- ✓ Removes categories, templates, references
- ✓ Handles [[wiki links]] properly (keeps display text)
- ✓ Stops at "References" section
- ✓ Splits into sentences
- ✓ Lowercases for embeddings
- ✓ Collects questions about uncertain templates
- ✓ Shows progress and timing

## Expected Performance

Based on similar parsers:
- **Ido Wikipedia** (~2,000 articles): 1-2 minutes
- **Esperanto Wikipedia** (~300,000 articles): 30-60 minutes

## Next Steps

1. Download Wikipedia dumps (see commands above)
2. Run parser with `--limit 500` to test
3. Review output and template questions
4. Run full processing
5. Proceed with FastText training
