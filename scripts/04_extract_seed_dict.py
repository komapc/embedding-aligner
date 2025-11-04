#!/usr/bin/env python3
"""
Step 4: Extract seed dictionary from vortaro_dictionary.json.

Input:
    - terraform/extractor-results/20251025-222952/vortaro_dictionary.json
    - models/ido_fasttext.model
    - models/epo_fasttext.model

Output:
    - data/seed_dictionary.txt (format: "ido_word esperanto_word")
    - data/seed_dictionary_stats.json
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from gensim.models import FastText

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_dictionary(dict_path: Path) -> Dict:
    """
    Load dictionary from JSON file.
    
    Args:
        dict_path: Path to dictionary JSON
        
    Returns:
        Dictionary data
    """
    # TODO: Implement dictionary loading
    pass


def extract_word_pairs(dictionary: Dict) -> List[Tuple[str, str]]:
    """
    Extract (ido_word, esperanto_word) pairs from dictionary.
    
    Args:
        dictionary: Dictionary data structure
        
    Returns:
        List of (ido, esperanto) tuples
    """
    # TODO: Implement pair extraction
    # - Parse dictionary structure
    # - Extract lemma forms
    # - Handle multiple translations
    # - Remove multi-word expressions (optional)
    pass


def filter_pairs_by_vocabulary(
    pairs: List[Tuple[str, str]],
    ido_model: FastText,
    epo_model: FastText,
    min_freq: int = 5
) -> List[Tuple[str, str]]:
    """
    Filter pairs to only include words in both embedding vocabularies.
    
    Args:
        pairs: List of (ido, esperanto) tuples
        ido_model: Ido FastText model
        epo_model: Esperanto FastText model
        min_freq: Minimum word frequency
        
    Returns:
        Filtered list of pairs
    """
    # TODO: Implement vocabulary filtering
    # - Check if word exists in vocabulary
    # - Check word frequency
    # - Remove low-frequency pairs
    pass


def save_seed_dictionary(pairs: List[Tuple[str, str]], output_path: Path):
    """
    Save seed dictionary to text file.
    
    Args:
        pairs: List of (ido, esperanto) tuples
        output_path: Path to save dictionary
    """
    # TODO: Implement saving
    # - Write one pair per line
    # - Format: "ido_word esperanto_word"
    pass


def compute_statistics(
    original_pairs: List[Tuple[str, str]],
    filtered_pairs: List[Tuple[str, str]]
) -> Dict:
    """
    Compute statistics about seed dictionary.
    
    Args:
        original_pairs: Original extracted pairs
        filtered_pairs: Filtered pairs
        
    Returns:
        Statistics dictionary
    """
    # TODO: Implement statistics
    stats = {
        'original_pairs': len(original_pairs),
        'filtered_pairs': len(filtered_pairs),
        'coverage': 0.0,
        'unique_ido_words': 0,
        'unique_epo_words': 0
    }
    return stats


def main():
    """Main execution function."""
    logger.info("Starting seed dictionary extraction...")
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    dict_path = base_dir.parent.parent / 'terraform' / 'extractor-results' / '20251025-222952' / 'vortaro_dictionary.json'
    models_dir = base_dir / 'models'
    data_dir = base_dir / 'data'
    output_path = data_dir / 'seed_dictionary.txt'
    stats_path = data_dir / 'seed_dictionary_stats.json'
    
    # Check if dictionary exists
    if not dict_path.exists():
        logger.error(f"Dictionary not found at {dict_path}")
        return
    
    # Check if models exist
    ido_model_path = models_dir / 'ido_fasttext.model'
    epo_model_path = models_dir / 'epo_fasttext.model'
    
    if not ido_model_path.exists() or not epo_model_path.exists():
        logger.error("Embedding models not found. Please train embeddings first.")
        return
    
    # Load models
    logger.info("Loading embedding models...")
    ido_model = FastText.load(str(ido_model_path))
    epo_model = FastText.load(str(epo_model_path))
    
    # Load dictionary
    logger.info(f"Loading dictionary from {dict_path}")
    dictionary = load_dictionary(dict_path)
    
    # Extract pairs
    logger.info("Extracting word pairs...")
    original_pairs = extract_word_pairs(dictionary)
    logger.info(f"Extracted {len(original_pairs)} pairs")
    
    # Filter by vocabulary
    logger.info("Filtering by vocabulary coverage...")
    filtered_pairs = filter_pairs_by_vocabulary(original_pairs, ido_model, epo_model)
    logger.info(f"Retained {len(filtered_pairs)} pairs after filtering")
    
    # Save seed dictionary
    logger.info(f"Saving seed dictionary to {output_path}")
    save_seed_dictionary(filtered_pairs, output_path)
    
    # Compute and save statistics
    stats = compute_statistics(original_pairs, filtered_pairs)
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    logger.info(f"Statistics: {stats}")
    
    logger.info("Seed dictionary extraction complete!")


if __name__ == '__main__':
    main()
