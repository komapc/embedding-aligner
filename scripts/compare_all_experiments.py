#!/usr/bin/env python3
"""
Compare all trained models including experiments.

Usage:
    python3 compare_all_experiments.py <word>
"""

import sys
from pathlib import Path
from gensim.models import FastText, Word2Vec
from gensim.models.callbacks import CallbackAny2Vec


class EpochLogger(CallbackAny2Vec):
    def __init__(self):
        self.epoch = 0
    def on_epoch_end(self, model):
        self.epoch += 1


def load_model(model_path):
    if 'word2vec' in str(model_path) or 'optimized' in str(model_path):
        return Word2Vec.load(str(model_path))
    else:
        return FastText.load(str(model_path))


def compare_all(word: str, models_dir: Path, topn: int = 10):
    models = {
        'FastText (n-grams)': 'ido_fasttext.model',
        'FastText (no n-grams)': 'ido_fasttext_no_ngrams.model',
        'Word2Vec (base)': 'ido_word2vec.model',
        'Optimized: Low min_count': 'ido_optimized_low-mincount.model',
        'Optimized: Large window': 'ido_optimized_large-window.model',
        'Optimized: Aggressive': 'ido_optimized_aggressive.model',
    }
    
    print(f"\n{'='*80}")
    print(f"COMPREHENSIVE MODEL COMPARISON: '{word}'")
    print(f"{'='*80}\n")
    
    results = []
    
    for name, filename in models.items():
        path = models_dir / filename
        if not path.exists():
            continue
        
        try:
            model = load_model(path)
            if word not in model.wv:
                continue
            
            freq = model.wv.get_vecattr(word, 'count')
            similar = model.wv.most_similar(word, topn=topn)
            
            results.append({
                'name': name,
                'vocab_size': len(model.wv),
                'freq': freq,
                'similar': similar
            })
        except:
            continue
    
    # Print results
    for r in results:
        print(f"📊 {r['name']}")
        print(f"   Vocabulary: {r['vocab_size']:,} words | Word frequency: {r['freq']}")
        print(f"   Top {topn} similar:")
        for i, (w, score) in enumerate(r['similar'], 1):
            print(f"      {i:2d}. {w:20s} {score:.4f}")
        print()
    
    # Summary comparison
    if len(results) > 1:
        print(f"\n{'='*80}")
        print("QUICK COMPARISON (Top 3 words only):")
        print(f"{'='*80}\n")
        for r in results:
            top3 = [w for w, s in r['similar'][:3]]
            print(f"{r['name']:30s} → {', '.join(top3)}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 compare_all_experiments.py <word>")
        sys.exit(1)
    
    word = sys.argv[1]
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / 'models'
    
    compare_all(word, models_dir, topn=10)
