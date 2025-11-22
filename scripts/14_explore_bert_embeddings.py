#!/usr/bin/env python3
"""
Explore BERT embeddings by finding nearest neighbors for words.
"""

import argparse
import numpy as np
import torch
from pathlib import Path
from transformers import XLMRobertaModel, XLMRobertaTokenizer
from sklearn.metrics.pairwise import cosine_similarity
import sys


def load_model(model_path):
    """Load the fine-tuned BERT model and tokenizer."""
    print(f"Loading model from {model_path}...")
    tokenizer = XLMRobertaTokenizer.from_pretrained(model_path)
    model = XLMRobertaModel.from_pretrained(model_path)
    model.eval()
    
    # Move to GPU if available
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    print(f"Model loaded on {device}")
    
    return model, tokenizer, device


def get_word_embedding(word, model, tokenizer, device):
    """Get the embedding for a single word."""
    # Tokenize the word
    tokens = tokenizer(word, return_tensors='pt', add_special_tokens=True)
    tokens = {k: v.to(device) for k, v in tokens.items()}
    
    # Get embeddings
    with torch.no_grad():
        outputs = model(**tokens)
        # Use the mean of all token embeddings (excluding special tokens)
        embeddings = outputs.last_hidden_state[0, 1:-1, :].mean(dim=0)
    
    return embeddings.cpu().numpy()


def load_vocabulary(corpus_path, max_words=10000):
    """Load vocabulary from corpus."""
    print(f"Loading vocabulary from {corpus_path}...")
    
    word_counts = {}
    with open(corpus_path, 'r', encoding='utf-8') as f:
        for line in f:
            words = line.strip().split()
            for word in words:
                word = word.lower()
                word_counts[word] = word_counts.get(word, 0) + 1
    
    # Sort by frequency and take top N
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    vocab = [word for word, count in sorted_words[:max_words]]
    
    print(f"Loaded {len(vocab)} words")
    return vocab


def build_embedding_matrix(vocab, model, tokenizer, device, save_path=None):
    """Build embedding matrix for vocabulary."""
    print(f"Building embedding matrix for {len(vocab)} words...")
    
    embeddings = []
    valid_words = []
    
    for i, word in enumerate(vocab):
        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(vocab)} words...")
        
        try:
            emb = get_word_embedding(word, model, tokenizer, device)
            embeddings.append(emb)
            valid_words.append(word)
        except Exception as e:
            print(f"  Warning: Failed to get embedding for '{word}': {e}")
    
    embedding_matrix = np.array(embeddings)
    
    if save_path:
        print(f"Saving embeddings to {save_path}...")
        np.savez(save_path, embeddings=embedding_matrix, words=valid_words)
    
    return embedding_matrix, valid_words


def find_nearest_neighbors(query_word, embedding_matrix, vocab, model, tokenizer, device, top_k=10):
    """Find nearest neighbors for a query word."""
    # Get query embedding
    query_emb = get_word_embedding(query_word, model, tokenizer, device).reshape(1, -1)
    
    # Compute similarities
    similarities = cosine_similarity(query_emb, embedding_matrix)[0]
    
    # Get top K indices
    top_indices = np.argsort(similarities)[::-1][:top_k]
    
    # Return results
    results = []
    for idx in top_indices:
        results.append({
            'word': vocab[idx],
            'similarity': similarities[idx]
        })
    
    return results


def interactive_mode(model, tokenizer, device, embedding_matrix, vocab):
    """Interactive mode for exploring embeddings."""
    print("\n" + "="*60)
    print("Interactive Embedding Explorer")
    print("="*60)
    print("Enter a word to find its nearest neighbors.")
    print("Type 'quit' or 'exit' to quit.\n")
    
    while True:
        try:
            word = input("Enter word: ").strip().lower()
            
            if word in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not word:
                continue
            
            print(f"\nNearest neighbors for '{word}':")
            print("-" * 60)
            
            results = find_nearest_neighbors(
                word, embedding_matrix, vocab, model, tokenizer, device, top_k=20
            )
            
            for i, result in enumerate(results, 1):
                print(f"{i:2d}. {result['word']:20s} (similarity: {result['similarity']:.4f})")
            
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(description='Explore BERT embeddings')
    parser.add_argument('--model', required=True, help='Path to fine-tuned model')
    parser.add_argument('--corpus', required=True, help='Path to corpus file')
    parser.add_argument('--word', help='Query word (if not provided, enters interactive mode)')
    parser.add_argument('--top-k', type=int, default=20, help='Number of nearest neighbors')
    parser.add_argument('--vocab-size', type=int, default=10000, help='Vocabulary size')
    parser.add_argument('--save-embeddings', help='Path to save embeddings')
    parser.add_argument('--load-embeddings', help='Path to load pre-computed embeddings')
    
    args = parser.parse_args()
    
    # Load model
    model, tokenizer, device = load_model(args.model)
    
    # Load or build embeddings
    if args.load_embeddings and Path(args.load_embeddings).exists():
        print(f"Loading pre-computed embeddings from {args.load_embeddings}...")
        data = np.load(args.load_embeddings)
        embedding_matrix = data['embeddings']
        vocab = data['words'].tolist()
        print(f"Loaded {len(vocab)} words")
    else:
        # Load vocabulary
        vocab = load_vocabulary(args.corpus, max_words=args.vocab_size)
        
        # Build embedding matrix
        embedding_matrix, vocab = build_embedding_matrix(
            vocab, model, tokenizer, device, 
            save_path=args.save_embeddings
        )
    
    # Query mode or interactive mode
    if args.word:
        print(f"\nNearest neighbors for '{args.word}':")
        print("-" * 60)
        
        results = find_nearest_neighbors(
            args.word, embedding_matrix, vocab, model, tokenizer, device, top_k=args.top_k
        )
        
        for i, result in enumerate(results, 1):
            print(f"{i:2d}. {result['word']:20s} (similarity: {result['similarity']:.4f})")
    else:
        interactive_mode(model, tokenizer, device, embedding_matrix, vocab)


if __name__ == '__main__':
    main()

