#!/usr/bin/env python3
"""
Complete pipeline for Ido↔Esperanto translation using fine-tuned BERT.

Steps:
1. Extract Esperanto embeddings from fine-tuned XLM-RoBERTa
2. Create automatic seed dictionary (cognates/similar words)
3. Align Ido and Esperanto embedding spaces using Procrustes
4. Find translation candidates
5. Validate and save results
"""

import argparse
import json
import numpy as np
import torch
from pathlib import Path
from transformers import XLMRobertaModel, XLMRobertaTokenizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.spatial.distance import cdist
from scipy.linalg import orthogonal_procrustes
from gensim.models import Word2Vec
from tqdm import tqdm
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_model(model_path):
    """Load fine-tuned BERT model."""
    logger.info(f"Loading model from {model_path}...")
    tokenizer = XLMRobertaTokenizer.from_pretrained(model_path)
    model = XLMRobertaModel.from_pretrained(model_path)
    model.eval()
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    logger.info(f"Model loaded on {device}")
    
    return model, tokenizer, device


def get_word_embedding(word, model, tokenizer, device):
    """Get embedding for a single word."""
    tokens = tokenizer(word, return_tensors='pt', add_special_tokens=True)
    tokens = {k: v.to(device) for k, v in tokens.items()}
    
    with torch.no_grad():
        outputs = model(**tokens)
        # Mean pooling of token embeddings (excluding special tokens)
        embeddings = outputs.last_hidden_state[0, 1:-1, :].mean(dim=0)
    
    return embeddings.cpu().numpy()


def load_ido_embeddings(npz_path):
    """Load pre-computed Ido embeddings."""
    logger.info(f"Loading Ido embeddings from {npz_path}...")
    data = np.load(npz_path)
    embeddings = data['embeddings']
    words = data['words'].tolist()
    word_to_idx = {word: idx for idx, word in enumerate(words)}
    logger.info(f"Loaded {len(words):,} Ido words")
    return embeddings, words, word_to_idx


def load_esperanto_vocab(model_path=None, vocab_path=None, max_words=10000):
    """Load Esperanto vocabulary from Word2Vec model or vocab file."""
    if vocab_path and Path(vocab_path).exists():
        logger.info(f"Loading Esperanto vocab from {vocab_path}...")
        with open(vocab_path, 'r', encoding='utf-8') as f:
            words = [line.strip() for line in f][:max_words]
    elif model_path and Path(model_path).exists():
        logger.info(f"Loading Esperanto vocab from Word2Vec model {model_path}...")
        w2v_model = Word2Vec.load(str(model_path))
        words = list(w2v_model.wv.key_to_index.keys())[:max_words]
    else:
        raise ValueError("Must provide either model_path or vocab_path")
    
    logger.info(f"Loaded {len(words):,} Esperanto words")
    return words


def extract_esperanto_embeddings(epo_vocab, model, tokenizer, device, save_path=None):
    """Extract Esperanto embeddings from fine-tuned BERT."""
    logger.info(f"\nExtracting Esperanto embeddings for {len(epo_vocab):,} words...")
    
    embeddings = []
    valid_words = []
    
    for i, word in enumerate(tqdm(epo_vocab, desc="Extracting")):
        if (i + 1) % 500 == 0:
            logger.info(f"  Processed {i + 1:,}/{len(epo_vocab):,} words...")
        
        try:
            emb = get_word_embedding(word, model, tokenizer, device)
            embeddings.append(emb)
            valid_words.append(word)
        except Exception as e:
            logger.warning(f"  Failed for '{word}': {e}")
    
    embedding_matrix = np.array(embeddings)
    
    if save_path:
        logger.info(f"Saving Esperanto embeddings to {save_path}...")
        np.savez(save_path, embeddings=embedding_matrix, words=valid_words)
    
    logger.info(f"✅ Extracted {len(valid_words):,} Esperanto embeddings")
    return embedding_matrix, valid_words


def create_seed_dictionary(ido_words, epo_words, min_similarity=0.7, max_pairs=500):
    """
    Create seed dictionary by finding cognates (similar words).
    This works well for Ido↔Esperanto due to their shared vocabulary.
    """
    logger.info(f"\nCreating seed dictionary (cognates)...")
    logger.info(f"Ido vocab: {len(ido_words):,}, Esperanto vocab: {len(epo_words):,}")
    
    seed_pairs = []
    
    # Convert to sets for faster lookup
    ido_set = set(ido_words)
    epo_set = set(epo_words)
    
    # 1. Exact matches (identical words)
    exact_matches = ido_set & epo_set
    for word in exact_matches:
        seed_pairs.append((word, word))
    
    logger.info(f"  Found {len(exact_matches):,} exact matches")
    
    # 2. Near matches (edit distance 1-2)
    from difflib import SequenceMatcher
    
    remaining_ido = ido_set - exact_matches
    remaining_epo = epo_set - exact_matches
    
    for ido_word in tqdm(list(remaining_ido), desc="Finding cognates"):
        if len(seed_pairs) >= max_pairs:
            break
        
        for epo_word in remaining_epo:
            # Skip if very different lengths
            if abs(len(ido_word) - len(epo_word)) > 2:
                continue
            
            # Compute similarity
            similarity = SequenceMatcher(None, ido_word, epo_word).ratio()
            
            if similarity >= min_similarity:
                seed_pairs.append((ido_word, epo_word))
                remaining_epo.discard(epo_word)
                break
    
    logger.info(f"  Found {len(seed_pairs) - len(exact_matches):,} near matches")
    logger.info(f"✅ Total seed pairs: {len(seed_pairs):,}")
    
    return seed_pairs[:max_pairs]


def align_embeddings_procrustes(ido_emb, ido_words, ido_idx, epo_emb, epo_words, epo_idx, seed_pairs):
    """
    Align Ido and Esperanto embeddings using Procrustes alignment.
    This finds an orthogonal transformation matrix W such that X @ W ≈ Y.
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"PROCRUSTES ALIGNMENT")
    logger.info(f"{'='*60}")
    logger.info(f"Seed pairs: {len(seed_pairs):,}")
    
    # Build paired matrices
    X_pairs = []  # Ido
    Y_pairs = []  # Esperanto
    
    for ido_word, epo_word in seed_pairs:
        if ido_word in ido_idx and epo_word in epo_idx:
            X_pairs.append(ido_emb[ido_idx[ido_word]])
            Y_pairs.append(epo_emb[epo_idx[epo_word]])
    
    X = np.array(X_pairs)
    Y = np.array(Y_pairs)
    
    logger.info(f"X (Ido) shape: {X.shape}")
    logger.info(f"Y (Esperanto) shape: {Y.shape}")
    
    # Compute initial similarity
    initial_sims = []
    for i in range(len(X)):
        sim = np.dot(X[i], Y[i]) / (np.linalg.norm(X[i]) * np.linalg.norm(Y[i]))
        initial_sims.append(sim)
    
    initial_mean = np.mean(initial_sims)
    logger.info(f"Initial mean cosine similarity: {initial_mean:.4f}")
    
    # Compute Procrustes transformation: X @ W ≈ Y
    logger.info("Computing orthogonal Procrustes transformation...")
    W, scale = orthogonal_procrustes(X, Y)
    
    # Apply transformation to all Ido embeddings
    ido_aligned = ido_emb @ W
    
    # Normalize
    ido_aligned = ido_aligned / (np.linalg.norm(ido_aligned, axis=1, keepdims=True) + 1e-8)
    epo_normalized = epo_emb / (np.linalg.norm(epo_emb, axis=1, keepdims=True) + 1e-8)
    
    # Compute final similarity
    X_aligned = ido_aligned[[ido_idx[w] for w, _ in seed_pairs if w in ido_idx]]
    Y_normalized = epo_normalized[[epo_idx[w] for _, w in seed_pairs if w in epo_idx]]
    
    final_sims = []
    for i in range(len(X_aligned)):
        sim = np.dot(X_aligned[i], Y_normalized[i])
        final_sims.append(sim)
    
    final_mean = np.mean(final_sims)
    improvement = final_mean - initial_mean
    
    logger.info(f"\n✅ Alignment complete!")
    logger.info(f"Initial similarity: {initial_mean:.4f}")
    logger.info(f"Final similarity: {final_mean:.4f}")
    logger.info(f"Improvement: +{improvement:.4f} ({improvement/initial_mean*100:+.1f}%)")
    
    return ido_aligned, epo_normalized, W


def find_translation_candidates(ido_emb, ido_words, epo_emb, epo_words, 
                                threshold=0.80, top_k=10, batch_size=100):
    """Find translation candidates using aligned embeddings."""
    logger.info(f"\n{'='*60}")
    logger.info(f"FINDING TRANSLATION CANDIDATES")
    logger.info(f"{'='*60}")
    logger.info(f"Threshold: {threshold}")
    logger.info(f"Top-k per word: {top_k}")
    logger.info(f"Ido words: {len(ido_words):,}")
    logger.info(f"Esperanto words: {len(epo_words):,}")
    
    candidates = {}
    
    # Process in batches for efficiency
    for i in tqdm(range(0, len(ido_words), batch_size), desc="Finding candidates"):
        batch_end = min(i + batch_size, len(ido_words))
        batch_ido = ido_emb[i:batch_end]
        batch_words = ido_words[i:batch_end]
        
        # Compute similarities
        similarities = np.dot(batch_ido, epo_emb.T)
        
        # Get top-k for each word
        for j, ido_word in enumerate(batch_words):
            # Get indices above threshold
            sims = similarities[j]
            above_threshold = np.where(sims >= threshold)[0]
            
            if len(above_threshold) > 0:
                # Get top-k
                top_indices = above_threshold[np.argsort(sims[above_threshold])][::-1][:top_k]
                
                translations = []
                for idx in top_indices:
                    translations.append({
                        'epo': epo_words[idx],
                        'similarity': float(sims[idx])
                    })
                
                candidates[ido_word] = translations
    
    total_pairs = sum(len(v) for v in candidates.values())
    
    logger.info(f"\n✅ Candidate extraction complete!")
    logger.info(f"Ido words with translations: {len(candidates):,}")
    logger.info(f"Total translation pairs: {total_pairs:,}")
    logger.info(f"Average candidates per word: {total_pairs/len(candidates):.1f}")
    
    return candidates


def evaluate_sample(candidates, seed_pairs):
    """Evaluate translation quality on seed dictionary."""
    logger.info(f"\n{'='*60}")
    logger.info(f"EVALUATION ON SEED DICTIONARY")
    logger.info(f"{'='*60}")
    
    correct_at_1 = 0
    correct_at_5 = 0
    correct_at_10 = 0
    total = 0
    
    for ido_word, expected_epo in seed_pairs:
        if ido_word in candidates:
            total += 1
            predictions = [c['epo'] for c in candidates[ido_word]]
            
            if expected_epo in predictions[:1]:
                correct_at_1 += 1
            if expected_epo in predictions[:5]:
                correct_at_5 += 1
            if expected_epo in predictions[:10]:
                correct_at_10 += 1
    
    if total > 0:
        logger.info(f"Precision@1:  {correct_at_1}/{total} = {correct_at_1/total*100:.1f}%")
        logger.info(f"Precision@5:  {correct_at_5}/{total} = {correct_at_5/total*100:.1f}%")
        logger.info(f"Precision@10: {correct_at_10}/{total} = {correct_at_10/total*100:.1f}%")
    else:
        logger.warning("No seed pairs found in candidates")
    
    return {
        'p@1': correct_at_1 / total if total > 0 else 0,
        'p@5': correct_at_5 / total if total > 0 else 0,
        'p@10': correct_at_10 / total if total > 0 else 0,
        'total': total
    }


def main():
    parser = argparse.ArgumentParser(description="BERT-based Ido↔Esperanto alignment")
    parser.add_argument('--bert-model', type=Path, required=True,
                        help='Fine-tuned BERT model directory')
    parser.add_argument('--ido-embeddings', type=Path, required=True,
                        help='Pre-computed Ido embeddings (.npz)')
    parser.add_argument('--epo-vocab', type=Path,
                        help='Esperanto vocabulary file')
    parser.add_argument('--epo-model', type=Path,
                        help='Esperanto Word2Vec model (alternative to --epo-vocab)')
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='Output directory for results')
    parser.add_argument('--max-epo-words', type=int, default=10000,
                        help='Maximum Esperanto words to process')
    parser.add_argument('--seed-pairs', type=int, default=500,
                        help='Maximum seed pairs for alignment')
    parser.add_argument('--threshold', type=float, default=0.80,
                        help='Similarity threshold for candidates')
    parser.add_argument('--top-k', type=int, default=10,
                        help='Top K candidates per word')
    parser.add_argument('--skip-epo-extraction', action='store_true',
                        help='Skip Esperanto extraction if already done')
    
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Load Ido embeddings
    logger.info(f"\n{'='*60}")
    logger.info(f"STEP 1: LOAD IDO EMBEDDINGS")
    logger.info(f"{'='*60}")
    ido_emb, ido_words, ido_idx = load_ido_embeddings(args.ido_embeddings)
    
    # Step 2: Extract or load Esperanto embeddings
    logger.info(f"\n{'='*60}")
    logger.info(f"STEP 2: ESPERANTO EMBEDDINGS")
    logger.info(f"{'='*60}")
    
    epo_embeddings_path = args.output_dir / 'esperanto_bert_embeddings.npz'
    
    if args.skip_epo_extraction and epo_embeddings_path.exists():
        logger.info(f"Loading pre-extracted Esperanto embeddings...")
        epo_emb, epo_words, epo_idx = load_ido_embeddings(epo_embeddings_path)
    else:
        # Load BERT model
        model, tokenizer, device = load_model(args.bert_model)
        
        # Load Esperanto vocabulary
        epo_vocab = load_esperanto_vocab(
            model_path=args.epo_model,
            vocab_path=args.epo_vocab,
            max_words=args.max_epo_words
        )
        
        # Extract embeddings
        epo_emb, epo_words = extract_esperanto_embeddings(
            epo_vocab, model, tokenizer, device,
            save_path=epo_embeddings_path
        )
        epo_idx = {word: idx for idx, word in enumerate(epo_words)}
    
    # Step 3: Create seed dictionary
    logger.info(f"\n{'='*60}")
    logger.info(f"STEP 3: CREATE SEED DICTIONARY")
    logger.info(f"{'='*60}")
    
    seed_pairs = create_seed_dictionary(
        ido_words, epo_words,
        min_similarity=0.7,
        max_pairs=args.seed_pairs
    )
    
    # Save seed dictionary
    seed_file = args.output_dir / 'seed_dictionary.txt'
    with open(seed_file, 'w', encoding='utf-8') as f:
        for ido_word, epo_word in seed_pairs:
            f.write(f"{ido_word}\t{epo_word}\n")
    logger.info(f"Saved seed dictionary to {seed_file}")
    
    # Step 4: Align embeddings
    logger.info(f"\n{'='*60}")
    logger.info(f"STEP 4: ALIGN EMBEDDING SPACES")
    logger.info(f"{'='*60}")
    
    ido_aligned, epo_aligned, W = align_embeddings_procrustes(
        ido_emb, ido_words, ido_idx,
        epo_emb, epo_words, epo_idx,
        seed_pairs
    )
    
    # Save transformation matrix
    np.save(args.output_dir / 'procrustes_W.npy', W)
    np.save(args.output_dir / 'ido_aligned.npy', ido_aligned)
    np.save(args.output_dir / 'epo_aligned.npy', epo_aligned)
    
    # Step 5: Find translation candidates
    logger.info(f"\n{'='*60}")
    logger.info(f"STEP 5: FIND TRANSLATION CANDIDATES")
    logger.info(f"{'='*60}")
    
    candidates = find_translation_candidates(
        ido_aligned, ido_words,
        epo_aligned, epo_words,
        threshold=args.threshold,
        top_k=args.top_k
    )
    
    # Step 6: Evaluate
    eval_results = evaluate_sample(candidates, seed_pairs)
    
    # Step 7: Save results
    logger.info(f"\n{'='*60}")
    logger.info(f"SAVING RESULTS")
    logger.info(f"{'='*60}")
    
    # Save candidates
    candidates_file = args.output_dir / 'translation_candidates.json'
    logger.info(f"Saving candidates to {candidates_file}")
    with open(candidates_file, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, indent=2, ensure_ascii=False)
    
    # Save statistics
    stats = {
        'ido_vocab_size': len(ido_words),
        'epo_vocab_size': len(epo_words),
        'seed_pairs': len(seed_pairs),
        'threshold': args.threshold,
        'top_k': args.top_k,
        'candidates_found': len(candidates),
        'total_pairs': sum(len(v) for v in candidates.values()),
        'evaluation': eval_results
    }
    
    stats_file = args.output_dir / 'alignment_stats.json'
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ PIPELINE COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Results saved to: {args.output_dir}")
    logger.info(f"Candidates: {len(candidates):,} Ido words")
    logger.info(f"Total pairs: {stats['total_pairs']:,}")
    logger.info(f"Precision@1: {eval_results['p@1']*100:.1f}%")
    logger.info(f"Precision@5: {eval_results['p@5']*100:.1f}%")
    logger.info(f"Precision@10: {eval_results['p@10']*100:.1f}%")


if __name__ == '__main__':
    main()

