#!/bin/bash
# Train FastText embeddings for Ido and Esperanto

set -e

# Check if FastText is available
if [ -z "$FASTTEXT_BIN" ]; then
    if [ -f "fastText/fasttext" ]; then
        FASTTEXT_BIN="./fastText/fasttext"
    else
        echo "Error: FastText not found. Please set FASTTEXT_BIN or install FastText."
        echo "See SETUP.md for installation instructions."
        exit 1
    fi
fi

echo "Using FastText: $FASTTEXT_BIN"

# Paths
PROCESSED_DIR="data/processed"
MODELS_DIR="models"
mkdir -p "$MODELS_DIR"

# Training parameters
DIM=300
WS=5
EPOCH=5
MIN_COUNT=5
NEG=10
THREAD=8

echo "=== Training Ido Embeddings ==="
$FASTTEXT_BIN skipgram \
    -input "$PROCESSED_DIR/ido_corpus.txt" \
    -output "$MODELS_DIR/ido_vectors" \
    -dim $DIM \
    -ws $WS \
    -epoch $EPOCH \
    -minCount $MIN_COUNT \
    -neg $NEG \
    -thread $THREAD

echo "✓ Ido embeddings trained: $MODELS_DIR/ido_vectors.vec"

echo ""
echo "=== Training Esperanto Embeddings ==="
$FASTTEXT_BIN skipgram \
    -input "$PROCESSED_DIR/epo_corpus.txt" \
    -output "$MODELS_DIR/epo_vectors" \
    -dim $DIM \
    -ws $WS \
    -epoch $EPOCH \
    -minCount $MIN_COUNT \
    -neg $NEG \
    -thread $THREAD

echo "✓ Esperanto embeddings trained: $MODELS_DIR/epo_vectors.vec"

echo ""
echo "=== Training Complete ==="
echo "Ido vectors: $MODELS_DIR/ido_vectors.vec"
echo "Esperanto vectors: $MODELS_DIR/epo_vectors.vec"
