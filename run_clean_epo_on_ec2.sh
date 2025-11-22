#!/bin/bash
# Clean Esperanto embeddings on EC2 (CPU instance - no GPU needed)

set -e

EC2_HOST="ubuntu@54.220.110.151"

echo "═══════════════════════════════════════════════════════════"
echo "Cleaning Esperanto Embeddings on EC2"
echo "═══════════════════════════════════════════════════════════"
echo "EC2 Host: $EC2_HOST"
echo ""

# Check if instance is reachable
echo "[1/6] Checking EC2 instance..."
if ! timeout 5 ssh -o ConnectTimeout=5 "$EC2_HOST" "echo 'Instance is up'" 2>/dev/null; then
    echo "❌ EC2 instance not reachable"
    echo ""
    echo "Start the instance with:"
    echo "  aws ec2 start-instances --instance-ids i-YOUR_INSTANCE_ID"
    echo ""
    exit 1
fi
echo "✅ Instance is reachable"

# Create directories
echo ""
echo "[2/6] Setting up directories on EC2..."
ssh "$EC2_HOST" "mkdir -p ~/embedding-aligner/{models,scripts}"

# Transfer files
echo ""
echo "[3/6] Transferring files to EC2..."
echo "  - Esperanto Word2Vec model (1.7 GB - this will take a few minutes)"
scp models/esperanto_min3.model "$EC2_HOST:~/embedding-aligner/models/" || {
    echo "⚠️  Model file not found locally or already on EC2"
}
scp models/esperanto_min3.model.wv.vectors.npy "$EC2_HOST:~/embedding-aligner/models/" || {
    echo "⚠️  Vector file not found locally or already on EC2"
}
scp models/esperanto_min3.model.syn1neg.npy "$EC2_HOST:~/embedding-aligner/models/" || {
    echo "⚠️  Syn1neg file not found locally or already on EC2"
}

echo "  - Cleaning script"
scp scripts/clean_esperanto_embeddings.py "$EC2_HOST:~/embedding-aligner/scripts/"

# Setup Python environment
echo ""
echo "[4/6] Setting up Python environment on EC2..."
ssh "$EC2_HOST" << 'EOF'
cd ~/embedding-aligner

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q --upgrade pip
pip install -q numpy gensim

echo "✅ Environment ready"
EOF

# Run cleaning
echo ""
echo "[5/6] Running cleaning script..."
echo "This will take 5-10 minutes..."
ssh "$EC2_HOST" << 'EOF'
cd ~/embedding-aligner
source venv/bin/activate

python3 scripts/clean_esperanto_embeddings.py \
    --model models/esperanto_min3.model \
    --output-prefix models/esperanto_clean_

echo ""
echo "✅ Cleaning complete!"
ls -lh models/esperanto_clean_*
EOF

# Pull results
echo ""
echo "[6/6] Pulling cleaned embeddings back to local machine..."
mkdir -p models/

scp "$EC2_HOST:~/embedding-aligner/models/esperanto_clean_300d.npy" \
    models/

scp "$EC2_HOST:~/embedding-aligner/models/esperanto_clean_vocab.txt" \
    models/

scp "$EC2_HOST:~/embedding-aligner/models/esperanto_clean_stats.json" \
    models/

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "✅ CLEANING COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Results saved to:"
echo "  • models/esperanto_clean_300d.npy"
echo "  • models/esperanto_clean_vocab.txt"
echo "  • models/esperanto_clean_stats.json"
echo ""
echo "Next step: Re-run alignment with both sides cleaned"
echo ""
echo "  ./run_alignment_both_clean.sh 0.60"
echo ""

