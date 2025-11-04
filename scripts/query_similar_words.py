#!/usr/bin/env python3
"""
Query tool to find similar words in trained embeddings.

Usage:
    python3 query_similar_words.py <word> [--topn 10]
"""

import sys
import argparse
from pathlib import Path
from gensim.models import FastText
from gensim.models.callbacks import CallbackAny2Vec


class EpochLogger(CallbackAny2Vec):
    """Callback to log training progress (needed for model loading)."""
    def __init__(self):
        self.epoch = 0
    def on_epoch_end(self, model):
        self.epoch += 1


def find_similar_words(model_path: Path, word: str, topn: int = 10):
    """
    Find most similar words to a given word.
    
    Args:
        model_path: Path to FastText model
        word: Query word
        topn: Number of similar words to return
    """
    print(f"Loading model from {model_path}...")
    model = FastText.load(str(model_path))
    
    print(f"\nVocabulary size: {len(model.wv):,} words")
    print(f"Vector dimension: {model.wv.vector_size}")
    
    if word not in model.wv:
        print(f"\n⚠️  Word '{word}' not in vocabulary")
        print(f"Trying with FastText character n-grams...")
        # FastText can still generate vectors for OOV words
        try:
            similar = model.wv.most_similar(word, topn=topn)
            print(f"\n✓ Generated vector using character n-grams")
            word_count = "N/A (OOV)"
        except Exception as e:
            print(f"❌ Cannot generate vector for '{word}': {e}")
            return
    else:
        similar = model.wv.most_similar(word, topn=topn)
        word_count = model.wv.get_vecattr(word, 'count')
        print(f"✓ Word '{word}' found (frequency: {word_count})")
    
    print(f"\nTop {topn} most similar words to '{word}':")
    print("-" * 50)
    for i, (sim_word, score) in enumerate(similar, 1):
        freq = model.wv.get_vecattr(sim_word, 'count')
        print(f"{i:2d}. {sim_word:20s} similarity: {score:.4f}  freq: {freq:6d}")


def main():
    parser = argparse.ArgumentParser(
        description='Find similar words in trained embeddings'
    )
    parser.add_argument('word', help='Word to query')
    parser.add_argument('--topn', type=int, default=10, 
                       help='Number of similar words to return (default: 10)')
    parser.add_argument('--model', default='models/ido_fasttext.model',
                       help='Path to model file')
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    model_path = base_dir / args.model
    
    if not model_path.exists():
        print(f"❌ Model not found at {model_path}")
        print("Please train the model first with: python3 scripts/02_train_ido_embeddings.py")
        sys.exit(1)
    
    find_similar_words(model_path, args.word, args.topn)


if __name__ == '__main__':
    main()
