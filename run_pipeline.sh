#!/bin/bash
# Run the complete embedding alignment pipeline

set -e  # Exit on error

echo "=== Embedding Alignment Pipeline ==="
echo ""

# Step 1: Prepare corpora
echo "Step 1: Preparing corpora..."
python3 scripts/01_prepare_corpora.py
echo ""

# Step 2: Train Ido embeddings
echo "Step 2: Training Ido embeddings..."
python3 scripts/02_train_ido_embeddings.py
echo ""

# Step 3: Train Esperanto embeddings
echo "Step 3: Training Esperanto embeddings..."
python3 scripts/03_train_epo_embeddings.py
echo ""

# Step 4: Extract seed dictionary
echo "Step 4: Extracting seed dictionary..."
python3 scripts/04_extract_seed_dict.py
echo ""

# Step 5: Align embeddings
echo "Step 5: Aligning embedding spaces..."
python3 scripts/05_align_embeddings.py
echo ""

# Step 6: Find candidates
echo "Step 6: Finding translation candidates..."
python3 scripts/06_find_candidates.py
echo ""

# Step 7: Validate candidates
echo "Step 7: Validating candidates..."
python3 scripts/07_validate_candidates.py
echo ""

echo "=== Pipeline Complete ==="
echo "Results saved in results/ directory"
