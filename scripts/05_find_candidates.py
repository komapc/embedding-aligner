#!/usr/bin/env python3
"""
Find translation candidates for unknown Ido words using aligned embeddings.
Uses CSLS for retrieval and applies high-precision filters.
"""

import numpy as np
from pathlib import Path
from tqdm import tqdm
import argparse

def load_embeddings(filepath):
    """Load word embeddings from text file."""
    print(f"Loading embeddings from {filepath}...")
    words = []
    vectors = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        # Skip header line (vocab_size, dimension)
        next(f)
        for line in f:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            word = parts[0]
            vector = np.array([float(x) for x in parts[1:]])
            words.append(word)
            vectors.append(vector)
    
    vectors = np.array(vectors)
    word_to_idx = {w: i for i, w in enumerate(words)}
    
    print(f"Loaded {len(words)} words with {vectors.shape[1]} dimensions")
    return words, vectors, word_to_idx

def load_dictionary(filepath):
    """Load existing dictionary."""
    pairs = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                pairs.add((parts[0], parts[1]))
    return pairs

def csls(src_vec, tgt_vecs, k=10):
    """
    Cross-domain Similarity Local Scaling (CSLS).
    Better than cosine similarity for cross-lingual retrieval.
    """
    # Normalize vectors
    src_vec = src_vec / np.linalg.norm(src_vec)
    tgt_vecs_norm = tgt_vecs / np.linalg.norm(tgt_vecs, axis=1, keepdims=True)
    
    # Cosine similarities
    similarities = np.dot(tgt_vecs_norm, src_vec)
    
    # Get top-k for CSLS calculation
    top_k_idx = np.argpartition(-similarities, min(k, len(similarities)-1))[:k]
    mean_similarity = np.mean(similarities[top_k_idx])
    
    # CSLS score
    csls_scores = 2 * similarities - mean_similarity
    
    return csls_scores

def find_candidates(ido_words, ido_vecs, ido_to_idx,
                   epo_words, epo_vecs, epo_to_idx,
                   existing_dict, threshold=0.7, k=10):
    """Find translation candidates for unknown Ido words."""
    
    # Get unknown Ido words
    existing_ido = set(pair[0] for pair in existing_dict)
    unknown_ido = [w for w in ido_words if w not in existing_ido]
    
    print(f"Finding candidates for {len(unknown_ido)} unknown Ido words...")
    print(f"Using threshold: {threshold}, k: {k}")
    
    candidates = []
    
    for ido_word in tqdm(unknown_ido, desc="Processing"):
        ido_idx = ido_to_idx[ido_word]
        ido_vec = ido_vecs[ido_idx]
        
        # Find nearest neighbors using CSLS
        csls_scores = csls(ido_vec, epo_vecs, k=k)
        
        # Get top-k candidates
        top_k_idx = np.argsort(-csls_scores)[:k]
        
        for idx in top_k_idx:
            similarity = csls_scores[idx]
            
            if similarity < threshold:
                continue
            
            epo_word = epo_words[idx]
            
            # Check mutual nearest neighbor
            reverse_csls = csls(epo_vecs[idx], ido_vecs, k=k)
            reverse_top_k = np.argsort(-reverse_csls)[:k]
            is_mutual = ido_idx in reverse_top_k
            
            # Calculate confidence
            confidence = similarity + (0.1 if is_mutual else 0)
            
            candidates.append({
                'ido': ido_word,
                'epo': epo_word,
                'similarity': float(similarity),
                'mutual': is_mutual,
                'confidence': float(confidence)
            })
    
    # Sort by confidence
    candidates.sort(key=lambda x: x['confidence'], reverse=True)
    
    print(f"Found {len(candidates)} candidates")
    return candidates

def save_candidates(candidates, output_file):
    """Save candidates to file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Ido\tEsperanto\tSimilarity\tMutual\tConfidence\n")
        for c in candidates:
            f.write(f"{c['ido']}\t{c['epo']}\t{c['similarity']:.4f}\t"
                   f"{c['mutual']}\t{c['confidence']:.4f}\n")
    print(f"Candidates saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Find translation candidates')
    parser.add_argument('--threshold', type=float, default=0.7,
                       help='Similarity threshold (default: 0.7)')
    parser.add_argument('--k', type=int, default=10,
                       help='Number of nearest neighbors (default: 10)')
    args = parser.parse_args()
    
    # Paths
    models_dir = Path('models')
    dict_dir = Path('data/dictionaries')
    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)
    
    # Load embeddings
    ido_words, ido_vecs, ido_to_idx = load_embeddings(
        models_dir / 'ido_aligned.vec')
    epo_words, epo_vecs, epo_to_idx = load_embeddings(
        models_dir / 'epo_aligned.vec')
    
    # Load existing dictionary
    dict_file = dict_dir / 'seed_dictionary_50k.txt'
    if not dict_file.exists():
        # Try alternative names
        dict_file = dict_dir / 'train_45k.txt'
    
    if dict_file.exists():
        existing_dict = load_dictionary(dict_file)
        print(f"Loaded {len(existing_dict)} existing translations")
    else:
        print("Warning: No existing dictionary found, processing all words")
        existing_dict = set()
    
    # Find candidates
    candidates = find_candidates(
        ido_words, ido_vecs, ido_to_idx,
        epo_words, epo_vecs, epo_to_idx,
        existing_dict,
        threshold=args.threshold,
        k=args.k
    )
    
    # Save results
    output_file = results_dir / f'candidates_threshold_{args.threshold}.txt'
    save_candidates(candidates, output_file)
    
    # Print summary
    print("\n=== Summary ===")
    print(f"Total candidates: {len(candidates)}")
    high_conf = sum(1 for c in candidates if c['confidence'] >= 0.8)
    mutual = sum(1 for c in candidates if c['mutual'])
    print(f"High confidence (≥0.8): {high_conf}")
    print(f"Mutual nearest neighbors: {mutual}")
    print(f"\nTop 10 candidates:")
    for c in candidates[:10]:
        print(f"  {c['ido']:15} → {c['epo']:15} "
              f"(conf: {c['confidence']:.3f}, mutual: {c['mutual']})")

if __name__ == '__main__':
    main()
