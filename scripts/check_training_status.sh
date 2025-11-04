#!/bin/bash
# Check training status of all experiments

cd "$(dirname "$0")/.."

echo "=========================================="
echo "Training Status"
echo "=========================================="
echo ""

experiments=("higher-mincount" "subsampling" "smaller-window" "cbow" "no-proper-nouns" "combined-best")

for exp in "${experiments[@]}"; do
    model_file="models/ido_exp_${exp}.model"
    
    if [ -f "$model_file" ]; then
        size=$(du -h "$model_file" | cut -f1)
        timestamp=$(stat -c %y "$model_file" | cut -d' ' -f1,2 | cut -d'.' -f1)
        echo "✅ $exp: COMPLETE ($size, $timestamp)"
    else
        echo "🔄 $exp: TRAINING..."
    fi
done

echo ""
echo "=========================================="
echo "To compare results once complete:"
echo "  python3 scripts/compare_experiments.py hundo"
echo "=========================================="
