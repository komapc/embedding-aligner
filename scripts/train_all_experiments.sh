#!/bin/bash
# Train all experimental models

cd "$(dirname "$0")/.."

echo "Starting all experiments..."
echo "This will take approximately 3-4 hours total"
echo ""

# Activate virtual environment
source venv/bin/activate

# Train each experiment
experiments=("higher-mincount" "subsampling" "smaller-window" "cbow" "no-proper-nouns" "combined-best")

for exp in "${experiments[@]}"; do
    echo "=========================================="
    echo "Training: $exp"
    echo "=========================================="
    python3 scripts/train_experiments.py --experiment "$exp"
    echo ""
done

echo "All experiments completed!"
echo "Compare results with: python3 scripts/compare_experiments.py hundo"
