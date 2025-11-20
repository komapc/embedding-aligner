#!/usr/bin/env python3
"""
Clean BERT embeddings and project to 300d for alignment with Esperanto.

This script:
1. Removes punctuation variants (keeps only clean words)
2. Projects from 768d to 300d using PCA
3. Creates embeddings compatible with Word2Vec Esperanto

Usage:
    python scripts/clean_and_project_bert.py \
        --input models/ido_bert_embeddings.npy \
        --vocab models/ido_bert_embeddings_vocab.txt \
        --output-300d models/ido_bert_embeddings_300d.npy \
        --output-vocab models/ido_bert_vocab_clean.txt
"""

import argparse
import logging
import numpy as np
import re
from pathlib import Path
from typing import List, Tuple, Set
from sklearn.decomposition import PCA
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def is_clean_word(word: str) -> bool:
    """
    Check if word is clean (no punctuation, no special chars).
    
    Returns True for: hundo, manjar, bela, urbo, etc.
    Returns False for: hundo, "hundo, 123, a., etc.
    """
    # Skip if empty
    if not word or len(word) == 0:
        return False
    
    # Skip single characters (except 'o', 'a', 'e', 'i', 'u')
    if len(word) == 1 and word not in ['o', 'a', 'e', 'i', 'u']:
        return False
    
    # Skip if contains any punctuation
    if re.search(r'[.,;:!?"\'()\[\]{}<>«»""''`]', word):
        return False
    
    # Skip if contains digits
    if re.search(r'\d', word):
        return False
    
    # Skip if contains special characters
    if re.search(r'[*@#$%^&+=|\\/_~]', word):
        return False
    
    # Skip if all uppercase (likely acronym or special token)
    if word.isupper() and len(word) > 1:
        return False
    
    # Must contain at least one letter
    if not re.search(r'[a-zA-Zĉĝĥĵŝŭ]', word):
        return False
    
    return True


def clean_embeddings(
    embeddings: np.ndarray,
    vocab: List[str],
    remove_duplicates: bool = True
) -> Tuple[np.ndarray, List[str], dict]:
    """
    Remove punctuation variants and duplicates from embeddings.
    
    If remove_duplicates=True and we have both 'hundo' and 'hundo,':
    - Keep only 'hundo'
    - Average their embeddings
    """
    logger.info(f"Cleaning {len(vocab):,} words...")
    
    clean_indices = []
    clean_words = []
    skipped_punctuation = 0
    skipped_numbers = 0
    skipped_special = 0
    
    # First pass: identify clean words
    for i, word in enumerate(tqdm(vocab, desc="Filtering")):
        if is_clean_word(word):
            clean_indices.append(i)
            clean_words.append(word)
        else:
            # Categorize what was skipped
            if re.search(r'[.,;:!?"\'()\[\]{}<>]', word):
                skipped_punctuation += 1
            elif re.search(r'\d', word):
                skipped_numbers += 1
            else:
                skipped_special += 1
    
    logger.info(f"Kept {len(clean_words):,} clean words")
    logger.info(f"Removed {skipped_punctuation:,} with punctuation")
    logger.info(f"Removed {skipped_numbers:,} with numbers")
    logger.info(f"Removed {skipped_special:,} special tokens")
    
    # Extract clean embeddings
    clean_embeddings = embeddings[clean_indices]
    
    # Handle duplicates (lowercase variants)
    if remove_duplicates:
        logger.info("Handling case variants...")
        word_to_indices = {}
        
        for i, word in enumerate(clean_words):
            word_lower = word.lower()
            if word_lower not in word_to_indices:
                word_to_indices[word_lower] = []
            word_to_indices[word_lower].append(i)
        
        # Average duplicate embeddings
        final_words = []
        final_embeddings = []
        duplicates_merged = 0
        
        for word_lower, indices in tqdm(word_to_indices.items(), desc="Merging"):
            if len(indices) > 1:
                # Average embeddings
                avg_embedding = np.mean(clean_embeddings[indices], axis=0)
                final_embeddings.append(avg_embedding)
                duplicates_merged += len(indices) - 1
            else:
                final_embeddings.append(clean_embeddings[indices[0]])
            
            # Use the most common case variant (usually lowercase)
            final_words.append(word_lower)
        
        logger.info(f"Merged {duplicates_merged:,} duplicate variants")
        
        final_embeddings = np.array(final_embeddings)
    else:
        final_words = clean_words
        final_embeddings = clean_embeddings
    
    # Statistics
    stats = {
        'original_vocab': len(vocab),
        'clean_vocab': len(final_words),
        'removed_punctuation': skipped_punctuation,
        'removed_numbers': skipped_numbers,
        'removed_special': skipped_special,
        'duplicates_merged': duplicates_merged if remove_duplicates else 0
    }
    
    logger.info(f"\n{'='*60}")
    logger.info(f"CLEANING SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Original: {stats['original_vocab']:,} words")
    logger.info(f"Clean: {stats['clean_vocab']:,} words")
    logger.info(f"Reduction: {stats['original_vocab'] - stats['clean_vocab']:,} words ({(stats['original_vocab'] - stats['clean_vocab']) / stats['original_vocab'] * 100:.1f}%)")
    
    return final_embeddings, final_words, stats


def project_to_300d(embeddings: np.ndarray, n_components: int = 300) -> Tuple[np.ndarray, dict]:
    """
    Project embeddings from 768d to 300d using PCA.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"DIMENSIONALITY REDUCTION")
    logger.info(f"{'='*60}")
    logger.info(f"Projecting from {embeddings.shape[1]}d to {n_components}d using PCA...")
    
    pca = PCA(n_components=n_components, random_state=42)
    projected = pca.fit_transform(embeddings)
    
    explained_var = np.sum(pca.explained_variance_ratio_)
    
    logger.info(f"✅ PCA complete")
    logger.info(f"Explained variance: {explained_var:.2%}")
    logger.info(f"Output shape: {projected.shape}")
    
    stats = {
        'original_dims': embeddings.shape[1],
        'projected_dims': n_components,
        'explained_variance': float(explained_var),
        'variance_per_component': pca.explained_variance_ratio_[:10].tolist()
    }
    
    return projected, stats


def main():
    parser = argparse.ArgumentParser(description="Clean and project BERT embeddings")
    parser.add_argument('--input', type=Path, required=True, help="Input BERT embeddings (.npy)")
    parser.add_argument('--vocab', type=Path, required=True, help="Input vocabulary")
    parser.add_argument('--output-300d', type=Path, required=True, help="Output 300d embeddings")
    parser.add_argument('--output-vocab', type=Path, required=True, help="Output clean vocabulary")
    parser.add_argument('--no-merge-duplicates', action='store_true', help="Don't merge case variants")
    parser.add_argument('--dims', type=int, default=300, help="Target dimensions (default: 300)")
    
    args = parser.parse_args()
    
    # Load embeddings
    logger.info(f"Loading embeddings from {args.input}")
    embeddings = np.load(args.input)
    
    logger.info(f"Loading vocabulary from {args.vocab}")
    with open(args.vocab, 'r', encoding='utf-8') as f:
        vocab = [line.strip() for line in f]
    
    logger.info(f"Loaded {len(vocab):,} embeddings, shape: {embeddings.shape}")
    
    # Clean embeddings
    clean_emb, clean_vocab, clean_stats = clean_embeddings(
        embeddings,
        vocab,
        remove_duplicates=not args.no_merge_duplicates
    )
    
    # Project to 300d
    projected_emb, proj_stats = project_to_300d(clean_emb, n_components=args.dims)
    
    # Save results
    logger.info(f"\n{'='*60}")
    logger.info(f"SAVING RESULTS")
    logger.info(f"{'='*60}")
    
    # Save embeddings
    args.output_300d.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Saving 300d embeddings to {args.output_300d}")
    np.save(args.output_300d, projected_emb)
    
    # Save vocabulary
    logger.info(f"Saving clean vocabulary to {args.output_vocab}")
    with open(args.output_vocab, 'w', encoding='utf-8') as f:
        for word in clean_vocab:
            f.write(word + '\n')
    
    # Save stats
    stats_file = args.output_300d.parent / 'bert_cleaning_stats.json'
    logger.info(f"Saving statistics to {stats_file}")
    import json
    stats = {
        'cleaning': clean_stats,
        'projection': proj_stats,
        'input_file': str(args.input),
        'output_file': str(args.output_300d),
        'vocab_file': str(args.output_vocab)
    }
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ SUCCESS")
    logger.info(f"{'='*60}")
    logger.info(f"Input:  {len(vocab):,} words × {embeddings.shape[1]} dims")
    logger.info(f"Output: {len(clean_vocab):,} words × {projected_emb.shape[1]} dims")
    logger.info(f"Reduction: {len(vocab) - len(clean_vocab):,} words removed")
    logger.info(f"Variance preserved: {proj_stats['explained_variance']:.2%}")
    logger.info(f"\n✅ Ready for alignment with Esperanto Word2Vec (300d)!")


if __name__ == '__main__':
    main()

