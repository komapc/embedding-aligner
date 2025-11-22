#!/bin/bash
# Quick test script for translation discovery
# Uses CLEANED results (both Ido and Esperanto)

set -e

cd "$(dirname "$0")"
source venv/bin/activate

# Default test words if none provided
WORDS="${@:-hundo krear obediar refuzar euro britaniana generala saluto}"

echo "═══════════════════════════════════════════════════════════════"
echo "Testing Translation Discovery (CLEANED RESULTS)"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Testing words: $WORDS"
echo ""

python scripts/find_nearest_words.py \
    --ido-embeddings results/bert_aligned_clean_0.60/ido_bert_aligned.npy \
    --ido-vocab models/ido_bert_vocab_clean.txt \
    --epo-embeddings results/bert_aligned_clean_0.60/epo_w2v_aligned.npy \
    --epo-vocab models/esperanto_clean__vocab.txt \
    --words $WORDS \
    --top-k 5

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "✅ Test Complete"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "To test other words:"
echo "  ./test_translations.sh word1 word2 word3"
echo ""
echo "To check discovered pairs file:"
echo "  cat results/bert_aligned_clean_0.60/bert_candidates.json | jq '.hundo'"
echo ""

