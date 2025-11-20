#!/usr/bin/env python3
"""
Analyze BERT embeddings quality and compare with Word2Vec.

This script:
1. Loads BERT embeddings
2. Finds semantically similar words within Ido
3. Compares with seed dictionary for quality assessment
4. Projects to 300d for comparison with Word2Vec

Usage:
    python scripts/analyze_bert_embeddings.py \
        --ido-bert models/ido_bert_embeddings.npy \
        --ido-w2v models/ido_combined_ACTUAL_min3.model \
        --seed-dict data/seed_dictionary.txt \
        --output results/bert_analysis.json
"""

import argparse
import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
from gensim.models import Word2Vec
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_bert_embeddings(npy_path: Path, vocab_path: Path) -> Tuple[np.ndarray, List[str], Dict[str, int]]:
    """Load BERT embeddings and vocabulary."""
    logger.info(f"Loading BERT embeddings from {npy_path}")
    embeddings = np.load(npy_path)
    
    logger.info(f"Loading vocabulary from {vocab_path}")
    with open(vocab_path, 'r', encoding='utf-8') as f:
        vocab = [line.strip() for line in f]
    
    word_to_idx = {word: idx for idx, word in enumerate(vocab)}
    
    logger.info(f"Loaded {len(vocab):,} BERT embeddings, shape: {embeddings.shape}")
    return embeddings, vocab, word_to_idx


def load_word2vec_model(model_path: Path) -> Tuple[np.ndarray, List[str], Dict[str, int]]:
    """Load Word2Vec model."""
    logger.info(f"Loading Word2Vec model from {model_path}")
    model = Word2Vec.load(str(model_path))
    
    vocab = list(model.wv.key_to_index.keys())
    embeddings = model.wv.vectors
    word_to_idx = model.wv.key_to_index
    
    logger.info(f"Loaded {len(vocab):,} Word2Vec embeddings, shape: {embeddings.shape}")
    return embeddings, vocab, word_to_idx


def load_seed_dictionary(seed_path: Path) -> Dict[str, List[str]]:
    """Load seed dictionary."""
    logger.info(f"Loading seed dictionary from {seed_path}")
    
    seed_dict = defaultdict(list)
    with open(seed_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '\t' in line:
                ido, epo = line.split('\t', 1)
                seed_dict[ido].append(epo)
    
    logger.info(f"Loaded {len(seed_dict):,} Ido words with seed translations")
    return dict(seed_dict)


def find_nearest_words(
    embeddings: np.ndarray,
    vocab: List[str],
    query_word: str,
    word_to_idx: Dict[str, int],
    top_k: int = 10
) -> List[Tuple[str, float]]:
    """Find k nearest words to query word."""
    if query_word not in word_to_idx:
        return []
    
    query_idx = word_to_idx[query_word]
    query_vec = embeddings[query_idx].reshape(1, -1)
    
    # Normalize
    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-8)
    emb_norm = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-8)
    
    # Compute similarities
    similarities = np.dot(emb_norm, query_norm.T).flatten()
    
    # Get top-k (excluding the query word itself)
    top_indices = np.argsort(similarities)[::-1][1:top_k+1]
    
    return [(vocab[idx], float(similarities[idx])) for idx in top_indices]


def analyze_seed_coverage(
    bert_embeddings: np.ndarray,
    bert_vocab: List[str],
    bert_word_to_idx: Dict[str, int],
    w2v_embeddings: np.ndarray,
    w2v_vocab: List[str],
    w2v_word_to_idx: Dict[str, int],
    seed_dict: Dict[str, List[str]]
) -> Dict:
    """Analyze how well embeddings cover seed dictionary words."""
    
    bert_coverage = sum(1 for word in seed_dict if word in bert_word_to_idx)
    w2v_coverage = sum(1 for word in seed_dict if word in w2v_word_to_idx)
    
    logger.info(f"BERT covers {bert_coverage}/{len(seed_dict)} seed words ({bert_coverage/len(seed_dict):.1%})")
    logger.info(f"W2V covers {w2v_coverage}/{len(seed_dict)} seed words ({w2v_coverage/len(seed_dict):.1%})")
    
    return {
        'total_seed_words': len(seed_dict),
        'bert_coverage': bert_coverage,
        'w2v_coverage': w2v_coverage,
        'bert_coverage_pct': bert_coverage / len(seed_dict),
        'w2v_coverage_pct': w2v_coverage / len(seed_dict)
    }


def compare_nearest_neighbors(
    query_words: List[str],
    bert_embeddings: np.ndarray,
    bert_vocab: List[str],
    bert_word_to_idx: Dict[str, int],
    w2v_embeddings: np.ndarray,
    w2v_vocab: List[str],
    w2v_word_to_idx: Dict[str, int],
    top_k: int = 10
) -> Dict:
    """Compare nearest neighbors between BERT and Word2Vec."""
    
    logger.info(f"Comparing nearest neighbors for {len(query_words)} words")
    
    comparisons = {}
    
    for word in query_words:
        bert_neighbors = find_nearest_words(
            bert_embeddings, bert_vocab, word, bert_word_to_idx, top_k
        )
        w2v_neighbors = find_nearest_words(
            w2v_embeddings, w2v_vocab, word, w2v_word_to_idx, top_k
        )
        
        if bert_neighbors and w2v_neighbors:
            comparisons[word] = {
                'bert': bert_neighbors,
                'word2vec': w2v_neighbors,
                'overlap': len(set(w for w, _ in bert_neighbors) & set(w for w, _ in w2v_neighbors))
            }
    
    logger.info(f"Compared {len(comparisons)} words")
    
    # Calculate average overlap
    avg_overlap = np.mean([c['overlap'] for c in comparisons.values()]) if comparisons else 0
    logger.info(f"Average neighbor overlap: {avg_overlap:.2f}/{top_k}")
    
    return comparisons


def project_to_300d(embeddings: np.ndarray) -> np.ndarray:
    """Project BERT embeddings from 768d to 300d using PCA."""
    logger.info("Projecting BERT embeddings from 768d to 300d using PCA...")
    
    pca = PCA(n_components=300, random_state=42)
    projected = pca.fit_transform(embeddings)
    
    explained_var = np.sum(pca.explained_variance_ratio_)
    logger.info(f"PCA explained variance: {explained_var:.2%}")
    
    return projected


def main():
    parser = argparse.ArgumentParser(description="Analyze BERT embeddings quality")
    parser.add_argument('--ido-bert', type=Path, required=True, help="Ido BERT embeddings (.npy)")
    parser.add_argument('--ido-vocab', type=Path, help="Ido vocabulary file")
    parser.add_argument('--ido-w2v', type=Path, required=True, help="Ido Word2Vec model")
    parser.add_argument('--seed-dict', type=Path, required=True, help="Seed dictionary")
    parser.add_argument('--output', type=Path, required=True, help="Output JSON file")
    parser.add_argument('--sample-words', type=int, default=50, help="Number of words to compare")
    
    args = parser.parse_args()
    
    # Default vocab path
    if not args.ido_vocab:
        args.ido_vocab = args.ido_bert.parent / (args.ido_bert.stem + '_vocab.txt')
    
    # Load embeddings
    bert_emb, bert_vocab, bert_idx = load_bert_embeddings(args.ido_bert, args.ido_vocab)
    w2v_emb, w2v_vocab, w2v_idx = load_word2vec_model(args.ido_w2v)
    
    # Load seed dictionary
    seed_dict = load_seed_dictionary(args.seed_dict)
    
    # Analyze seed coverage
    logger.info("\n" + "="*60)
    logger.info("SEED DICTIONARY COVERAGE")
    logger.info("="*60)
    coverage_stats = analyze_seed_coverage(
        bert_emb, bert_vocab, bert_idx,
        w2v_emb, w2v_vocab, w2v_idx,
        seed_dict
    )
    
    # Select sample words for comparison (prefer seed words)
    seed_words_in_both = [
        w for w in seed_dict.keys()
        if w in bert_idx and w in w2v_idx
    ]
    sample_words = seed_words_in_both[:args.sample_words]
    
    if len(sample_words) < args.sample_words:
        # Add more common words
        common_words = [
            w for w in bert_vocab[:1000]
            if w in w2v_idx and w not in sample_words
        ]
        sample_words.extend(common_words[:args.sample_words - len(sample_words)])
    
    logger.info(f"Selected {len(sample_words)} sample words for comparison")
    
    # Compare nearest neighbors
    logger.info("\n" + "="*60)
    logger.info("NEAREST NEIGHBOR COMPARISON (BERT vs Word2Vec)")
    logger.info("="*60)
    comparisons = compare_nearest_neighbors(
        sample_words,
        bert_emb, bert_vocab, bert_idx,
        w2v_emb, w2v_vocab, w2v_idx,
        top_k=10
    )
    
    # Show some examples
    logger.info("\n" + "="*60)
    logger.info("EXAMPLES (First 5 words)")
    logger.info("="*60)
    for i, (word, comp) in enumerate(list(comparisons.items())[:5]):
        logger.info(f"\n{i+1}. '{word}':")
        logger.info(f"   BERT neighbors: {', '.join(w for w, _ in comp['bert'][:5])}")
        logger.info(f"   W2V neighbors:  {', '.join(w for w, _ in comp['word2vec'][:5])}")
        logger.info(f"   Overlap: {comp['overlap']}/10")
        if word in seed_dict:
            logger.info(f"   Expected (seed): {', '.join(seed_dict[word])}")
    
    # Project BERT to 300d
    logger.info("\n" + "="*60)
    logger.info("DIMENSIONALITY REDUCTION")
    logger.info("="*60)
    bert_300d = project_to_300d(bert_emb)
    
    # Save projected embeddings
    projected_path = args.ido_bert.parent / 'ido_bert_embeddings_300d.npy'
    logger.info(f"Saving 300d projections to {projected_path}")
    np.save(projected_path, bert_300d)
    
    # Save results
    logger.info(f"\nSaving analysis to {args.output}")
    results = {
        'config': {
            'ido_bert': str(args.ido_bert),
            'ido_w2v': str(args.ido_w2v),
            'seed_dict': str(args.seed_dict),
            'bert_dims': bert_emb.shape[1],
            'w2v_dims': w2v_emb.shape[1]
        },
        'coverage': coverage_stats,
        'comparisons': comparisons,
        'sample_words': sample_words,
        'projected_embeddings': str(projected_path)
    }
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info("✅ Done!")


if __name__ == '__main__':
    main()

