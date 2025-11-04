#!/usr/bin/env python3
"""
Train embeddings with optimized parameters for small corpus.

Experiments:
1. Lower min_count (keep more words)
2. Larger window (more context)
3. More epochs (better convergence)
4. CBOW vs Skip-gram comparison
"""

import argparse
import logging
import string
from pathlib import Path
from gensim.models import Word2Vec
from gensim.models.callbacks import CallbackAny2Vec

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EpochLogger(CallbackAny2Vec):
    def __init__(self):
        self.epoch = 0
    def on_epoch_end(self, model):
        self.epoch += 1
        logger.info(f"Epoch {self.epoch} completed")


def load_sentences(corpus_path: Path):
    """Load sentences with punctuation stripping."""
    with open(corpus_path, 'r', encoding='utf-8') as f:
        for line in f:
            # Strip punctuation from each token
            tokens = [token.strip(string.punctuation) for token in line.strip().split()]
            # Filter out empty tokens
            tokens = [t for t in tokens if t]
            if tokens:
                yield tokens


def train_optimized(corpus_path: Path, output_path: Path, config: dict):
    """Train with specific configuration."""
    logger.info(f"Configuration: {config}")
    
    sentences = list(load_sentences(corpus_path))
    logger.info(f"Loaded {len(sentences)} sentences")
    
    model = Word2Vec(
        vector_size=config['vector_size'],
        window=config['window'],
        min_count=config['min_count'],
        workers=4,
        sg=config['sg'],
        negative=config['negative'],
        epochs=config['epochs'],
        alpha=config['alpha'],
        min_alpha=config['min_alpha'],
        callbacks=[EpochLogger()]
    )
    
    model.build_vocab(sentences)
    logger.info(f"Vocabulary: {len(model.wv)} words")
    
    model.train(sentences, total_examples=len(sentences), epochs=config['epochs'])
    
    model.save(str(output_path))
    logger.info(f"Saved to {output_path}")
    
    return model


def evaluate(model, test_words):
    """Quick evaluation."""
    for word in test_words:
        if word in model.wv:
            similar = model.wv.most_similar(word, topn=5)
            logger.info(f"\n'{word}': {[w for w, s in similar]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--experiment', required=True, 
                       choices=['low-mincount', 'large-window', 'more-epochs', 'cbow', 'aggressive'])
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    corpus_path = base_dir / 'data' / 'processed' / 'ido_clean.txt'
    models_dir = base_dir / 'models'
    
    # Base configuration
    base_config = {
        'vector_size': 300,
        'window': 5,
        'min_count': 20,
        'sg': 1,  # Skip-gram
        'negative': 5,
        'epochs': 10,
        'alpha': 0.025,
        'min_alpha': 0.0001
    }
    
    # Experiment configurations
    experiments = {
        'low-mincount': {
            **base_config,
            'min_count': 5,  # Keep more words
            'epochs': 15  # More training to compensate
        },
        'large-window': {
            **base_config,
            'window': 10,  # Larger context
            'epochs': 15
        },
        'more-epochs': {
            **base_config,
            'epochs': 30,  # Much more training
            'alpha': 0.05,  # Higher learning rate
            'min_alpha': 0.0001
        },
        'cbow': {
            **base_config,
            'sg': 0,  # CBOW instead of skip-gram
            'epochs': 15
        },
        'aggressive': {
            'vector_size': 300,
            'window': 10,
            'min_count': 5,
            'sg': 1,
            'negative': 10,  # More negative samples
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001
        }
    }
    
    config = experiments[args.experiment]
    output_path = models_dir / f'ido_optimized_{args.experiment}.model'
    
    logger.info(f"Running experiment: {args.experiment}")
    model = train_optimized(corpus_path, output_path, config)
    
    test_words = ['hundo', 'kato', 'linguo', 'programo']
    evaluate(model, test_words)


if __name__ == '__main__':
    main()
