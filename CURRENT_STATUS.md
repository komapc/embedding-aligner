# Current Status - Dictionary Generation Pipeline

**Last Updated:** 2025-12-03  
**Session:** Bidix Lemma Extraction Fix

## Recent Changes

### ✅ Fixed: Bidix Lemma Extraction (2025-12-03)

**Problem:** Bidix entries were using surface forms (e.g., "persono") instead of lemmas (e.g., "person"), causing translation failures because the morphological analyzer outputs lemmas.

**Solution:**
- Added `extract_lemma_ido()` function to `17_format_for_apertium.py`
- Modified `create_dix_entry()` to extract and use lemmas instead of surface forms
- Regenerated bidix from JSON sources with correct lemma extraction

**Files Modified:**
- `projects/embedding-aligner/scripts/17_format_for_apertium.py`
  - Added `extract_lemma_ido()` function (lines 72-92)
  - Updated `create_dix_entry()` to use lemmas (lines 129-143)

**Rule Added:**
- `.cursor/rules/no-manual-words.mdc` - Prevents manual dictionary edits

## Current State

### ✅ Working

1. **Monodix Generation**
   - YAML lexicon → monodix generation working correctly
   - Stem extraction working for all paradigms
   - Morphological analysis working: `personi` → `person<n><pl><nom>`

2. **Bidix Generation Script**
   - Lemma extraction implemented and working
   - Regeneration from JSON sources functional
   - Multiple format support (BERT, Vortaro, Extractor)

3. **Bidix Entry Format**
   - Entries now use lemmas (e.g., `person<s n="n"/>` instead of `persono<s n="n"/>`)
   - XML structure is correct and validates

### ⚠️ Known Issues

1. **Bidix Matching with POS Tags**
   - **Status:** Under investigation
   - **Symptom:** Words with POS tags in bidix (e.g., `person<s n="n"/>`) are not matching during translation
   - **Example:** `personi` → `@personi` (not translated)
   - **Analysis:**
     - Morphological analysis works: `^personi/person<n><pl><nom>$`
     - Bidix entry exists: `<l>person<s n="n"/></l><r>homo<s n="n"/></r>`
     - Bidix lookup fails: `^person/@person$` (not matched)
   - **Possible Causes:**
     - Apertium bidix matching algorithm may require different format
     - POS tag matching may need additional configuration
     - Whitespace or XML formatting issues
   - **Next Steps:**
     - Investigate Apertium bidix matching behavior with POS tags
     - Compare with working entries (e.g., entries without POS tags work)
     - Check Apertium documentation for bidix POS tag requirements

2. **Some Words Missing from Bidix**
   - Words like "linguo" are not in the bidix (not in JSON sources)
   - This is expected - only words from JSON sources are included

## Technical Details

### Lemma Extraction Logic

The `extract_lemma_ido()` function extracts stems based on POS:

```python
- Nouns ending in -o: remove -o (persono → person)
- Verbs ending in -ar: remove -ar (irar → ir)
- Adjectives ending in -a: remove -a (bona → bon)
- Adverbs ending in -e: remove -e (bone → bon)
- Others: return word as-is
```

This matches the stem extraction logic in `generate_ido_monodix_from_yaml.py`.

### Bidix Generation Workflow

1. **Load JSON sources** (BERT, Vortaro, Extractor formats)
2. **Convert to normalized format** (via `format_converters.py`)
3. **Merge translations** (via `merge_translations.py`)
4. **Generate bidix entries** (via `17_format_for_apertium.py`)
   - Extract lemmas from surface forms
   - Add POS tags when possible
   - Create XML entries
5. **Save to bidix XML file**

### Regeneration Command

```bash
cd projects/embedding-aligner

python3 scripts/regenerate_bidix.py \
  --json results/vortaro_format/ido_epo_dictionary.json \
  --output ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix
```

## Files and Locations

### Key Scripts
- `projects/embedding-aligner/scripts/17_format_for_apertium.py` - Bidix entry generation
- `projects/embedding-aligner/scripts/regenerate_bidix.py` - Main regeneration script
- `projects/embedding-aligner/scripts/generate_ido_monodix_from_yaml.py` - Monodix generation

### Dictionary Files
- `apertium/apertium-ido/apertium-ido.ido.dix` - Ido monodix
- `apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix` - Ido-Esperanto bidix

### Source Data
- `apdata/ido_lexicon.yaml` - YAML lexicon (source of truth for monodix)
- `projects/embedding-aligner/results/vortaro_format/ido_epo_dictionary.json` - Vortaro translations
- `projects/embedding-aligner/results/bert_aligned_clean_0.60/bert_candidates.json` - BERT alignments

## Testing

### Test Morphological Analysis
```bash
cd apertium/apertium-ido-epo
echo "personi" | lt-proc ido-epo.automorf.bin
# Output: ^personi/person<n><pl><nom>$
```

### Test Bidix Lookup
```bash
cd apertium/apertium-ido-epo
echo "^person/person<n><pl><nom>$" | lt-proc -b ido-epo.autobil.bin
# Current output: ^person/@person$ (not matched)
```

### Test Translation
```bash
cd apertium/apertium-ido-epo
echo "personi" | apertium -d . ido-epo
# Current output: @personi (not translated)
```

## Next Session Priorities

1. **Investigate Bidix Matching Issue**
   - Research Apertium bidix matching with POS tags
   - Test different bidix entry formats
   - Compare working vs non-working entries

2. **Verify Lemma Extraction**
   - Test with various word types (nouns, verbs, adjectives, adverbs)
   - Ensure all paradigms are handled correctly

3. **Add More Translation Sources**
   - Include additional JSON sources in regeneration
   - Expand vocabulary coverage

## Related Documentation

- `DICTIONARY_REGENERATION.md` - Complete regeneration workflow
- `SOURCE_JSON_FILES.md` - Available JSON source files
- `.cursor/rules/no-manual-words.mdc` - Rule against manual edits


