#!/usr/bin/env python3
"""
Align cleaned BERT embeddings with Esperanto Word2Vec using retrofitting.

This script:
1. Loads clean BERT Ido embeddings (300d)
2. Loads Esperanto Word2Vec embeddings (300d)
3. Applies retrofitting with seed dictionary
4. Finds translation candidates

Usage:
    python scripts/align_bert_with_esperanto.py \
        --ido-bert models/ido_bert_clean_300d.npy \
        --ido-vocab models/ido_bert_vocab_clean.txt \
        --epo-w2v models/esperanto_min3.model \
        --seed-dict data/seed_dictionary.txt \
        --output-dir results/bert_aligned/
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
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_bert_embeddings(npy_path: Path, vocab_path: Path):
    """Load BERT embeddings."""
    logger.info(f"Loading BERT embeddings from {npy_path}")
    embeddings = np.load(npy_path)
    
    with open(vocab_path, 'r', encoding='utf-8') as f:
        vocab = [line.strip() for line in f]
    
    word_to_idx = {word: idx for idx, word in enumerate(vocab)}
    
    logger.info(f"Loaded {len(vocab):,} BERT embeddings, shape: {embeddings.shape}")
    return embeddings, vocab, word_to_idx


def load_word2vec_model(model_path: Path):
    """Load Word2Vec model."""
    logger.info(f"Loading Word2Vec model from {model_path}")
    model = Word2Vec.load(str(model_path))
    
    vocab = list(model.wv.key_to_index.keys())
    embeddings = model.wv.vectors
    word_to_idx = model.wv.key_to_index
    
    logger.info(f"Loaded {len(vocab):,} Word2Vec embeddings, shape: {embeddings.shape}")
    return embeddings, vocab, word_to_idx


def load_seed_dictionary(seed_path: Path, ido_vocab: set, epo_vocab: set):
    """Load seed dictionary (space-separated format)."""
    logger.info(f"Loading seed dictionary from {seed_path}")
    
    seed_pairs = []
    skipped = 0
    
    with open(seed_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                ido_word = parts[0].lower()
                epo_word = parts[1].lower()
                
                # Only keep if both words exist in vocabularies
                if ido_word in ido_vocab and epo_word in epo_vocab:
                    seed_pairs.append((ido_word, epo_word))
                else:
                    skipped += 1
    
    logger.info(f"Loaded {len(seed_pairs):,} seed pairs (skipped {skipped:,})")
    return seed_pairs


def retrofit_embeddings(
    ido_emb: np.ndarray,
    ido_vocab: List[str],
    ido_idx: Dict[str, int],
    epo_emb: np.ndarray,
    epo_vocab: List[str],
    epo_idx: Dict[str, int],
    seed_pairs: List[Tuple[str, str]],
    iterations: int = 10,
    alpha: float = 0.5
):
    """
    Retrofit embeddings using seed dictionary.
    
    For each iteration:
    - Pull Ido word closer to its Esperanto translation
    - Pull Esperanto word closer to its Ido translation
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"RETROFITTING ALIGNMENT")
    logger.info(f"{'='*60}")
    logger.info(f"Iterations: {iterations}")
    logger.info(f"Alpha: {alpha}")
    logger.info(f"Seed pairs: {len(seed_pairs):,}")
    
    # Copy embeddings
    ido_aligned = ido_emb.copy()
    epo_aligned = epo_emb.copy()
    
    # Track progress
    initial_sim = compute_seed_similarity(ido_aligned, ido_idx, epo_aligned, epo_idx, seed_pairs)
    logger.info(f"Initial mean similarity: {initial_sim:.4f}")
    
    # Retrofitting iterations
    for iteration in range(iterations):
        start_time = time.time()
        
        # Update Ido embeddings
        for ido_word, epo_word in seed_pairs:
            if ido_word in ido_idx and epo_word in epo_idx:
                ido_i = ido_idx[ido_word]
                epo_i = epo_idx[epo_word]
                
                # Pull Ido word closer to Esperanto translation
                ido_aligned[ido_i] = (1 - alpha) * ido_aligned[ido_i] + alpha * epo_aligned[epo_i]
        
        # Update Esperanto embeddings
        for ido_word, epo_word in seed_pairs:
            if ido_word in ido_idx and epo_word in epo_idx:
                ido_i = ido_idx[ido_word]
                epo_i = epo_idx[epo_word]
                
                # Pull Esperanto word closer to Ido translation
                epo_aligned[epo_i] = (1 - alpha) * epo_aligned[epo_i] + alpha * ido_aligned[ido_i]
        
        # Normalize
        ido_aligned = ido_aligned / (np.linalg.norm(ido_aligned, axis=1, keepdims=True) + 1e-8)
        epo_aligned = epo_aligned / (np.linalg.norm(epo_aligned, axis=1, keepdims=True) + 1e-8)
        
        # Check progress
        current_sim = compute_seed_similarity(ido_aligned, ido_idx, epo_aligned, epo_idx, seed_pairs)
        elapsed = time.time() - start_time
        
        logger.info(f"Iteration {iteration+1}/{iterations}: similarity={current_sim:.4f} ({elapsed:.2f}s)")
    
    final_sim = compute_seed_similarity(ido_aligned, ido_idx, epo_aligned, epo_idx, seed_pairs)
    improvement = final_sim - initial_sim
    
    logger.info(f"\n✅ Retrofitting complete!")
    logger.info(f"Initial similarity: {initial_sim:.4f}")
    logger.info(f"Final similarity: {final_sim:.4f}")
    logger.info(f"Improvement: +{improvement:.4f} ({improvement/initial_sim*100:+.1f}%)")
    
    return ido_aligned, epo_aligned


def compute_seed_similarity(ido_emb, ido_idx, epo_emb, epo_idx, seed_pairs):
    """Compute mean cosine similarity for seed pairs."""
    similarities = []
    
    for ido_word, epo_word in seed_pairs:
        if ido_word in ido_idx and epo_word in epo_idx:
            ido_vec = ido_emb[ido_idx[ido_word]]
            epo_vec = epo_emb[epo_idx[epo_word]]
            sim = np.dot(ido_vec, epo_vec)
            similarities.append(sim)
    
    return np.mean(similarities) if similarities else 0.0


def find_translation_candidates(
    ido_emb: np.ndarray,
    ido_vocab: List[str],
    epo_emb: np.ndarray,
    epo_vocab: List[str],
    threshold: float = 0.50,
    top_k: int = 5,
    batch_size: int = 100
):
    """Find translation candidates using aligned embeddings."""
    logger.info(f"\n{'='*60}")
    logger.info(f"FINDING TRANSLATION CANDIDATES")
    logger.info(f"{'='*60}")
    logger.info(f"Threshold: {threshold}")
    logger.info(f"Top-k per word: {top_k}")
    
    candidates = {}
    total_pairs = 0
    
    # Normalize embeddings
    ido_norm = ido_emb / (np.linalg.norm(ido_emb, axis=1, keepdims=True) + 1e-8)
    epo_norm = epo_emb / (np.linalg.norm(epo_emb, axis=1, keepdims=True) + 1e-8)
    
    # Process in batches
    for i in tqdm(range(0, len(ido_vocab), batch_size), desc="Finding candidates"):
        batch_end = min(i + batch_size, len(ido_vocab))
        batch_ido = ido_norm[i:batch_end]
        batch_words = ido_vocab[i:batch_end]
        
        # Compute similarities
        similarities = np.dot(batch_ido, epo_norm.T)
        
        # Get top-k for each word
        for j, word in enumerate(batch_words):
            # Get indices above threshold
            above_threshold = np.where(similarities[j] >= threshold)[0]
            
            if len(above_threshold) > 0:
                # Get top-k
                top_indices = above_threshold[np.argsort(similarities[j][above_threshold])][::-1][:top_k]
                
                translations = [
                    {
                        'translation': epo_vocab[idx],
                        'similarity': float(similarities[j][idx])
                    }
                    for idx in top_indices
                ]
                
                candidates[word] = translations
                total_pairs += len(translations)
    
    logger.info(f"Found {len(candidates):,} Ido words with translations")
    logger.info(f"Total translation pairs: {total_pairs:,}")
    
    return candidates


def main():
    parser = argparse.ArgumentParser(description="Align BERT with Esperanto")
    parser.add_argument('--ido-bert', type=Path, required=True)
    parser.add_argument('--ido-vocab', type=Path, required=True)
    parser.add_argument('--epo-w2v', type=Path, required=True)
    parser.add_argument('--seed-dict', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--threshold', type=float, default=0.50)
    parser.add_argument('--iterations', type=int, default=10)
    parser.add_argument('--alpha', type=float, default=0.5)
    
    args = parser.parse_args()
    
    # Load embeddings
    ido_emb, ido_vocab, ido_idx = load_bert_embeddings(args.ido_bert, args.ido_vocab)
    epo_emb, epo_vocab, epo_idx = load_word2vec_model(args.epo_w2v)
    
    # Load seed dictionary
    seed_pairs = load_seed_dictionary(args.seed_dict, set(ido_vocab), set(epo_vocab))
    
    # Retrofit embeddings
    ido_aligned, epo_aligned = retrofit_embeddings(
        ido_emb, ido_vocab, ido_idx,
        epo_emb, epo_vocab, epo_idx,
        seed_pairs,
        iterations=args.iterations,
        alpha=args.alpha
    )
    
    # Find translation candidates
    candidates = find_translation_candidates(
        ido_aligned, ido_vocab,
        epo_aligned, epo_vocab,
        threshold=args.threshold
    )
    
    # Save results
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"SAVING RESULTS")
    logger.info(f"{'='*60}")
    
    # Save candidates
    candidates_file = args.output_dir / 'bert_candidates.json'
    logger.info(f"Saving candidates to {candidates_file}")
    with open(candidates_file, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)
    
    # Save aligned embeddings
    logger.info(f"Saving aligned embeddings...")
    np.save(args.output_dir / 'ido_bert_aligned.npy', ido_aligned)
    np.save(args.output_dir / 'epo_w2v_aligned.npy', epo_aligned)
    
    # Statistics
    stats = {
        'ido_vocab_size': len(ido_vocab),
        'epo_vocab_size': len(epo_vocab),
        'seed_pairs': len(seed_pairs),
        'threshold': args.threshold,
        'candidates_found': len(candidates),
        'total_pairs': sum(len(v) for v in candidates.values())
    }
    
    stats_file = args.output_dir / 'bert_alignment_stats.json'
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ ALIGNMENT COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Candidates found: {len(candidates):,} Ido words")
    logger.info(f"Total pairs: {stats['total_pairs']:,}")
    logger.info(f"Results saved to: {args.output_dir}")


if __name__ == '__main__':
    main()

