#!/bin/bash
# Run alignment with BOTH Ido and Esperanto cleaned embeddings

set -e

THRESHOLD=${1:-0.60}

echo "═══════════════════════════════════════════════════════════"
echo "Running Alignment with BOTH Sides Cleaned"
echo "═══════════════════════════════════════════════════════════"
echo "Threshold: $THRESHOLD"
echo ""

source venv/bin/activate

python scripts/align_bert_with_esperanto.py \
    --ido-bert models/ido_bert_clean_300d.npy \
    --ido-vocab models/ido_bert_vocab_clean.txt \
    --epo-w2v models/esperanto_clean__300d.npy \
    --epo-vocab models/esperanto_clean__vocab.txt \
    --seed-dict data/seed_dictionary.txt \
    --output-dir results/bert_aligned_clean_${THRESHOLD}/ \
    --threshold ${THRESHOLD} \
    --iterations 10 \
    --alpha 0.5

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ ALIGNMENT COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Results saved to: results/bert_aligned_clean_${THRESHOLD}/"
echo ""

