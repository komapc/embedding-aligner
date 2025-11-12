#!/bin/bash
# Check training status for Esperanto embeddings

echo "════════════════════════════════════════════════════════════════"
echo "  ESPERANTO EMBEDDING TRAINING STATUS"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if training process is running
if pgrep -f "train_esperanto_embeddings.py.*esperanto_10pct" > /dev/null; then
    echo "✓ Training process: RUNNING"
    
    # Get process info
    ps aux | grep -E "train_esperanto.*esperanto_10pct" | grep -v grep | \
        awk '{printf "  PID: %s\n  CPU: %s%%\n  Memory: %s%%\n  Time: %s\n", $2, $3, $4, $10}'
    
    echo ""
    echo "⏳ Status: Training in progress..."
    echo "   Expected time: 30-60 minutes total"
    
    # Check for model files
    if [ -f "models/esperanto_10pct.model" ]; then
        echo ""
        echo "✓ Model file detected:"
        ls -lh models/esperanto_10pct.model* | awk '{print "  " $9 " - " $5}'
    else
        echo ""
        echo "  Model will be saved when training completes."
    fi
    
else
    echo "⚠ Training process: NOT RUNNING"
    echo ""
    
    # Check if model exists (training might have completed)
    if [ -f "models/esperanto_10pct.model" ]; then
        echo "✓ Training COMPLETED! Model found:"
        echo ""
        ls -lh models/esperanto_10pct.model* | awk '{print "  " $9 " - " $5}'
        echo ""
        echo "To test the model, run:"
        echo "  cd /home/mark/apertium-dev/projects/embedding-aligner"
        echo "  source venv/bin/activate"
        echo "  python3 scripts/query_nearest_words.py \\"
        echo "    models/esperanto_10pct.model hundo --topn 15"
    else
        echo "✗ Model not found. Training may have failed."
        echo ""
        echo "Check logs or restart training."
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════════"

