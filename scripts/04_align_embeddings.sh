#!/bin/bash
# Align Ido and Esperanto embedding spaces using VecMap

set -e

# Check if VecMap is available
if [ -z "$VECMAP_DIR" ]; then
    if [ -d "vecmap" ]; then
        VECMAP_DIR="./vecmap"
    else
        echo "Error: VecMap not found. Please set VECMAP_DIR or install VecMap."
        echo "See SETUP.md for installation instructions."
        exit 1
    fi
fi

echo "Using VecMap: $VECMAP_DIR"

# Paths
DICT_DIR="data/dictionaries"
MODELS_DIR="models"

# Check if seed dictionary exists
if [ ! -f "$DICT_DIR/train_45k.txt" ]; then
    echo "Error: Training dictionary not found: $DICT_DIR/train_45k.txt"
    echo "Please prepare seed dictionary first (see SETUP.md)"
    exit 1
fi

echo "=== Aligning Embedding Spaces ==="
python3 "$VECMAP_DIR/map_embeddings.py" \
    --supervised "$DICT_DIR/train_45k.txt" \
    --orthogonal \
    "$MODELS_DIR/ido_vectors.vec" \
    "$MODELS_DIR/epo_vectors.vec" \
    "$MODELS_DIR/ido_aligned.vec" \
    "$MODELS_DIR/epo_aligned.vec"

echo "✓ Alignment complete!"
echo "Aligned Ido vectors: $MODELS_DIR/ido_aligned.vec"
echo "Aligned Esperanto vectors: $MODELS_DIR/epo_aligned.vec"

echo ""
echo "=== Validating Alignment ==="
if [ -f "$DICT_DIR/validation_5k.txt" ]; then
    python3 "$VECMAP_DIR/eval_translation.py" \
        "$MODELS_DIR/ido_aligned.vec" \
        "$MODELS_DIR/epo_aligned.vec" \
        -d "$DICT_DIR/validation_5k.txt" \
        --retrieval csls_knn_10
else
    echo "Warning: Validation dictionary not found: $DICT_DIR/validation_5k.txt"
    echo "Skipping validation step."
fi
