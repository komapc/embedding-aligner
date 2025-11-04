#!/usr/bin/env python3
"""
Step 2: Train Ido word embeddings using FastText.

Input:
    - data/processed/ido_clean.txt

Output:
    - models/ido_fasttext.model
    - models/ido_fasttext.model.wv.vectors.npy
"""

import logging
from pathlib import Path
from gensim.models import FastText
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
    # TODO: Implement sentence loading
    # - Read file line by line
    # - Split into tokens
    # - Yield token list
    pass


def train_embeddings(
    corpus_path: Path,
    output_path: Path,
    vector_size: int = 300,
    window: int = 5,
    min_count: int = 5,
    epochs: int = 10,
    workers: int = 4
) -> FastText:
    """
    Train FastText embeddings.
    
    Args:
        corpus_path: Path to cleaned corpus
        output_path: Path to save model
        vector_size: Embedding dimension
        window: Context window size
        min_count: Minimum word frequency
        epochs: Number of training epochs
        workers: Number of CPU workers
        
    Returns:
        Trained FastText model
    """
    # TODO: Implement embedding training
    # - Load sentences
    # - Initialize FastText model
    # - Train with progress logging
    # - Save model
    # - Return model
    pass


def evaluate_embeddings(model: FastText, test_words: list):
    """
    Quick evaluation of trained embeddings.
    
    Args:
        model: Trained FastText model
        test_words: List of words to test
    """
    # TODO: Implement evaluation
    # - Check vocabulary size
    # - Test similarity queries
    # - Show most similar words for test cases
    pass


def main():
    """Main execution function."""
    logger.info("Starting Ido embedding training...")
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    corpus_path = base_dir / 'data' / 'processed' / 'ido_clean.txt'
    models_dir = base_dir / 'models'
    models_dir.mkdir(parents=True, exist_ok=True)
    output_path = models_dir / 'ido_fasttext.model'
    
    # Check if corpus exists
    if not corpus_path.exists():
        logger.error(f"Corpus not found at {corpus_path}")
        logger.error("Please run 01_prepare_corpora.py first")
        return
    
    # Train embeddings
    logger.info(f"Training embeddings from {corpus_path}")
    model = train_embeddings(
        corpus_path=corpus_path,
        output_path=output_path,
        vector_size=300,
        window=5,
        min_count=5,
        epochs=10,
        workers=4
    )
    
    # Evaluate
    test_words = ['hundo', 'kato', 'esar', 'irar', 'bona']
    logger.info("Evaluating embeddings...")
    evaluate_embeddings(model, test_words)
    
    logger.info(f"Model saved to {output_path}")
    logger.info("Ido embedding training complete!")


if __name__ == '__main__':
    main()
