#!/usr/bin/env python3
"""
Extract word embeddings from fine-tuned BERT model.

Usage:
    python scripts/14_extract_bert_embeddings.py \
        --model models/bert-ido-finetuned \
        --vocab data/ido_vocabulary.txt \
        --output models/ido_bert_embeddings.npy \
        --batch-size 32

Expected time: 15-30 minutes for 95K vocabulary
"""

import argparse
import logging
import numpy as np
import torch
from pathlib import Path
from typing import List, Dict
from transformers import XLMRobertaModel, XLMRobertaTokenizer
from tqdm import tqdm

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_vocabulary(vocab_path: Path) -> List[str]:
    """Load vocabulary file (one word per line)."""
    logger.info(f"Loading vocabulary from {vocab_path}")
    
    with open(vocab_path, 'r', encoding='utf-8') as f:
        words = [line.strip() for line in f if line.strip()]
    
    logger.info(f"Loaded {len(words):,} words")
    return words


def extract_embeddings(
    model,
    tokenizer,
    words: List[str],
    batch_size: int = 32,
    device: str = "cuda"
) -> Dict[str, np.ndarray]:
    """
    Extract BERT embeddings for a list of words.
    
    For multi-subword tokens, averages the embeddings.
    """
    logger.info(f"Extracting embeddings for {len(words):,} words")
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Device: {device}")
    
    model = model.to(device)
    model.eval()
    
    embeddings = {}
    
    with torch.no_grad():
        for i in tqdm(range(0, len(words), batch_size), desc="Extracting"):
            batch_words = words[i:i+batch_size]
            
            # Tokenize batch
            inputs = tokenizer(
                batch_words,
                padding=True,
                truncation=True,
                max_length=32,  # Words shouldn't be longer
                return_tensors="pt"
            ).to(device)
            
            # Get embeddings
            outputs = model(**inputs)
            last_hidden = outputs.last_hidden_state  # [batch, seq_len, hidden_size]
            
            # Average subword embeddings (excluding padding/special tokens)
            for j, word in enumerate(batch_words):
                # Get attention mask for this word
                mask = inputs['attention_mask'][j]  # [seq_len]
                
                # Get embeddings for non-padding tokens
                word_embeddings = last_hidden[j][mask == 1]  # [num_tokens, hidden_size]
                
                # Exclude [CLS] and [SEP] tokens (first and last)
                if len(word_embeddings) > 2:
                    word_embeddings = word_embeddings[1:-1]
                
                # Average
                avg_embedding = word_embeddings.mean(dim=0).cpu().numpy()
                embeddings[word] = avg_embedding
    
    logger.info(f"Extracted {len(embeddings):,} embeddings")
    return embeddings


def save_embeddings(
    embeddings: Dict[str, np.ndarray],
    output_path: Path,
    vocab_path: Path
):
    """Save embeddings as numpy array with vocabulary file."""
    logger.info(f"Saving embeddings to {output_path}")
    
    # Create embedding matrix
    words = list(embeddings.keys())
    matrix = np.array([embeddings[w] for w in words])
    
    # Save
    np.save(output_path, matrix)
    
    # Save vocabulary
    vocab_file = vocab_path
    with open(vocab_file, 'w', encoding='utf-8') as f:
        for word in words:
            f.write(f"{word}\n")
    
    logger.info(f"Saved {len(words):,} embeddings")
    logger.info(f"Matrix shape: {matrix.shape}")
    logger.info(f"Vocabulary saved to {vocab_file}")


def main():
    parser = argparse.ArgumentParser(description='Extract BERT embeddings')
    parser.add_argument('--model', required=True, type=Path,
                        help='Path to fine-tuned BERT model')
    parser.add_argument('--vocab', required=True, type=Path,
                        help='Path to vocabulary file (one word per line)')
    parser.add_argument('--output', required=True, type=Path,
                        help='Output path for embeddings (.npy)')
    parser.add_argument('--batch-size', type=int, default=32,
                        help='Batch size (default: 32)')
    
    args = parser.parse_args()
    
    # Check GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    
    # Load model
    logger.info("Loading fine-tuned model...")
    model = XLMRobertaModel.from_pretrained(str(args.model))
    tokenizer = XLMRobertaTokenizer.from_pretrained(str(args.model))
    
    # Load vocabulary
    words = load_vocabulary(args.vocab)
    
    # Extract embeddings
    embeddings = extract_embeddings(model, tokenizer, words, args.batch_size, device)
    
    # Save
    vocab_output = args.output.parent / f"{args.output.stem}_vocab.txt"
    save_embeddings(embeddings, args.output, vocab_output)
    
    logger.info("✅ Done!")


if __name__ == '__main__':
    main()

