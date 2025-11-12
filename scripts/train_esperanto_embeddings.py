#!/usr/bin/env python3
"""
Train Esperanto word embeddings using combined-best configuration.

Based on the successful Ido configuration:
- Algorithm: Word2Vec Skip-gram
- Vector size: 300 dimensions
- Window: 5 (focused context)
- Min count: 15 (remove rare words)
- Sample: 1e-5 (balance frequent words)
- Filter proper nouns: Yes
- Negative samples: 10
- Epochs: 30

Expected corpus: ~293M words, ~11.6M sentences
Expected training time: 15-20 hours on t3.small
Expected vocabulary: 200K-300K words
"""

import argparse
import logging
import string
import time
from pathlib import Path
from gensim.models import Word2Vec
from gensim.models.callbacks import CallbackAny2Vec

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EpochLogger(CallbackAny2Vec):
    """Callback to log training progress."""
    def __init__(self):
        self.epoch = 0
        self.epoch_start_time = None
        
    def on_epoch_begin(self, model):
        self.epoch_start_time = time.time()
        logger.info(f"Starting epoch {self.epoch + 1}")
    
    def on_epoch_end(self, model):
        self.epoch += 1
        epoch_time = time.time() - self.epoch_start_time
        logger.info(f"Epoch {self.epoch} completed in {epoch_time:.2f} seconds")


def is_proper_noun(word):
    """Detect proper nouns (capitalized words)."""
    if not word:
        return False
    # Check if first letter is uppercase and word is longer than 1 char
    return word[0].isupper() and len(word) > 1 and word.isalpha()


def load_sentences(corpus_path: Path, filter_proper: bool = False):
    """
    Load sentences from corpus file.
    
    Yields tokenized sentences with optional proper noun filtering.
    """
    logger.info(f"Loading corpus from {corpus_path}")
    logger.info(f"Filter proper nouns: {filter_proper}")
    
    sentence_count = 0
    word_count = 0
    
    with open(corpus_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Strip punctuation from each token
            tokens = [token.strip(string.punctuation) for token in line.strip().split()]
            # Filter out empty tokens
            tokens = [t for t in tokens if t]
            
            # Optionally filter proper nouns
            if filter_proper:
                tokens = [t for t in tokens if not is_proper_noun(t)]
            
            if tokens:
                word_count += len(tokens)
                sentence_count += 1
                
                # Log progress every 100K sentences
                if sentence_count % 100000 == 0:
                    logger.info(f"Loaded {sentence_count:,} sentences ({word_count:,} words)")
                
                yield tokens
    
    logger.info(f"Corpus loaded: {sentence_count:,} sentences, {word_count:,} words")


def train_embeddings(
    corpus_path: Path,
    output_path: Path,
    config: dict
):
    """Train word embeddings with specified configuration."""
    
    logger.info("="*60)
    logger.info("ESPERANTO EMBEDDING TRAINING")
    logger.info("="*60)
    logger.info(f"Corpus: {corpus_path}")
    logger.info(f"Output: {output_path}")
    logger.info(f"Configuration:")
    for key, value in config.items():
        logger.info(f"  {key}: {value}")
    logger.info("="*60)
    
    # Extract filter_proper from config
    filter_proper = config.pop('filter_proper', False)
    
    # Load sentences
    logger.info("Loading sentences from corpus...")
    start_time = time.time()
    sentences = list(load_sentences(corpus_path, filter_proper))
    load_time = time.time() - start_time
    logger.info(f"Sentences loaded in {load_time:.2f} seconds ({load_time/60:.2f} minutes)")
    
    # Create output directory
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create epoch logger callback
    epoch_logger = EpochLogger()
    config['callbacks'] = [epoch_logger]
    
    # Train model
    logger.info("Training Word2Vec model...")
    train_start = time.time()
    
    model = Word2Vec(sentences=sentences, **config)
    
    train_time = time.time() - train_start
    logger.info(f"Training completed in {train_time:.2f} seconds ({train_time/60:.2f} minutes, {train_time/3600:.2f} hours)")
    
    # Save model
    logger.info(f"Saving model to {output_path}")
    model.save(str(output_path))
    
    # Print statistics
    logger.info("="*60)
    logger.info("TRAINING COMPLETE")
    logger.info("="*60)
    logger.info(f"Vocabulary size: {len(model.wv):,} words")
    logger.info(f"Total training time: {train_time:.2f} seconds ({train_time/3600:.2f} hours)")
    logger.info(f"Model saved to: {output_path}")
    logger.info("="*60)
    
    # Test with a few sample words
    logger.info("\nSample similarity tests:")
    test_words = ['hundo', 'kato', 'lingvo', 'manĝi', 'domo', 'homo']
    for word in test_words:
        if word in model.wv:
            similar = model.wv.most_similar(word, topn=5)
            logger.info(f"\n{word}:")
            for sim_word, score in similar:
                logger.info(f"  {sim_word}: {score:.3f}")
        else:
            logger.info(f"\n{word}: NOT IN VOCABULARY")
    
    return model


def main():
    parser = argparse.ArgumentParser(
        description='Train Esperanto word embeddings'
    )
    parser.add_argument(
        '--corpus',
        type=Path,
        required=True,
        help='Input corpus file (one sentence per line)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output model file path'
    )
    parser.add_argument(
        '--config',
        type=str,
        default='combined-best',
        choices=['combined-best', 'baseline', 'custom'],
        help='Configuration preset (default: combined-best)'
    )
    
    args = parser.parse_args()
    
    # Configuration presets
    configs = {
        'combined-best': {
            'vector_size': 300,
            'window': 5,           # Focused context
            'min_count': 15,       # Remove rare words
            'workers': 4,
            'sg': 1,               # Skip-gram
            'negative': 10,        # More negative samples
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001,
            'sample': 1e-5,        # Subsample frequent words
            'filter_proper': True, # Filter proper nouns
        },
        'baseline': {
            'vector_size': 300,
            'window': 10,
            'min_count': 5,
            'workers': 4,
            'sg': 1,
            'negative': 5,
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001,
            'sample': 0,
            'filter_proper': False,
        },
        'custom': {
            # User can modify this
            'vector_size': 300,
            'window': 5,
            'min_count': 10,
            'workers': 4,
            'sg': 1,
            'negative': 10,
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001,
            'sample': 1e-5,
            'filter_proper': True,
        }
    }
    
    config = configs[args.config]
    
    # Train
    train_embeddings(args.corpus, args.output, config)
    
    logger.info("\n✓ Done!")


if __name__ == '__main__':
    main()

