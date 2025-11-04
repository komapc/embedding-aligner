# Pipeline Overview - Quick Reference

## Project Structure

```
projects/embedding-aligner/
├── scripts/                           # Pipeline scripts (01-07)
├── data/
│   ├── raw/                          # Raw corpora
│   ├── processed/                    # Cleaned corpora
│   └── seed_dictionary.txt           # Generated from vortaro
├── models/                           # Trained embeddings & alignment
├── results/                          # Translation candidates
├── requirements.txt                  # Python dependencies
├── run_pipeline.sh                   # Run all steps
├── ALIGNMENT_PLAN.md                 # Detailed plan
└── IMPLEMENTATION_STATUS.md          # Current status
```

## Pipeline Scripts (Skeleton Created)

| Script | Purpose | Input | Output | Status |
|--------|---------|-------|--------|--------|
| `01_prepare_corpora.py` | Clean & tokenize | Raw corpora | Clean corpora | ⏳ TODO |
| `02_train_ido_embeddings.py` | Train Ido FastText | Ido corpus | Ido model | ⏳ TODO |
| `03_train_epo_embeddings.py` | Train Epo FastText | Epo corpus | Epo model | ⏳ TODO |
| `04_extract_seed_dict.py` | Extract dictionary | vortaro JSON | Seed pairs | ⏳ TODO |
| `05_align_embeddings.py` | Learn mapping | Models + seed | Alignment matrix | ⏳ TODO |
| `06_find_candidates.py` | Find translations | Aligned models | Candidates JSON | ⏳ TODO |
| `07_validate_candidates.py` | Filter & rank | Candidates | High/med/low conf | ⏳ TODO |

## Quick Start

### 1. Install Dependencies
```bash
cd projects/embedding-aligner
pip install -r requirements.txt
```

### 2. Prepare Data
- Ido corpus: Already at `data/processed/ido_corpus.txt` (300K phrases)
- Esperanto corpus: Need to obtain and place at `data/raw/epo_corpus.txt`
- Dictionary: Already at `terraform/extractor-results/.../vortaro_dictionary.json`

### 3. Run Pipeline
```bash
# Run all steps
./run_pipeline.sh

# Or run individually
python3 scripts/01_prepare_corpora.py
python3 scripts/02_train_ido_embeddings.py
# etc.
```

## Implementation Order

1. **Start with Step 1** (`01_prepare_corpora.py`)
   - Implement text cleaning
   - Test on small sample
   - Verify output format

2. **Then Step 2** (`02_train_ido_embeddings.py`)
   - Implement FastText training
   - Test with Ido corpus
   - Check embedding quality

3. **Continue sequentially** through steps 3-7

## Key Functions to Implement

Each script has TODO markers for:
- Data loading/saving
- Core algorithm implementation
- Evaluation/statistics
- Error handling

## Testing Strategy

1. **Unit test** each function with small data
2. **Integration test** each script end-to-end
3. **Pipeline test** with subset of data
4. **Full run** on complete corpus

## Expected Timeline

- Implementation: 2-3 days
- Testing: 1 day
- Full pipeline run: 1-2 hours
- Evaluation: 1 day

## Next Action

Start implementing `01_prepare_corpora.py` - the text cleaning and preparation script.
