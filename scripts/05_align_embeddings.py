#!/usr/bin/env python3
"""
Step 5: Learn alignment mapping between Ido and Esperanto embedding spaces.

Input:
    - models/ido_fasttext.model
    - models/epo_fasttext.model
    - data/seed_dictionary.txt

Output:
    - models/alignment_matrix.npy
    - models/alignment_stats.json
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Tuple
from gensim.models import FastText
from scipy.linalg import orthogonal_procrustes

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_seed_dictionary(dict_path: Path) -> list:
    """
    Load seed dictionary from text file.
    
    Args:
        dict_path: Path to seed dictionary
        
    Returns:
        List of (ido_word, esperanto_word) tuples
    """
    pairs = []
    with open(dict_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) == 2:
                pairs.append((parts[0], parts[1]))
    return pairs


def extract_embedding_matrices(
    pairs: list,
    ido_model: FastText,
    epo_model: FastText
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract embedding matrices for seed dictionary pairs.
    
    Args:
        pairs: List of (ido_word, esperanto_word) tuples
        ido_model: Ido FastText model
        epo_model: Esperanto FastText model
        
    Returns:
        Tuple of (X_ido, X_epo) numpy arrays
    """
    ido_vectors = []
    epo_vectors = []
    
    for ido_word, epo_word in pairs:
        if ido_word in ido_model.wv and epo_word in epo_model.wv:
            ido_vectors.append(ido_model.wv[ido_word])
            epo_vectors.append(epo_model.wv[epo_word])
    
    X_ido = np.array(ido_vectors)
    X_epo = np.array(epo_vectors)
    
    return X_ido, X_epo


def learn_procrustes_alignment(X_src: np.ndarray, X_tgt: np.ndarray) -> np.ndarray:
    """
    Learn orthogonal Procrustes alignment.
    
    Find orthogonal matrix W that minimizes ||W * X_src - X_tgt||^2
    
    Args:
        X_src: Source embeddings (n_pairs x embedding_dim)
        X_tgt: Target embeddings (n_pairs x embedding_dim)
        
    Returns:
        Alignment matrix W (embedding_dim x embedding_dim)
    """
    # Use scipy's orthogonal_procrustes
    # It solves: min ||W @ X_src.T - X_tgt.T||
    W, _ = orthogonal_procrustes(X_src, X_tgt)
    return W


def evaluate_alignment(
    W: np.ndarray,
    X_src: np.ndarray,
    X_tgt: np.ndarray,
    pairs: list
) -> dict:
    """
    Evaluate alignment quality on seed dictionary.
    
    Args:
        W: Alignment matrix
        X_src: Source embeddings
        X_tgt: Target embeddings
        pairs: List of word pairs
        
    Returns:
        Evaluation metrics dictionary
    """
    from sklearn.metrics.pairwise import cosine_similarity
    
    # Apply alignment
    X_aligned = (W @ X_src.T).T
    
    # Compute cosine similarities between aligned source and all targets
    similarities = cosine_similarity(X_aligned, X_tgt)
    
    # For each source word, find rank of correct target
    n_pairs = len(pairs)
    correct_ranks = []
    diagonal_sims = []
    
    for i in range(n_pairs):
        # Similarity scores for this source word
        sims = similarities[i]
        diagonal_sims.append(sims[i])  # Similarity to correct target
        
        # Rank of correct target (0-indexed)
        rank = np.sum(sims > sims[i])
        correct_ranks.append(rank)
    
    # Calculate precision@k
    p_at_1 = np.mean([r == 0 for r in correct_ranks])
    p_at_5 = np.mean([r < 5 for r in correct_ranks])
    p_at_10 = np.mean([r < 10 for r in correct_ranks])
    
    metrics = {
        'mean_similarity': float(np.mean(diagonal_sims)),
        'median_similarity': float(np.median(diagonal_sims)),
        'precision_at_1': float(p_at_1),
        'precision_at_5': float(p_at_5),
        'precision_at_10': float(p_at_10),
        'num_pairs': n_pairs
    }
    return metrics


def main():
    """Main execution function."""
    logger.info("Starting embedding alignment...")
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / 'models'
    data_dir = base_dir / 'data'
    
    seed_dict_path = data_dir / 'seed_dictionary.txt'
    ido_model_path = models_dir / 'ido_fasttext.model'
    epo_model_path = models_dir / 'epo_fasttext.model'
    alignment_path = models_dir / 'alignment_matrix.npy'
    stats_path = models_dir / 'alignment_stats.json'
    
    # Check if files exist
    if not seed_dict_path.exists():
        logger.error(f"Seed dictionary not found at {seed_dict_path}")
        return
    
    if not ido_model_path.exists() or not epo_model_path.exists():
        logger.error("Embedding models not found")
        return
    
    # Load models
    logger.info("Loading embedding models...")
    ido_model = FastText.load(str(ido_model_path))
    epo_model = FastText.load(str(epo_model_path))
    
    # Load seed dictionary
    logger.info(f"Loading seed dictionary from {seed_dict_path}")
    pairs = load_seed_dictionary(seed_dict_path)
    logger.info(f"Loaded {len(pairs)} seed pairs")
    
    # Extract embedding matrices
    logger.info("Extracting embedding matrices...")
    X_ido, X_epo = extract_embedding_matrices(pairs, ido_model, epo_model)
    logger.info(f"Matrix shapes: Ido {X_ido.shape}, Esperanto {X_epo.shape}")
    
    # Learn alignment
    logger.info("Learning Procrustes alignment...")
    W = learn_procrustes_alignment(X_ido, X_epo)
    logger.info(f"Alignment matrix shape: {W.shape}")
    
    # Evaluate alignment
    logger.info("Evaluating alignment quality...")
    metrics = evaluate_alignment(W, X_ido, X_epo, pairs)
    logger.info(f"Alignment metrics: {metrics}")
    
    # Save alignment matrix
    logger.info(f"Saving alignment matrix to {alignment_path}")
    np.save(alignment_path, W)
    
    # Save statistics
    with open(stats_path, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    logger.info("Embedding alignment complete!")


if __name__ == '__main__':
    main()
