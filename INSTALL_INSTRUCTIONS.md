# Installation Instructions

## System Requirements

Install Python venv support:
```bash
sudo apt install python3.12-venv
```

## Setup Virtual Environment

```bash
cd projects/embedding-aligner

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Verify Installation

```bash
python3 -c "import gensim; print('Gensim version:', gensim.__version__)"
```

## Running the Pipeline

With venv activated:
```bash
./run_pipeline.sh
```

Or run individual steps:
```bash
python3 scripts/01_prepare_corpora.py
python3 scripts/02_train_ido_embeddings.py
# etc.
```
