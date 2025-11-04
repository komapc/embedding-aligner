#!/usr/bin/env python3
"""
Step 6: Find translation candidates using aligned embeddings.

Input:
    - models/ido_fasttext.model
    - models/epo_fasttext.model
    - models/alignment_matrix.npy
    - data/seed_dictionary.txt

Output:
    - results/candidate_translations.json
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List, Set
from gensim.models import FastText
from sklearn.metrics.pairwise import cosine_similarity

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_seed_words(dict_path: Path) -> Set[str]:
    """
    Load Ido words from seed dictionary to exclude them.
    
    Args:
        dict_path: Path to seed dictionary
        
    Returns:
        Set of Ido words already in dictionary
    """
    seed_words = set()
    with open(dict_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 1:
                seed_words.add(parts[0])
    return seed_words


def get_candidate_words(
    ido_model: FastText,
    seed_words: Set[str],
    min_freq: int = 10,
    max_words: int = 10000
) -> List[str]:
    """
    Get list of Ido words to find translations for.
    
    Args:
        ido_model: Ido FastText model
        seed_words: Words already in dictionary (to exclude)
        min_freq: Minimum word frequency
        max_words: Maximum number of words to process
        
    Returns:
        List of Ido words
    """
    candidates = []
    
    # Get words sorted by frequency
    vocab_items = [(word, ido_model.wv.get_vecattr(word, 'count')) 
                   for word in ido_model.wv.index_to_key]
    vocab_items.sort(key=lambda x: x[1], reverse=True)
    
    for word, count in vocab_items:
        if word in seed_words:
            continue
        if count < min_freq:
            continue
        if len(word) < 3:  # Skip very short words
            continue
        
        candidates.append(word)
        
        if len(candidates) >= max_words:
            break
    
    return candidates


def find_nearest_neighbors(
    word: str,
    ido_model: FastText,
    epo_model: FastText,
    alignment_matrix: np.ndarray,
    k: int = 10
) -> List[Dict]:
    """
    Find k nearest Esperanto neighbors for an Ido word.
    
    Args:
        word: Ido word
        ido_model: Ido FastText model
        epo_model: Esperanto FastText model
        alignment_matrix: Alignment matrix W
        k: Number of neighbors to return
        
    Returns:
        List of dicts with 'translation' and 'similarity' keys
    """
    if word not in ido_model.wv:
        return []
    
    # Get Ido embedding
    v_ido = ido_model.wv[word].reshape(1, -1)
    
    # Apply alignment
    v_aligned = (alignment_matrix @ v_ido.T).T
    
    # Get all Esperanto embeddings
    epo_vectors = epo_model.wv.vectors
    
    # Compute cosine similarities
    similarities = cosine_similarity(v_aligned, epo_vectors)[0]
    
    # Get top k indices
    top_k_indices = np.argsort(similarities)[-k:][::-1]
    
    # Build result list
    results = []
    for idx in top_k_indices:
        epo_word = epo_model.wv.index_to_key[idx]
        similarity = float(similarities[idx])
        results.append({
            'translation': epo_word,
            'similarity': similarity
        })
    
    return results


def process_all_candidates(
    candidate_words: List[str],
    ido_model: FastText,
    epo_model: FastText,
    alignment_matrix: np.ndarray,
    k: int = 10
) -> Dict[str, List[Dict]]:
    """
    Process all candidate words and find translations.
    
    Args:
        candidate_words: List of Ido words
        ido_model: Ido FastText model
        epo_model: Esperanto FastText model
        alignment_matrix: Alignment matrix
        k: Number of neighbors per word
        
    Returns:
        Dictionary mapping Ido words to candidate translations
    """
    from tqdm import tqdm
    
    results = {}
    
    for word in tqdm(candidate_words, desc="Finding candidates"):
        neighbors = find_nearest_neighbors(
            word, ido_model, epo_model, alignment_matrix, k
        )
        if neighbors:
            results[word] = neighbors
    
    return results


def main():
    """Main execution function."""
    logger.info("Starting candidate translation search...")
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    models_dir = base_dir / 'models'
    data_dir = base_dir / 'data'
    results_dir = base_dir / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    
    seed_dict_path = data_dir / 'seed_dictionary.txt'
    ido_model_path = models_dir / 'ido_fasttext.model'
    epo_model_path = models_dir / 'epo_fasttext.model'
    alignment_path = models_dir / 'alignment_matrix.npy'
    output_path = results_dir / 'candidate_translations.json'
    
    # Check if files exist
    if not all([seed_dict_path.exists(), ido_model_path.exists(), 
                epo_model_path.exists(), alignment_path.exists()]):
        logger.error("Required files not found. Please run previous steps first.")
        return
    
    # Load models and alignment
    logger.info("Loading models and alignment matrix...")
    ido_model = FastText.load(str(ido_model_path))
    epo_model = FastText.load(str(epo_model_path))
    alignment_matrix = np.load(alignment_path)
    
    # Load seed words
    logger.info("Loading seed dictionary...")
    seed_words = load_seed_words(seed_dict_path)
    logger.info(f"Loaded {len(seed_words)} seed words to exclude")
    
    # Get candidate words
    logger.info("Selecting candidate words...")
    candidate_words = get_candidate_words(ido_model, seed_words, min_freq=10, max_words=10000)
    logger.info(f"Processing {len(candidate_words)} candidate words")
    
    # Find translations
    logger.info("Finding translation candidates...")
    candidates = process_all_candidates(
        candidate_words,
        ido_model,
        epo_model,
        alignment_matrix,
        k=10
    )
    
    # Save results
    logger.info(f"Saving candidates to {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Found candidates for {len(candidates)} words")
    logger.info("Candidate translation search complete!")


if __name__ == '__main__':
    main()
