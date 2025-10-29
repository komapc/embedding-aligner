# Installing Dependencies

## Python Packages

Since your system uses externally-managed Python, you have two options:

### Option 1: Use pipx (Recommended for system-wide tools)

```bash
# Install pipx if not already installed
sudo apt install pipx

# Install packages
pipx install wikiextractor
```

### Option 2: Install system packages

```bash
# Install Python packages via apt
sudo apt install python3-numpy python3-scipy python3-tqdm python3-sklearn

# For wikiextractor, use pip with --break-system-packages (not recommended)
# OR download manually from GitHub
```

### Option 3: Use virtual environment (Cleanest)

```bash
# Install venv support
sudo apt install python3.12-venv

# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

## External Tools

### FastText

```bash
git clone https://github.com/facebookresearch/fastText.git
cd fastText
make
# Binary will be at: fastText/fasttext
```

### VecMap

```bash
git clone https://github.com/artetxem/vecmap.git
# No compilation needed, pure Python
```

## Quick Start (Recommended)

```bash
cd projects/embedding-aligner

# 1. Install venv support
sudo apt install python3.12-venv

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Install FastText
git clone https://github.com/facebookresearch/fastText.git
cd fastText && make && cd ..

# 5. Install VecMap
git clone https://github.com/artetxem/vecmap.git

# 6. Set environment variables
export FASTTEXT_BIN=$(pwd)/fastText/fasttext
export VECMAP_DIR=$(pwd)/vecmap

# 7. Verify setup
python -c "import numpy, scipy, wikiextractor; print('✓ Python packages OK')"
$FASTTEXT_BIN --help | head -n 1
python $VECMAP_DIR/map_embeddings.py --help | head -n 1
```

## Notes

- The virtual environment approach is cleanest and avoids system conflicts
- Remember to activate the venv before running scripts: `source venv/bin/activate`
- FastText and VecMap can be installed anywhere, just set the environment variables
