#!/usr/bin/env python3
"""
Quick BERT embedding analysis - just show quality of nearest neighbors.
"""

import numpy as np
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import json

def load_embeddings(npy_path: Path, vocab_path: Path):
    """Load embeddings and vocabulary."""
    print(f"Loading embeddings from {npy_path}")
    embeddings = np.load(npy_path)
    
    print(f"Loading vocabulary from {vocab_path}")
    with open(vocab_path, 'r', encoding='utf-8') as f:
        vocab = [line.strip() for line in f]
    
    word_to_idx = {word: idx for idx, word in enumerate(vocab)}
    
    print(f"✅ Loaded {len(vocab):,} embeddings, shape: {embeddings.shape}")
    return embeddings, vocab, word_to_idx


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """L2 normalize."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / (norms + 1e-8)


def find_nearest(embeddings: np.ndarray, vocab: List[str], word_to_idx: Dict[str, int], query_word: str, top_k: int = 10):
    """Find nearest neighbors to a query word."""
    if query_word not in word_to_idx:
        return None
    
    idx = word_to_idx[query_word]
    query_vec = embeddings[idx]
    
    # Compute all similarities
    sims = np.dot(embeddings, query_vec)
    
    # Get top-k (excluding the query itself)
    top_indices = np.argsort(sims)[::-1][1:top_k+1]
    
    return [(vocab[i], float(sims[i])) for i in top_indices]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--embeddings', type=Path, required=True)
    parser.add_argument('--vocab', type=Path)
    parser.add_argument('--test-words', nargs='+', default=['la', 'hundo', 'manjar', 'bela', 'amo', 'urbo', 'homo', 'aquo', 'vizajar', 'libro'])
    parser.add_argument('--output', type=Path)
    
    args = parser.parse_args()
    
    # Default vocab path
    if not args.vocab:
        args.vocab = args.embeddings.parent / (args.embeddings.stem + '_vocab.txt')
    
    # Load
    emb, vocab, word_to_idx = load_embeddings(args.embeddings, args.vocab)
    
    # Normalize
    print("\nNormalizing embeddings...")
    emb_norm = normalize_embeddings(emb)
    
    # Test words
    print(f"\n{'='*70}")
    print(f"BERT EMBEDDING QUALITY - Nearest Neighbors")
    print(f"{'='*70}\n")
    
    results = {}
    
    for word in args.test_words:
        neighbors = find_nearest(emb_norm, vocab, word_to_idx, word, top_k=10)
        
        if neighbors:
            results[word] = neighbors
            print(f"📖 '{word}':")
            for i, (neighbor, sim) in enumerate(neighbors, 1):
                print(f"   {i:2d}. {neighbor:20s} (similarity: {sim:.4f})")
            print()
        else:
            print(f"❌ '{word}' not in vocabulary\n")
    
    # Save if requested
    if args.output:
        print(f"Saving results to {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print("✅ Saved!")


if __name__ == '__main__':
    main()

