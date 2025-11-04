#!/usr/bin/env python3
"""
Compare different embedding models on the same test words.

Usage:
    python3 compare_models.py <word>
"""

import sys
import argparse
from pathlib import Path
from gensim.models import FastText, Word2Vec
from gensim.models.callbacks import CallbackAny2Vec


class EpochLogger(CallbackAny2Vec):
    """Callback needed for model loading."""
    def __init__(self):
        self.epoch = 0
    def on_epoch_end(self, model):
        self.epoch += 1


def load_model(model_path: Path):
    """Load any model type."""
    if 'word2vec' in str(model_path):
        return Word2Vec.load(str(model_path))
    else:
        return FastText.load(str(model_path))


def compare_models(word: str, models_dir: Path, topn: int = 10):
    """Compare all available models for a given word."""
    
    model_files = {
        'FastText (with n-grams)': 'ido_fasttext.model',
        'FastText (no n-grams)': 'ido_fasttext_no_ngrams.model',
        'Word2Vec': 'ido_word2vec.model',
        '🏆 Optimized Aggressive': 'ido_optimized_aggressive.model'
    }
    
    print(f"\n{'='*70}")
    print(f"Comparing models for word: '{word}'")
    print(f"{'='*70}\n")
    
    for model_name, model_file in model_files.items():
        model_path = models_dir / model_file
        
        if not model_path.exists():
            print(f"⏭️  {model_name}: Model not found")
            continue
        
        try:
            print(f"📊 {model_name}")
            print(f"   Model: {model_file}")
            
            model = load_model(model_path)
            
            if word not in model.wv:
                print(f"   ⚠️  Word '{word}' not in vocabulary")
                print()
                continue
            
            freq = model.wv.get_vecattr(word, 'count')
            print(f"   Vocabulary: {len(model.wv):,} words")
            print(f"   Word frequency: {freq}")
            print(f"   Top {topn} similar words:")
            
            similar = model.wv.most_similar(word, topn=topn)
            for i, (sim_word, score) in enumerate(similar, 1):
                sim_freq = model.wv.get_vecattr(sim_word, 'count')
                print(f"      {i:2d}. {sim_word:20s} {score:.4f}  (freq: {sim_freq})")
            
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()


def main():
    parser = argparse.ArgumentParser(
        description='Compare different embedding models'
    )
    parser.add_argument('word', help='Word to query')
    parser.add_argument('--topn', type=int, default=10, 
                       help='Number of similar words (default: 10)')
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / 'models'
    
    if not models_dir.exists():
        print(f"❌ Models directory not found at {models_dir}")
        sys.exit(1)
    
    compare_models(args.word, models_dir, args.topn)


if __name__ == '__main__':
    main()
