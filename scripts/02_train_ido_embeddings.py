#!/usr/bin/env python3
"""
Step 2: Train Ido word embeddings with configurable model type.

Supported models:
    - fasttext: FastText with character n-grams (default)
    - fasttext-no-ngrams: FastText without character n-grams
    - word2vec: Word2Vec skip-gram

Input:
    - data/processed/ido_clean.txt

Output:
    - models/ido_{model_type}.model
"""

import argparse
import logging
from pathlib import Path
from gensim.models import FastText, Word2Vec
from gensim.models.callbacks import CallbackAny2Vec

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EpochLogger(CallbackAny2Vec):
    """Callback to log training progress."""
    
    def __init__(self):
        self.epoch = 0
    
    def on_epoch_end(self, model):
        self.epoch += 1
        logger.info(f"Epoch {self.epoch} completed")


def load_sentences(corpus_path: Path):
    """
    Load and yield sentences from corpus.
    
    Args:
        corpus_path: Path to cleaned corpus file
        
    Yields:
        List of tokens for each sentence
    """
    with open(corpus_path, 'r', encoding='utf-8') as f:
        for line in f:
            tokens = line.strip().split()
            if tokens:
                yield tokens


def train_embeddings(
    corpus_path: Path,
    output_path: Path,
    model_type: str = 'fasttext',
    vector_size: int = 300,
    window: int = 5,
    min_count: int = 20,
    epochs: int = 10,
    workers: int = 4
):
    """
    Train word embeddings with specified model type.
    
    Args:
        corpus_path: Path to cleaned corpus
        output_path: Path to save model
        model_type: 'fasttext', 'fasttext-no-ngrams', or 'word2vec'
        vector_size: Embedding dimension
        window: Context window size
        min_count: Minimum word frequency
        epochs: Number of training epochs
        workers: Number of CPU workers
        
    Returns:
        Trained model
    """
    logger.info("Loading sentences...")
    sentences = list(load_sentences(corpus_path))
    logger.info(f"Loaded {len(sentences)} sentences")
    
    logger.info(f"Initializing {model_type} model...")
    
    if model_type == 'fasttext':
        # FastText with character n-grams
        model = FastText(
            vector_size=vector_size,
            window=window,
            min_count=min_count,
            workers=workers,
            sg=1,  # Skip-gram
            min_n=3,  # Character n-gram min
            max_n=6,  # Character n-gram max
            epochs=epochs,
            callbacks=[EpochLogger()]
        )
    elif model_type == 'fasttext-no-ngrams':
        # FastText without character n-grams
        model = FastText(
            vector_size=vector_size,
            window=window,
            min_count=min_count,
            workers=workers,
            sg=1,  # Skip-gram
            min_n=0,  # Disable character n-grams
            max_n=0,
            epochs=epochs,
            callbacks=[EpochLogger()]
        )
    elif model_type == 'word2vec':
        # Word2Vec (no subword information)
        model = Word2Vec(
            vector_size=vector_size,
            window=window,
            min_count=min_count,
            workers=workers,
            sg=1,  # Skip-gram
            epochs=epochs,
            callbacks=[EpochLogger()]
        )
    else:
        raise ValueError(f"Unknown model type: {model_type}")
    
    logger.info("Building vocabulary...")
    model.build_vocab(sentences)
    logger.info(f"Vocabulary size: {len(model.wv)}")
    
    logger.info(f"Training for {epochs} epochs...")
    model.train(
        sentences,
        total_examples=len(sentences),
        epochs=epochs
    )
    
    logger.info(f"Saving model to {output_path}")
    model.save(str(output_path))
    
    return model


def evaluate_embeddings(model, test_words: list):
    """
    Quick evaluation of trained embeddings.
    
    Args:
        model: Trained FastText model
        test_words: List of words to test
    """
    logger.info(f"Vocabulary size: {len(model.wv)}")
    logger.info(f"Vector dimension: {model.wv.vector_size}")
    
    logger.info("\nTesting word similarities:")
    for word in test_words:
        if word in model.wv:
            similar = model.wv.most_similar(word, topn=5)
            logger.info(f"\n'{word}' most similar words:")
            for sim_word, score in similar:
                logger.info(f"  {sim_word}: {score:.3f}")
        else:
            logger.warning(f"'{word}' not in vocabulary")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Train Ido word embeddings with configurable model type'
    )
    parser.add_argument(
        '--model-type',
        choices=['fasttext', 'fasttext-no-ngrams', 'word2vec'],
        default='fasttext',
        help='Model type to train (default: fasttext)'
    )
    parser.add_argument('--vector-size', type=int, default=300, help='Embedding dimension')
    parser.add_argument('--window', type=int, default=5, help='Context window size')
    parser.add_argument('--min-count', type=int, default=20, help='Minimum word frequency')
    parser.add_argument('--epochs', type=int, default=10, help='Number of training epochs')
    parser.add_argument('--workers', type=int, default=4, help='Number of CPU workers')
    
    args = parser.parse_args()
    
    logger.info(f"Starting Ido embedding training with {args.model_type}...")
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    corpus_path = base_dir / 'data' / 'processed' / 'ido_clean.txt'
    models_dir = base_dir / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)
    output_path = models_dir / f'ido_{args.model_type.replace("-", "_")}.model'
    
    # Check if corpus exists
    if not corpus_path.exists():
        logger.error(f"Corpus not found at {corpus_path}")
        logger.error("Please run 01_prepare_corpora.py first")
        return
    
    # Train embeddings
    logger.info(f"Training embeddings from {corpus_path}")
    logger.info(f"Parameters: vector_size={args.vector_size}, window={args.window}, "
                f"min_count={args.min_count}, epochs={args.epochs}")
    
    model = train_embeddings(
        corpus_path=corpus_path,
        output_path=output_path,
        model_type=args.model_type,
        vector_size=args.vector_size,
        window=args.window,
        min_count=args.min_count,
        epochs=args.epochs,
        workers=args.workers
    )
    
    # Evaluate
    test_words = ['hundo', 'kato', 'esar', 'irar', 'bona', 'linguo', 'programo']
    logger.info("Evaluating embeddings...")
    evaluate_embeddings(model, test_words)
    
    logger.info(f"Model saved to {output_path}")
    logger.info(f"Ido embedding training complete ({args.model_type})!")


if __name__ == '__main__':
    main()
