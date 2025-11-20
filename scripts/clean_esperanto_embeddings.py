#!/usr/bin/env python3
"""
Clean Esperanto Word2Vec embeddings by removing punctuation, numbers, and special characters.

Similar to clean_and_project_bert.py but for Esperanto Word2Vec embeddings.
Already 300D so no PCA needed.

Usage:
    python scripts/clean_esperanto_embeddings.py \
        --model models/esperanto_min3.model \
        --output-prefix models/esperanto_clean_
"""

import argparse
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict
import re
from gensim.models import Word2Vec
from collections import defaultdict
import json


def should_keep_word(word: str) -> bool:
    """
    Determine if a word should be kept based on cleaning criteria.
    
    Keep if:
    - Alphabetic characters (including Esperanto diacritics)
    - No punctuation, numbers, or special characters
    - Not a special token
    """
    # Skip special tokens
    if word.startswith('[') and word.endswith(']'):
        return False
    
    # Skip if contains numbers
    if any(c.isdigit() for c in word):
        return False
    
    # Skip if contains punctuation (except hyphens within word)
    # Allow internal hyphens like "sankta-luizo" but not trailing "sankta-luizo,"
    if re.search(r'[^\w\-ĉĝĥĵŝŭ]', word, re.IGNORECASE):
        return False
    
    # Skip if starts or ends with hyphen
    if word.startswith('-') or word.endswith('-'):
        return False
    
    # Skip very short words (1 character) except valid Esperanto words
    if len(word) < 2:
        return False
    
    # Must contain at least one letter
    if not re.search(r'[a-zĉĝĥĵŝŭ]', word, re.IGNORECASE):
        return False
    
    return True


def clean_embeddings(
    model: Word2Vec,
    merge_case: bool = True
) -> Tuple[np.ndarray, List[str], Dict[str, int]]:
    """
    Clean Word2Vec embeddings by removing noise and merging variants.
    
    Args:
        model: Gensim Word2Vec model
        merge_case: If True, merge uppercase variants to lowercase
        
    Returns:
        Tuple of (embeddings, vocabulary, word_to_idx)
    """
    print("\n" + "="*70)
    print("CLEANING ESPERANTO EMBEDDINGS")
    print("="*70)
    
    vocab = list(model.wv.index_to_key)
    embeddings = model.wv.vectors
    
    print(f"\nOriginal vocabulary: {len(vocab):,} words")
    print(f"Original embeddings shape: {embeddings.shape}")
    
    # Step 1: Filter words
    print("\n[1/3] Filtering words...")
    keep_indices = []
    keep_words = []
    
    for idx, word in enumerate(vocab):
        if should_keep_word(word):
            keep_indices.append(idx)
            keep_words.append(word)
    
    filtered_embeddings = embeddings[keep_indices]
    filtered_words = keep_words
    
    print(f"  Kept: {len(filtered_words):,} words")
    print(f"  Removed: {len(vocab) - len(filtered_words):,} words")
    
    # Step 2: Merge case variants
    if merge_case:
        print("\n[2/3] Merging case variants...")
        word_map = defaultdict(list)  # lowercase -> [(original, idx)]
        
        for idx, word in enumerate(filtered_words):
            word_lower = word.lower()
            word_map[word_lower].append((word, idx))
        
        # Keep lowercase version, average embeddings if multiple variants
        clean_words = []
        clean_embeddings_list = []
        
        for word_lower, variants in word_map.items():
            if len(variants) == 1:
                # Only one variant, keep as-is (but use lowercase)
                _, idx = variants[0]
                clean_words.append(word_lower)
                clean_embeddings_list.append(filtered_embeddings[idx])
            else:
                # Multiple variants, average their embeddings
                indices = [idx for _, idx in variants]
                avg_embedding = filtered_embeddings[indices].mean(axis=0)
                clean_words.append(word_lower)
                clean_embeddings_list.append(avg_embedding)
        
        clean_embeddings = np.array(clean_embeddings_list)
        
        print(f"  Before merging: {len(filtered_words):,} words")
        print(f"  After merging: {len(clean_words):,} words")
        print(f"  Merged: {len(filtered_words) - len(clean_words):,} case variants")
    else:
        clean_embeddings = filtered_embeddings
        clean_words = filtered_words
    
    # Step 3: Create word-to-index mapping
    print("\n[3/3] Creating word-to-index mapping...")
    word_to_idx = {word: idx for idx, word in enumerate(clean_words)}
    
    print("\n" + "="*70)
    print("CLEANING COMPLETE")
    print("="*70)
    print(f"Final vocabulary: {len(clean_words):,} words")
    print(f"Final embeddings shape: {clean_embeddings.shape}")
    print(f"Reduction: {len(vocab) - len(clean_words):,} words removed ({(len(vocab)-len(clean_words))/len(vocab)*100:.1f}%)")
    
    return clean_embeddings, clean_words, word_to_idx


def save_results(
    embeddings: np.ndarray,
    vocab: List[str],
    output_prefix: Path,
    original_count: int,
    kept_count: int
):
    """Save cleaned embeddings, vocabulary, and statistics."""
    print("\n" + "="*70)
    print("SAVING RESULTS")
    print("="*70)
    
    # Save embeddings
    embeddings_path = output_prefix.parent / f"{output_prefix.stem}_300d.npy"
    print(f"\nSaving embeddings to: {embeddings_path}")
    np.save(embeddings_path, embeddings)
    print(f"  Size: {embeddings_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Save vocabulary
    vocab_path = output_prefix.parent / f"{output_prefix.stem}_vocab.txt"
    print(f"\nSaving vocabulary to: {vocab_path}")
    with open(vocab_path, 'w', encoding='utf-8') as f:
        for word in vocab:
            f.write(f"{word}\n")
    print(f"  Words: {len(vocab):,}")
    
    # Save statistics
    stats = {
        'original_vocabulary': original_count,
        'cleaned_vocabulary': kept_count,
        'removed': original_count - kept_count,
        'reduction_percent': (original_count - kept_count) / original_count * 100,
        'embedding_dimension': embeddings.shape[1]
    }
    
    stats_path = output_prefix.parent / f"{output_prefix.stem}_stats.json"
    print(f"\nSaving statistics to: {stats_path}")
    with open(stats_path, 'w') as f:
        json.dump(stats, f, indent=2)
    
    print("\n" + "="*70)
    print("✅ ALL FILES SAVED")
    print("="*70)
    
    # Show sample cleaned words
    print("\nSample cleaned vocabulary (first 20):")
    for i, word in enumerate(vocab[:20], 1):
        print(f"  {i:2d}. {word}")


def main():
    parser = argparse.ArgumentParser(
        description='Clean Esperanto Word2Vec embeddings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('--model', type=Path, required=True,
                        help='Path to Esperanto Word2Vec model')
    parser.add_argument('--output-prefix', type=Path, required=True,
                        help='Output prefix (e.g., models/esperanto_clean_)')
    parser.add_argument('--no-merge-case', action='store_true',
                        help='Do not merge case variants')
    
    args = parser.parse_args()
    
    # Load model
    print("="*70)
    print("LOADING ESPERANTO WORD2VEC MODEL")
    print("="*70)
    print(f"\nModel: {args.model}")
    
    model = Word2Vec.load(str(args.model))
    original_count = len(model.wv.index_to_key)
    
    print(f"✅ Loaded model with {original_count:,} words")
    print(f"   Embedding dimension: {model.wv.vector_size}")
    
    # Clean embeddings
    embeddings, vocab, word_to_idx = clean_embeddings(
        model,
        merge_case=not args.no_merge_case
    )
    
    # Create output directory
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    
    # Save results
    save_results(
        embeddings,
        vocab,
        args.output_prefix,
        original_count,
        len(vocab)
    )
    
    print("\n" + "="*70)
    print("✅ CLEANING COMPLETE!")
    print("="*70)
    print("\nOutput files:")
    print(f"  • {args.output_prefix.parent / f'{args.output_prefix.stem}_300d.npy'}")
    print(f"  • {args.output_prefix.parent / f'{args.output_prefix.stem}_vocab.txt'}")
    print(f"  • {args.output_prefix.parent / f'{args.output_prefix.stem}_stats.json'}")
    print("\nNext step: Re-run alignment with cleaned Esperanto embeddings")


if __name__ == '__main__':
    main()

