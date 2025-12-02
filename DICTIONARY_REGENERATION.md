# Dictionary Regeneration Workflow

## Overview

This document explains how to regenerate **all dictionaries** (bidix + monodix) from **multiple JSON sources** (BERT, Vortaro, Extractor formats).

## Quick Answer

**YES** - When you update any JSON sources, you can regenerate all dictionaries with **two commands**:

```bash
cd projects/embedding-aligner

# Step 1: Regenerate bidix from all JSON sources
python3 scripts/regenerate_bidix.py \
  --json results/bert_aligned_clean_0.60/bert_candidates.json \
  --json results/vortaro_format/ido_epo_dictionary.json \
  --json extractor/dist/bidix_big.json \
  --output ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix

# Step 2: Regenerate monodix from updated bidix
python3 scripts/regenerate_monodix.py \
  --bidix ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix \
  --yaml ../../apdata/ido_lexicon.yaml \
  --output ../../apertium/apertium-ido/apertium-ido.ido.dix
```

This will:
1. ✅ Regenerate **bidix** from multiple JSON sources (all formats supported)
2. ✅ Extract new lemmas from bidix → update **YAML lexicon**
3. ✅ Regenerate **monodix** from YAML
4. ✅ Keep ALL translation alternatives (no deduplication)

## Complete Workflow

### When You Update Sources

**After updating any source** (Wikipedia/Wiktionary dumps, BERT extraction, new word sources):

1. **Regenerate bidix from all JSON sources**:
   ```bash
   cd projects/embedding-aligner
   
   python3 scripts/regenerate_bidix.py \
     --json results/bert_aligned_clean_0.60/bert_candidates.json \
     --json results/vortaro_format/ido_epo_dictionary.json \
     --json extractor/dist/bidix_big.json \
     --output ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix
   ```
   
   Supports multiple formats automatically:
   - **BERT format**: `{"ido_word": [{"translation": "...", "similarity": ...}]}`
   - **Vortaro format**: `{"ido_to_esperanto": [...]}`
   - **Extractor format**: `[{"lemma": "...", "senses": [...]}]`

2. **Regenerate monodix from updated bidix**:
   ```bash
   python3 scripts/regenerate_monodix.py \
     --bidix ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix \
     --yaml ../../apdata/ido_lexicon.yaml \
     --output ../../apertium/apertium-ido/apertium-ido.ido.dix
   ```

3. **Rebuild analyzers**:
   ```bash
   cd ../../apertium/apertium-ido && make clean && make
   cd ../apertium-ido-epo && make clean && make
   ```

4. **Test translation**:
   ```bash
   cd apertium/apertium-ido-epo
   echo "Hodie partoprenis kin Idisti..." | apertium -d . ido-epo
   ```

## What Gets Regenerated

### 1. Bilingual Dictionary (bidix)
- **Sources**: Multiple JSON files (BERT, Vortaro, Extractor formats)
- **Output**: `apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix`
- **Script**: `regenerate_bidix.py`
- **Process**: Multiple JSON → normalized format → merged (all translations kept) → bidix XML

### 2. YAML Lexicon (source of truth)
- **File**: `apdata/ido_lexicon.yaml`
- **Process**: New lemmas extracted from updated bidix → added to YAML
- **Format**: Human-readable YAML with lemmas + POS + paradigms

### 3. Monolingual Dictionary (monodix)
- **Source**: Updated bidix → extracted lemmas → YAML lexicon
- **Output**: `apertium/apertium-ido/apertium-ido.ido.dix`
- **Script**: `regenerate_monodix.py`
- **Process**: Bidix → extract lemmas → update YAML → generate monodix XML

### 4. Compiled Analyzers
- **Ido analyzer**: `apertium/apertium-ido/ido.automorf.bin`
- **Bilingual analyzer**: `apertium/apertium-ido-epo/ido-epo.autobil.bin`
- **Process**: `make clean && make` in each repo

## Script Options

### regenerate_bidix.py

```bash
python3 scripts/regenerate_bidix.py \
  --json FILE1.json \
  --json FILE2.json \
  [--format bert|vortaro|extractor] \
  [--format bert|vortaro|extractor] \
  --output OUTPUT.dix \
  [--min-similarity 0.0] \
  [--max-translations N] \
  [--add-pos-tags]
```

**Options:**
- `--json`: **Required, repeatable**. JSON source file (can specify multiple)
- `--format`: Optional format for each JSON file (auto-detected if not specified)
- `--output`: **Required**. Output bidix XML file path
- `--min-similarity`: Minimum similarity threshold (default: 0.0 = keep all)
- `--max-translations`: Max translations per word (default: None = keep all)
- `--add-pos-tags`: Add POS tags based on morphology (default: True)

**Supported Formats:**
- `bert`: BERT alignment candidates format
- `vortaro`: Vortaro dictionary format
- `extractor`: Extractor/Wiktionary format

### regenerate_monodix.py

```bash
python3 scripts/regenerate_monodix.py \
  --bidix INPUT.dix \
  [--yaml ../../apdata/ido_lexicon.yaml] \
  [--output ../../apertium/apertium-ido/apertium-ido.ido.dix]
```

**Options:**
- `--bidix`: **Required**. Input bidix file path
- `--yaml`: YAML lexicon file (default: `../../apdata/ido_lexicon.yaml`)
- `--output`: Output monodix file (default: `../../apertium/apertium-ido/...`)

## Example Usage Scenarios

### Scenario 1: Update after BERT alignment improvements
```bash
# After improving BERT extraction algorithm:
python3 scripts/regenerate_bidix.py \
  --json results/bert_aligned_clean_0.60/bert_candidates.json \
  --output ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix

python3 scripts/regenerate_monodix.py \
  --bidix ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix
```

### Scenario 2: Combine multiple sources
```bash
# Combine BERT + Vortaro + Extractor:
python3 scripts/regenerate_bidix.py \
  --json results/bert_aligned_clean_0.60/bert_candidates.json \
  --json results/vortaro_format/ido_epo_dictionary.json \
  --json extractor/dist/bidix_big.json \
  --output ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix

python3 scripts/regenerate_monodix.py \
  --bidix ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix
```

### Scenario 3: After redownloading Wikipedia/Wiktionary
```bash
# After extracting new data:
python3 scripts/regenerate_bidix.py \
  --json extractor/dist/bidix_big.json \
  --json extractor/dist/ido_dictionary.json \
  --output ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix

python3 scripts/regenerate_monodix.py \
  --bidix ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix
```

## Benefits of This Approach

✅ **Multiple JSON formats supported** - BERT, Vortaro, Extractor automatically detected  
✅ **All translations preserved** - no deduplication, keeps all alternatives  
✅ **Explicit file paths** - full control over which sources to use  
✅ **Two-script workflow** - clear separation: bidix generation → monodix generation  
✅ **No manual editing** - all changes are script-driven  
✅ **YAML as source of truth** - human-readable, version-controllable  
✅ **Automatic lemma extraction** - bidix → YAML → monodix pipeline  
✅ **Reproducible** - same JSON sources → same dictionaries  
✅ **Incremental** - adds new lemmas without breaking existing ones  

## Testing

Run all tests to verify the pipeline:

```bash
cd projects/embedding-aligner/scripts
python3 run_tests.py
```

This runs:
- **Format converter tests** (`test_format_converters.py`) - Tests BERT/Vortaro/Extractor format conversion
- **Merge translation tests** (`test_merge_translations.py`) - Tests merging multiple sources
- **Full pipeline integration tests** (`test_regeneration_pipeline.py`) - Tests end-to-end workflow

Individual tests can also be run directly:

```bash
python3 test_format_converters.py
python3 test_merge_translations.py
python3 test_regeneration_pipeline.py
```

All tests should pass before committing changes to the regeneration scripts.

## Troubleshooting

### YAML file not found
```bash
# Create initial YAML from existing monodix:
python3 scripts/bootstrap_ido_yaml_from_monodix.py \
  --monodix ../../apertium/apertium-ido/apertium-ido.ido.dix \
  --output ../../apdata/ido_lexicon.yaml
```

### Analyzer rebuild fails
- Check that all dependencies are installed
- Verify XML is valid: `xmllint --noout apertium-ido.ido.dix`
- Check make logs for specific errors

### Missing paradigms
- Edit `apdata/ido_lexicon.yaml` to add new paradigms
- Or update `regenerate_all_from_bert.py` to handle new POS types

## Related Scripts

### Main Regeneration Scripts:
- `regenerate_bidix.py` - **Primary script**: Multiple JSON formats → unified bidix XML
- `regenerate_monodix.py` - **Primary script**: Bidix → extract lemmas → update YAML → monodix XML

### Supporting Modules:
- `format_converters.py` - Convert BERT/Vortaro/Extractor formats to common format
- `merge_translations.py` - Merge multiple sources keeping all translations

### Legacy Scripts (still available):
- `17_format_for_apertium.py` - BERT JSON → bidix XML (used by regenerate_bidix.py)
- `generate_ido_monodix_from_yaml.py` - YAML → monodix XML (used by regenerate_monodix.py)
- `regenerate_all_from_bert.py` - Old unified script (BERT-only, use regenerate_bidix.py instead)
- `bootstrap_ido_yaml_from_monodix.py` - monodix → YAML (one-time bootstrap)

