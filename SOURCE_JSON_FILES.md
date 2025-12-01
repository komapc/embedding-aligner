# Source JSON Files for Dictionary Generation

Complete list of all JSON files available for dictionary generation.

## 🎯 Primary Source Files (Recommended)

These are the main files you should use for dictionary regeneration:

### 1. 🤖 BERT Alignment Results (Best Quality)

#### **Primary: `bert_aligned_clean_0.60/bert_candidates.json`**
- **Location**: `projects/embedding-aligner/results/bert_aligned_clean_0.60/bert_candidates.json`
- **Size**: 430.1 KB
- **Entries**: 2,608 Ido words → Esperanto candidates
- **Format**: `{"ido_word": [{"translation": "epo_word", "similarity": 0.95}, ...]}`
- **Status**: ✅ **Currently used** - This is what's in your bidix
- **Quality**: Cleaned, high-quality alignments (similarity ≥ 0.60)

#### Alternative: `bert_aligned_clean_0.80/bert_candidates.json`
- **Location**: `projects/embedding-aligner/results/bert_aligned_clean_0.80/bert_candidates.json`
- **Size**: 260.5 KB
- **Entries**: 2,436 Ido words (more conservative, higher quality)
- **Quality**: Even higher quality (similarity ≥ 0.80)

#### Alternative: `bert_aligned/bert_candidates.json`
- **Location**: `projects/embedding-aligner/results/bert_aligned/bert_candidates.json`
- **Size**: 875.3 KB
- **Entries**: 2,623 Ido words (includes lower quality alignments)
- **Quality**: Raw BERT alignment (no cleaning)

#### Alternative: `bert_ido_epo_alignment/translation_candidates.json`
- **Location**: `projects/embedding-aligner/results/bert_ido_epo_alignment/translation_candidates.json`
- **Size**: 3.8 MB
- **Entries**: 5,000 Ido words
- **Quality**: Larger dataset from BERT alignment pipeline

### 2. 📚 Vortaro Format Dictionaries

#### `vortaro_format/ido_epo_dictionary.json`
- **Location**: `projects/embedding-aligner/results/vortaro_format/ido_epo_dictionary.json`
- **Size**: 1.1 MB
- **Format**: Different structure (2 keys, values are lists)
- **Source**: Formatted for Vortaro dictionary format

#### `vortaro_filtered_0.80/dictionary.json`
- **Location**: `projects/embedding-aligner/results/vortaro_filtered_0.80/dictionary.json`
- **Size**: 1.9 MB
- **Entries**: 11,601 keys
- **Quality**: Filtered at 0.80 similarity threshold

#### `vortaro_improved/dictionary.json`
- **Location**: `projects/embedding-aligner/results/vortaro_improved/dictionary.json`
- **Size**: 1.6 MB
- **Entries**: 11,601 keys
- **Quality**: Improved/processed version

### 3. 🔍 Extractor Dictionaries

#### `extractor/dist/bidix_big.json`
- **Location**: `projects/extractor/dist/bidix_big.json`
- **Size**: 4.2 MB
- **Entries**: 8,537 items (list format)
- **Source**: Extracted from Wikipedia/Wiktionary
- **Format**: Different structure - list of entries

#### `extractor/dist/ido_dictionary.json`
- **Location**: `projects/extractor/dist/ido_dictionary.json`
- **Size**: 5.2 MB
- **Entries**: 8,506 items (list format)
- **Source**: Ido words from extractor pipeline

#### `extractor/final_vocabulary.json`
- **Location**: `projects/extractor/final_vocabulary.json`
- **Size**: 800.4 KB
- **Format**: dict with 2 keys
- **Source**: Final vocabulary from extractor

#### `extractor/dictionary_eo_io.json`
- **Location**: `projects/extractor/dictionary_eo_io.json`
- **Size**: 6.5 KB
- **Format**: dict with 2 keys
- **Source**: Extracted Esperanto-Ido dictionary

---

## 📊 Summary Statistics

| Category | Files | Total Size | Primary Use |
|----------|-------|------------|-------------|
| **BERT Alignment** | 4 | ~5.5 MB | ✅ Primary source (currently used) |
| **Vortaro Format** | 3 | ~4.6 MB | Alternative format |
| **Extractor** | 4 | ~10.3 MB | Additional vocabulary |
| **Total** | **11** | **~20.4 MB** | Dictionary generation |

---

## 🔄 Usage with Regeneration Script

### Current Default (Recommended):
```bash
python3 scripts/regenerate_all_from_bert.py \
  --bert-json results/bert_aligned_clean_0.60/bert_candidates.json \
  --rebuild
```

### Use Higher Quality Set:
```bash
python3 scripts/regenerate_all_from_bert.py \
  --bert-json results/bert_aligned_clean_0.80/bert_candidates.json \
  --rebuild
```

### Use Larger Dataset:
```bash
python3 scripts/regenerate_all_from_bert.py \
  --bert-json results/bert_ido_epo_alignment/translation_candidates.json \
  --rebuild
```

---

## 📝 Additional JSON Files

### Statistics Files (Metadata Only):
- `bert_aligned/bert_alignment_stats.json`
- `bert_aligned_clean_0.60/bert_alignment_stats.json`
- `apertium_format/apertium_format_stats.json`
- `apertium_format_fixed/apertium_format_stats.json`
- `dix_format_stats.json`
- `bert_clean_analysis.json`
- `bert_threshold_analysis.json`
- `candidate_stats.json`
- `candidate_stats_aligned.json`
- `vortaro_format/vortaro_stats.json`

### Translation Candidates:
- `candidate_translations.json` (empty)
- `candidate_translations_aligned.json` (130 words)

### Extractor Work Files (47 total JSON files):
Located in `projects/extractor/`:
- `work/bilingual_*.json` - Various bilingual dictionaries
- `work/io_wikipedia_*.json` - Wikipedia extracted data
- `work/io_wiktionary_*.json` - Wiktionary extracted data
- `work/en_wikt_*.json` - English Wiktionary pivot data
- `work/eo_wikt_*.json` - Esperanto Wiktionary data
- And many more intermediate processing files

---

## 🎯 Recommendations

1. **For Production**: Use `bert_aligned_clean_0.60/bert_candidates.json` (current default)
   - Best balance of quality and quantity
   - Already tested and working

2. **For Higher Quality**: Use `bert_aligned_clean_0.80/bert_candidates.json`
   - More conservative threshold
   - Fewer entries but higher confidence

3. **For Maximum Coverage**: Use `bert_ido_epo_alignment/translation_candidates.json`
   - Largest dataset (5,000 words)
   - May include lower quality alignments

4. **For Additional Vocabulary**: Combine with extractor dictionaries
   - Use `extractor/dist/bidix_big.json` for proper nouns, geographic names
   - Use `extractor/dist/ido_dictionary.json` for monolingual vocabulary

---

## 📚 File Format Notes

### BERT Candidates Format:
```json
{
  "ido_word": [
    {"translation": "esperanto_word", "similarity": 0.95},
    {"translation": "alternative", "similarity": 0.85}
  ]
}
```

### Vortaro Format:
Different structure - may need conversion script

### Extractor Format:
Various structures - may need format-specific scripts

---

**Last Updated**: 2025-11-24  
**Total Source Files**: 14 primary + 47 extractor work files = 61 JSON files

