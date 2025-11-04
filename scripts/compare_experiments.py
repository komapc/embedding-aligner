#!/usr/bin/env python3
"""
Compare results from all experimental models.

Usage:
    python3 compare_experiments.py <word>
"""

import sys
from pathlib import Path
from gensim.models import Word2Vec


EXPERIMENTS = [
    ('baseline', 'models/ido_optimized_aggressive.model', 'Current baseline (min_count=5, window=10)'),
    ('higher-mincount', 'models/ido_exp_higher-mincount.model', 'min_count=20'),
    ('subsampling', 'models/ido_exp_subsampling.model', 'sample=1e-5'),
    ('smaller-window', 'models/ido_exp_smaller-window.model', 'window=5'),
    ('cbow', 'models/ido_exp_cbow.model', 'CBOW instead of Skip-gram'),
    ('no-proper-nouns', 'models/ido_exp_no-proper-nouns.model', 'Filter capitalized words'),
    ('combined-best', 'models/ido_exp_combined-best.model', 'Best settings combined'),
]


def load_model(model_path: Path):
    """Load model if it exists."""
    if not model_path.exists():
        return None
    return Word2Vec.load(str(model_path))


def compare_all(word: str, topn: int = 10):
    """Compare word across all experiments."""
    base_dir = Path(__file__).parent.parent
    
    print(f"\n{'='*100}")
    print(f"Comparing embeddings for: '{word}'")
    print(f"{'='*100}\n")
    
    for exp_name, model_file, description in EXPERIMENTS:
        model_path = base_dir / model_file
        model = load_model(model_path)
        
        if model is None:
            print(f"❌ {exp_name:20s} - Model not found")
            continue
        
        if word not in model.wv:
            print(f"❌ {exp_name:20s} - Word not in vocabulary")
            continue
        
        vocab_size = len(model.wv)
        word_freq = model.wv.get_vecattr(word, 'count')
        
        print(f"📊 {exp_name:20s} (vocab: {vocab_size:,}, freq: {word_freq})")
        print(f"   {description}")
        
        similar = model.wv.most_similar(word, topn=topn)
        
        for i, (sim_word, score) in enumerate(similar, 1):
            freq = model.wv.get_vecattr(sim_word, 'count')
            print(f"      {i:2d}. {sim_word:20s} {score:.4f}  (freq: {freq})")
        
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 compare_experiments.py <word> [topn]")
        print("\nExample: python3 compare_experiments.py hundo")
        return 1
    
    word = sys.argv[1]
    topn = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    compare_all(word, topn)
    
    return 0


if __name__ == '__main__':
    exit(main())
