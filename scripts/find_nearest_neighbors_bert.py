#!/usr/bin/env python3
"""
Find nearest neighbors in BERT embeddings to discover translations.

This script:
1. Loads fine-tuned BERT embeddings (Ido)
2. Loads Esperanto Word2Vec embeddings
3. Finds nearest Esperanto neighbors for each Ido word
4. Compares with existing alignment results

Usage:
    python scripts/find_nearest_neighbors_bert.py \
        --ido-bert models/ido_bert_embeddings.npy \
        --esperanto-w2v models/esperanto_min3.model \
        --seed-dict data/seed_dictionary.txt \
        --output results/bert_nearest_neighbors.json \
        --top-k 10
"""

import argparse
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from gensim.models import Word2Vec
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_bert_embeddings(npy_path: Path, vocab_path: Path) -> Tuple[np.ndarray, List[str]]:
    """Load BERT embeddings and vocabulary."""
    logger.info(f"Loading BERT embeddings from {npy_path}")
    embeddings = np.load(npy_path)
    
    logger.info(f"Loading vocabulary from {vocab_path}")
    with open(vocab_path, 'r', encoding='utf-8') as f:
        vocab = [line.strip() for line in f]
    
    logger.info(f"Loaded {len(vocab):,} BERT embeddings, shape: {embeddings.shape}")
    return embeddings, vocab


def load_word2vec_embeddings(model_path: Path) -> Tuple[np.ndarray, List[str]]:
    """Load Word2Vec embeddings."""
    logger.info(f"Loading Word2Vec model from {model_path}")
    model = Word2Vec.load(str(model_path))
    
    vocab = list(model.wv.key_to_index.keys())
    embeddings = model.wv.vectors
    
    logger.info(f"Loaded {len(vocab):,} Word2Vec embeddings, shape: {embeddings.shape}")
    return embeddings, vocab


def load_seed_dictionary(seed_path: Path) -> Dict[str, List[str]]:
    """Load seed dictionary (Ido -> Esperanto)."""
    logger.info(f"Loading seed dictionary from {seed_path}")
    
    seed_dict = {}
    with open(seed_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '\t' in line:
                ido, epo = line.strip().split('\t')
                if ido not in seed_dict:
                    seed_dict[ido] = []
                seed_dict[ido].append(epo)
    
    logger.info(f"Loaded {len(seed_dict):,} seed pairs")
    return seed_dict


def normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    """L2 normalize embeddings for cosine similarity."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / (norms + 1e-8)


def find_nearest_neighbors(
    ido_embeddings: np.ndarray,
    ido_vocab: List[str],
    epo_embeddings: np.ndarray,
    epo_vocab: List[str],
    top_k: int = 10,
    batch_size: int = 100
) -> Dict[str, List[Tuple[str, float]]]:
    """
    Find nearest Esperanto neighbors for each Ido word.
    
    Uses batched cosine similarity for efficiency.
    """
    logger.info(f"Finding top {top_k} nearest neighbors for {len(ido_vocab):,} Ido words")
    
    # Normalize embeddings
    logger.info("Normalizing embeddings...")
    ido_norm = normalize_embeddings(ido_embeddings)
    epo_norm = normalize_embeddings(epo_embeddings)
    
    results = {}
    
    # Process in batches for memory efficiency
    for i in tqdm(range(0, len(ido_vocab), batch_size), desc="Finding neighbors"):
        batch_end = min(i + batch_size, len(ido_vocab))
        batch_ido = ido_norm[i:batch_end]
        batch_words = ido_vocab[i:batch_end]
        
        # Compute similarities: [batch_size, epo_vocab_size]
        similarities = np.dot(batch_ido, epo_norm.T)
        
        # Get top-k for each word in batch
        for j, word in enumerate(batch_words):
            # Get top-k indices (highest similarities)
            top_indices = np.argpartition(similarities[j], -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(similarities[j][top_indices])][::-1]
            
            # Store results
            results[word] = [
                (epo_vocab[idx], float(similarities[j][idx]))
                for idx in top_indices
            ]
    
    logger.info(f"Found neighbors for {len(results):,} words")
    return results


def evaluate_on_seed_dictionary(
    nearest_neighbors: Dict[str, List[Tuple[str, float]]],
    seed_dict: Dict[str, List[str]]
) -> Dict[str, float]:
    """
    Evaluate accuracy on seed dictionary.
    
    Metrics:
    - P@1: Precision at rank 1 (top prediction is correct)
    - P@5: Precision at rank 5 (correct answer in top 5)
    - P@10: Precision at rank 10 (correct answer in top 10)
    - MRR: Mean Reciprocal Rank
    """
    logger.info("Evaluating on seed dictionary...")
    
    p1_count = 0
    p5_count = 0
    p10_count = 0
    reciprocal_ranks = []
    evaluated = 0
    
    for ido_word, expected_epo in seed_dict.items():
        if ido_word not in nearest_neighbors:
            continue
        
        evaluated += 1
        neighbors = nearest_neighbors[ido_word]
        predicted_words = [word for word, _ in neighbors]
        
        # Check if any expected translation is in predictions
        found_at = None
        for expected in expected_epo:
            if expected in predicted_words:
                found_at = predicted_words.index(expected) + 1
                break
        
        if found_at:
            reciprocal_ranks.append(1.0 / found_at)
            if found_at == 1:
                p1_count += 1
            if found_at <= 5:
                p5_count += 1
            if found_at <= 10:
                p10_count += 1
        else:
            reciprocal_ranks.append(0.0)
    
    metrics = {
        'evaluated_pairs': evaluated,
        'p@1': p1_count / evaluated if evaluated > 0 else 0.0,
        'p@5': p5_count / evaluated if evaluated > 0 else 0.0,
        'p@10': p10_count / evaluated if evaluated > 0 else 0.0,
        'mrr': np.mean(reciprocal_ranks) if reciprocal_ranks else 0.0
    }
    
    logger.info(f"Evaluated on {evaluated:,} seed pairs")
    logger.info(f"P@1:  {metrics['p@1']:.2%}")
    logger.info(f"P@5:  {metrics['p@5']:.2%}")
    logger.info(f"P@10: {metrics['p@10']:.2%}")
    logger.info(f"MRR:  {metrics['mrr']:.4f}")
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Find nearest neighbors using BERT embeddings")
    parser.add_argument('--ido-bert', type=Path, required=True, help="Ido BERT embeddings (.npy)")
    parser.add_argument('--ido-vocab', type=Path, help="Ido vocabulary file (default: .npy path + _vocab.txt)")
    parser.add_argument('--esperanto-w2v', type=Path, required=True, help="Esperanto Word2Vec model")
    parser.add_argument('--seed-dict', type=Path, required=True, help="Seed dictionary file")
    parser.add_argument('--output', type=Path, required=True, help="Output JSON file")
    parser.add_argument('--top-k', type=int, default=10, help="Number of neighbors to find")
    parser.add_argument('--sample', type=int, help="Only process first N Ido words (for testing)")
    
    args = parser.parse_args()
    
    # Default vocab path
    if not args.ido_vocab:
        args.ido_vocab = args.ido_bert.parent / (args.ido_bert.stem + '_vocab.txt')
    
    # Load embeddings
    ido_embeddings, ido_vocab = load_bert_embeddings(args.ido_bert, args.ido_vocab)
    epo_embeddings, epo_vocab = load_word2vec_embeddings(args.esperanto_w2v)
    
    # Load seed dictionary
    seed_dict = load_seed_dictionary(args.seed_dict)
    
    # Sample if requested
    if args.sample:
        logger.info(f"⚠️  Sampling first {args.sample:,} Ido words")
        ido_embeddings = ido_embeddings[:args.sample]
        ido_vocab = ido_vocab[:args.sample]
    
    # Find nearest neighbors
    nearest_neighbors = find_nearest_neighbors(
        ido_embeddings,
        ido_vocab,
        epo_embeddings,
        epo_vocab,
        top_k=args.top_k
    )
    
    # Evaluate on seed dictionary
    metrics = evaluate_on_seed_dictionary(nearest_neighbors, seed_dict)
    
    # Save results
    logger.info(f"Saving results to {args.output}")
    output_data = {
        'config': {
            'ido_bert': str(args.ido_bert),
            'esperanto_w2v': str(args.esperanto_w2v),
            'seed_dict': str(args.seed_dict),
            'top_k': args.top_k,
            'ido_vocab_size': len(ido_vocab),
            'epo_vocab_size': len(epo_vocab)
        },
        'metrics': metrics,
        'nearest_neighbors': nearest_neighbors
    }
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info("✅ Done!")
    logger.info(f"Results saved to {args.output}")


if __name__ == '__main__':
    main()

