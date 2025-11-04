#!/usr/bin/env python3
"""
Step 7: Validate and filter translation candidates.

Input:
    - results/candidate_translations.json
    - models/ido_fasttext.model
    - models/epo_fasttext.model
    - models/alignment_matrix.npy

Output:
    - results/high_confidence_translations.json
    - results/medium_confidence_translations.json
    - results/validation_stats.json
"""

import json
import logging
import numpy as np
from pathlib import Path
from typing import Dict, List
from gensim.models import FastText

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_candidates(candidates_path: Path) -> Dict:
    """Load candidate translations from JSON."""
    with open(candidates_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def check_mutual_nearest_neighbor(
    ido_word: str,
    epo_word: str,
    ido_model: FastText,
    epo_model: FastText,
    alignment_matrix: np.ndarray,
    k: int = 10
) -> bool:
    """Check if translation is mutual nearest neighbor."""
    from sklearn.metrics.pairwise import cosine_similarity
    
    # Check Esperanto -> Ido direction
    if epo_word not in epo_model.wv:
        return False
    
    # Get Esperanto embedding
    v_epo = epo_model.wv[epo_word].reshape(1, -1)
    
    # Apply inverse alignment (transpose)
    v_aligned = (alignment_matrix.T @ v_epo.T).T
    
    # Get all Ido embeddings
    ido_vectors = ido_model.wv.vectors
    
    # Compute similarities
    similarities = cosine_similarity(v_aligned, ido_vectors)[0]
    
    # Get top k
    top_k_indices = np.argsort(similarities)[-k:][::-1]
    top_k_words = [ido_model.wv.index_to_key[idx] for idx in top_k_indices]
    
    return ido_word in top_k_words


def compute_frequency_ratio(
    ido_word: str,
    epo_word: str,
    ido_model: FastText,
    epo_model: FastText
) -> float:
    """Compute frequency ratio between words."""
    ido_count = ido_model.wv.get_vecattr(ido_word, 'count')
    epo_count = epo_model.wv.get_vecattr(epo_word, 'count')
    
    # Return ratio (smaller / larger) to get value between 0 and 1
    if ido_count == 0 or epo_count == 0:
        return 0.0
    
    return min(ido_count, epo_count) / max(ido_count, epo_count)


def compute_edit_distance(word1: str, word2: str) -> int:
    """Compute Levenshtein edit distance."""
    if len(word1) < len(word2):
        return compute_edit_distance(word2, word1)
    
    if len(word2) == 0:
        return len(word1)
    
    previous_row = range(len(word2) + 1)
    for i, c1 in enumerate(word1):
        current_row = [i + 1]
        for j, c2 in enumerate(word2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def filter_candidates(
    candidates: Dict,
    ido_model: FastText,
    epo_model: FastText,
    alignment_matrix: np.ndarray,
    min_similarity: float = 0.5,
    check_mutual: bool = True
) -> Dict:
    """
    Filter candidates by quality criteria.
    
    Returns:
        Dict with 'high', 'medium', 'low' confidence levels
    """
    from tqdm import tqdm
    
    high_conf = {}
    medium_conf = {}
    low_conf = {}
    
    for ido_word, translations in tqdm(candidates.items(), desc="Validating"):
        for trans in translations:
            epo_word = trans['translation']
            similarity = trans['similarity']
            
            # Skip if below minimum threshold
            if similarity < min_similarity:
                continue
            
            # Check mutual nearest neighbor
            is_mutual = False
            if check_mutual:
                is_mutual = check_mutual_nearest_neighbor(
                    ido_word, epo_word, ido_model, epo_model, alignment_matrix
                )
            
            # Compute additional features
            freq_ratio = compute_frequency_ratio(ido_word, epo_word, ido_model, epo_model)
            edit_dist = compute_edit_distance(ido_word, epo_word)
            
            # Classify by confidence
            if similarity > 0.7 and (is_mutual or not check_mutual) and freq_ratio > 0.1:
                if ido_word not in high_conf:
                    high_conf[ido_word] = []
                high_conf[ido_word].append({
                    'translation': epo_word,
                    'similarity': similarity,
                    'mutual_nn': is_mutual,
                    'freq_ratio': freq_ratio,
                    'edit_distance': edit_dist
                })
            elif similarity > 0.6:
                if ido_word not in medium_conf:
                    medium_conf[ido_word] = []
                medium_conf[ido_word].append({
                    'translation': epo_word,
                    'similarity': similarity,
                    'mutual_nn': is_mutual,
                    'freq_ratio': freq_ratio,
                    'edit_distance': edit_dist
                })
            else:
                if ido_word not in low_conf:
                    low_conf[ido_word] = []
                low_conf[ido_word].append({
                    'translation': epo_word,
                    'similarity': similarity,
                    'mutual_nn': is_mutual,
                    'freq_ratio': freq_ratio,
                    'edit_distance': edit_dist
                })
    
    return {'high': high_conf, 'medium': medium_conf, 'low': low_conf}
    # - Check mutual nearest neighbors
    # - Check frequency consistency
    # - Compute edit distance
    # - Classify by confidence level
    pass


def compute_statistics(filtered: Dict) -> Dict:
    """Compute validation statistics."""
    high_words = len(filtered['high'])
    medium_words = len(filtered['medium'])
    low_words = len(filtered['low'])
    
    high_pairs = sum(len(v) for v in filtered['high'].values())
    medium_pairs = sum(len(v) for v in filtered['medium'].values())
    low_pairs = sum(len(v) for v in filtered['low'].values())
    
    stats = {
        'high_confidence_words': high_words,
        'high_confidence_pairs': high_pairs,
        'medium_confidence_words': medium_words,
        'medium_confidence_pairs': medium_pairs,
        'low_confidence_words': low_words,
        'low_confidence_pairs': low_pairs,
        'total_words': high_words + medium_words + low_words,
        'total_pairs': high_pairs + medium_pairs + low_pairs
    }
    return stats


def main():
    """Main execution function."""
    logger.info("Starting candidate validation...")
    
    base_dir = Path(__file__).parent.parent
    results_dir = base_dir / 'results'
    models_dir = base_dir / 'models'
    
    candidates_path = results_dir / 'candidate_translations.json'
    high_conf_path = results_dir / 'high_confidence_translations.json'
    medium_conf_path = results_dir / 'medium_confidence_translations.json'
    stats_path = results_dir / 'validation_stats.json'
    
    if not candidates_path.exists():
        logger.error("Candidates file not found")
        return
    
    # Load models
    logger.info("Loading models...")
    ido_model = FastText.load(str(models_dir / 'ido_fasttext.model'))
    epo_model = FastText.load(str(models_dir / 'epo_fasttext.model'))
    alignment_matrix = np.load(models_dir / 'alignment_matrix.npy')
    
    # Load candidates
    logger.info("Loading candidates...")
    candidates = load_candidates(candidates_path)
    
    # Filter candidates
    logger.info("Filtering candidates...")
    filtered = filter_candidates(candidates, ido_model, epo_model, alignment_matrix)
    
    # Save results
    logger.info("Saving filtered results...")
    with open(high_conf_path, 'w', encoding='utf-8') as f:
        json.dump(filtered['high'], f, indent=2, ensure_ascii=False)
    
    with open(medium_conf_path, 'w', encoding='utf-8') as f:
        json.dump(filtered['medium'], f, indent=2, ensure_ascii=False)
    
    # Compute and save statistics
    stats = compute_statistics(filtered)
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"Validation complete: {stats}")


if __name__ == '__main__':
    main()
