# Setup Instructions

## 1. Python Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## 2. Install FastText

```bash
# Clone and build FastText
git clone https://github.com/facebookresearch/fastText.git
cd fastText
make
# Binary will be at: fastText/fasttext

# Add to PATH or note the location
export FASTTEXT_BIN=$(pwd)/fasttext
```

## 3. Install VecMap

```bash
# Clone VecMap
git clone https://github.com/artetxem/vecmap.git
# Scripts will be in: vecmap/

# Note the location
export VECMAP_DIR=$(pwd)/vecmap
```

## 4. Prepare Seed Dictionary

The seed dictionary should be in format:
```
ido_word esperanto_word
altra alia
amiko amiko
bona bona
...
```

Place your 50K dictionary at:
```
data/dictionaries/seed_dictionary_50k.txt
```

The scripts will automatically split it into:
- `train_45k.txt` (90% for training alignment)
- `validation_5k.txt` (10% for validation)

## 5. Verify Setup

```bash
# Check Python packages
python -c "import numpy, scipy, wikiextractor; print('Python packages OK')"

# Check FastText
$FASTTEXT_BIN --help

# Check VecMap
python $VECMAP_DIR/map_embeddings.py --help
```

## 6. Directory Structure

After setup, you should have:
```
embedding-aligner/
├── venv/                   # Python virtual environment
├── fastText/               # FastText installation
├── vecmap/                 # VecMap installation
├── data/
│   └── dictionaries/
│       └── seed_dictionary_50k.txt
└── ...
```

## Disk Space Requirements

- Wikipedia dumps: ~500MB compressed, ~2GB uncompressed
- Trained embeddings: ~500MB each (Ido + Esperanto)
- Aligned embeddings: ~500MB each
- **Total**: ~5-10GB

## Compute Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Time**: 
  - Ido embeddings: 10-30 minutes
  - Esperanto embeddings: 1-2 hours
  - Alignment: 5-10 minutes
  - Candidate generation: 5-10 minutes

## Next Steps

After setup is complete, proceed to `README.md` for the pipeline execution steps.
