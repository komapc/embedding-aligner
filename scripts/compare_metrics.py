#!/usr/bin/env python3
"""
Compare different similarity metrics for finding nearest words.

Metrics tested:
1. Cosine similarity (standard)
2. Dot product
3. Euclidean distance (inverted)
4. Frequency-weighted cosine

Usage:
    python3 compare_metrics.py <word> [--model path]
"""

import sys
import argparse
import numpy as np
from pathlib import Path
from gensim.models import Word2Vec, FastText
from gensim.models.callbacks import CallbackAny2Vec


class EpochLogger(CallbackAny2Vec):
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


def cosine_similarity(vec1, vec2):
    """Standard cosine similarity."""
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    return dot / (norm1 * norm2)


def dot_product_similarity(vec1, vec2):
    """Raw dot product (magnitude-sensitive)."""
    return np.dot(vec1, vec2)


def euclidean_similarity(vec1, vec2):
    """Inverted Euclidean distance (closer = higher score)."""
    distance = np.linalg.norm(vec1 - vec2)
    return 1.0 / (1.0 + distance)  # Invert so higher = more similar


def frequency_weighted_cosine(vec1, vec2, freq1, freq2):
    """Cosine similarity weighted by word frequencies."""
    cos_sim = cosine_similarity(vec1, vec2)
    # Downweight if frequency difference is large
    freq_ratio = min(freq1, freq2) / max(freq1, freq2)
    return cos_sim * (0.5 + 0.5 * freq_ratio)


def find_similar_with_metric(model, word, metric_name, topn=10):
    """Find similar words using specified metric."""
    if word not in model.wv:
        return None
    
    query_vec = model.wv[word]
    query_freq = model.wv.get_vecattr(word, 'count')
    
    similarities = []
    
    for other_word in model.wv.index_to_key:
        if other_word == word:
            continue
        
        other_vec = model.wv[other_word]
        other_freq = model.wv.get_vecattr(other_word, 'count')
        
        if metric_name == 'cosine':
            sim = cosine_similarity(query_vec, other_vec)
        elif metric_name == 'dot_product':
            sim = dot_product_similarity(query_vec, other_vec)
        elif metric_name == 'euclidean':
            sim = euclidean_similarity(query_vec, other_vec)
        elif metric_name == 'freq_weighted':
            sim = frequency_weighted_cosine(query_vec, other_vec, query_freq, other_freq)
        else:
            raise ValueError(f"Unknown metric: {metric_name}")
        
        similarities.append((other_word, sim, other_freq))
    
    # Sort by similarity
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:topn]


def compare_all_metrics(model, word, topn=10):
    """Compare all metrics for a given word."""
    
    metrics = {
        'Cosine Similarity (standard)': 'cosine',
        'Dot Product': 'dot_product',
        'Euclidean Distance': 'euclidean',
        'Frequency-Weighted Cosine': 'freq_weighted'
    }
    
    print(f"\n{'='*70}")
    print(f"Comparing similarity metrics for: '{word}'")
    print(f"Model: {model}")
    print(f"{'='*70}\n")
    
    if word not in model.wv:
        print(f"❌ Word '{word}' not in vocabulary")
        return
    
    word_freq = model.wv.get_vecattr(word, 'count')
    print(f"Word frequency: {word_freq}")
    print(f"Vocabulary size: {len(model.wv):,} words\n")
    
    for metric_name, metric_key in metrics.items():
        print(f"📊 {metric_name}")
        print(f"   Top {topn} similar words:")
        
        results = find_similar_with_metric(model, word, metric_key, topn)
        
        if results:
            for i, (sim_word, score, freq) in enumerate(results, 1):
                print(f"      {i:2d}. {sim_word:20s} {score:.4f}  (freq: {freq})")
        
        print()


def main():
    parser = argparse.ArgumentParser(
        description='Compare different similarity metrics'
    )
    parser.add_argument('word', help='Word to query')
    parser.add_argument('--model', default='models/ido_optimized_aggressive.model',
                       help='Path to model file')
    parser.add_argument('--topn', type=int, default=10,
                       help='Number of similar words (default: 10)')
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    model_path = base_dir / args.model
    
    if not model_path.exists():
        print(f"❌ Model not found at {model_path}")
        sys.exit(1)
    
    print(f"Loading model from {model_path}...")
    model = load_model(model_path)
    
    compare_all_metrics(model, args.word, args.topn)


if __name__ == '__main__':
    main()
