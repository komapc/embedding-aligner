#!/usr/bin/env python3
"""
Query nearest words from trained word embedding models.
Usage: python3 query_nearest_words.py <model_path> <word> [--topn 10]
"""

import argparse
from gensim.models import Word2Vec
import sys

def query_nearest_words(model_path, word, topn=10):
    """Load model and find nearest words."""
    print(f"Loading model from: {model_path}")
    try:
        model = Word2Vec.load(model_path)
        print(f"✅ Model loaded successfully!")
        print(f"   Vocabulary size: {len(model.wv)}")
        print(f"   Vector dimensions: {model.wv.vector_size}")
        print(f"\n{'='*60}")
        
        # Check if word exists in vocabulary
        if word not in model.wv:
            print(f"❌ Word '{word}' not found in vocabulary!")
            
            # Try to find similar words
            print(f"\n🔍 Searching for similar words containing '{word}'...")
            similar = [w for w in model.wv.index_to_key if word in w.lower()][:10]
            if similar:
                print(f"   Found: {', '.join(similar)}")
            else:
                print(f"   No similar words found.")
            return
        
        # Get nearest words
        print(f"\n🎯 Nearest words to '{word}':")
        print(f"{'='*60}")
        
        nearest = model.wv.most_similar(word, topn=topn)
        
        for i, (similar_word, similarity) in enumerate(nearest, 1):
            bar_length = int(similarity * 40)
            bar = '█' * bar_length + '░' * (40 - bar_length)
            print(f"{i:2d}. {similar_word:20s} │ {bar} │ {similarity:.4f}")
        
        print(f"{'='*60}\n")
        
    except FileNotFoundError:
        print(f"❌ Error: Model file not found at {model_path}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description='Query nearest words from word embedding models'
    )
    parser.add_argument('model', help='Path to the trained model file')
    parser.add_argument('word', help='Word to query')
    parser.add_argument('--topn', type=int, default=10, 
                       help='Number of nearest words to return (default: 10)')
    
    args = parser.parse_args()
    
    query_nearest_words(args.model, args.word, args.topn)

if __name__ == '__main__':
    main()

