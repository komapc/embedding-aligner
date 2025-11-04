#!/usr/bin/env python3
"""
Train multiple experimental models with different configurations.

Experiments:
1. higher-mincount: min_count=20, remove rare words
2. subsampling: sample=1e-5, balance frequent words
3. smaller-window: window=5, focused context
4. cbow: CBOW instead of Skip-gram
5. no-proper-nouns: filter capitalized words
6. combined-best: best settings combined
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


def is_proper_noun(word):
    """Detect proper nouns (capitalized words)."""
    if not word:
        return False
    # Check if first letter is uppercase and word is longer than 1 char
    return word[0].isupper() and len(word) > 1 and word.isalpha()


def load_sentences(corpus_path: Path, filter_proper=False):
    """Load sentences with optional proper noun filtering."""
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
                yield tokens


EXPERIMENTS = {
    'higher-mincount': {
        'description': 'min_count=20 to remove rare words and proper nouns',
        'config': {
            'vector_size': 300,
            'window': 10,
            'min_count': 20,
            'workers': 4,
            'sg': 1,  # Skip-gram
            'negative': 5,
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001,
            'sample': 0,  # No subsampling
        },
        'filter_proper': False,
    },
    'subsampling': {
        'description': 'sample=1e-5 to balance frequent words',
        'config': {
            'vector_size': 300,
            'window': 10,
            'min_count': 5,
            'workers': 4,
            'sg': 1,
            'negative': 5,
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001,
            'sample': 1e-5,  # Subsample frequent words
        },
        'filter_proper': False,
    },
    'smaller-window': {
        'description': 'window=5 for more focused context',
        'config': {
            'vector_size': 300,
            'window': 5,  # Smaller window
            'min_count': 5,
            'workers': 4,
            'sg': 1,
            'negative': 5,
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001,
            'sample': 0,
        },
        'filter_proper': False,
    },
    'cbow': {
        'description': 'CBOW (sg=0) better for small corpus',
        'config': {
            'vector_size': 300,
            'window': 10,
            'min_count': 5,
            'workers': 4,
            'sg': 0,  # CBOW
            'negative': 5,
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001,
            'sample': 0,
        },
        'filter_proper': False,
    },
    'no-proper-nouns': {
        'description': 'Filter out capitalized words (proper nouns)',
        'config': {
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
        },
        'filter_proper': True,  # Filter proper nouns
    },
    'combined-best': {
        'description': 'Best settings: min_count=15, window=5, sample=1e-5, filter proper nouns',
        'config': {
            'vector_size': 300,
            'window': 5,  # Focused
            'min_count': 15,  # Remove rare words
            'workers': 4,
            'sg': 1,
            'negative': 10,  # More negative samples
            'epochs': 30,
            'alpha': 0.05,
            'min_alpha': 0.0001,
            'sample': 1e-5,  # Subsample frequent
        },
        'filter_proper': True,  # Filter proper nouns
    },
}


def train_experiment(corpus_path: Path, output_path: Path, experiment_name: str):
    """Train with specific experiment configuration."""
    exp = EXPERIMENTS[experiment_name]
    config = exp['config']
    filter_proper = exp['filter_proper']
    
    logger.info(f"\n{'='*70}")
    logger.info(f"Experiment: {experiment_name}")
    logger.info(f"Description: {exp['description']}")
    logger.info(f"Config: {config}")
    logger.info(f"Filter proper nouns: {filter_proper}")
    logger.info(f"{'='*70}\n")
    
    sentences = list(load_sentences(corpus_path, filter_proper=filter_proper))
    logger.info(f"Loaded {len(sentences)} sentences")
    
    model = Word2Vec(
        vector_size=config['vector_size'],
        window=config['window'],
        min_count=config['min_count'],
        workers=config['workers'],
        sg=config['sg'],
        negative=config['negative'],
        epochs=config['epochs'],
        alpha=config['alpha'],
        min_alpha=config['min_alpha'],
        sample=config['sample'],
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
    logger.info("\n" + "="*70)
    logger.info("Quick Evaluation")
    logger.info("="*70)
    
    for word in test_words:
        if word in model.wv:
            similar = model.wv.most_similar(word, topn=5)
            logger.info(f"\n'{word}' most similar words:")
            for sim_word, score in similar:
                freq = model.wv.get_vecattr(sim_word, 'count')
                logger.info(f"  {sim_word}: {score:.3f} (freq: {freq})")
        else:
            logger.info(f"\n'{word}': NOT IN VOCABULARY")


def main():
    parser = argparse.ArgumentParser(
        description='Train experimental models with different configurations'
    )
    parser.add_argument('--experiment', required=True, 
                       choices=list(EXPERIMENTS.keys()),
                       help='Experiment to run')
    parser.add_argument('--corpus', default='data/processed/ido_corpus.txt',
                       help='Path to corpus file')
    parser.add_argument('--output-dir', default='models',
                       help='Output directory for models')
    
    args = parser.parse_args()
    
    base_dir = Path(__file__).parent.parent
    corpus_path = base_dir / args.corpus
    output_dir = base_dir / args.output_dir
    output_dir.mkdir(exist_ok=True)
    
    output_path = output_dir / f"ido_exp_{args.experiment}.model"
    
    if not corpus_path.exists():
        logger.error(f"Corpus not found at {corpus_path}")
        return 1
    
    model = train_experiment(corpus_path, output_path, args.experiment)
    
    # Quick evaluation
    test_words = ['hundo', 'kato', 'linguo', 'programo']
    evaluate(model, test_words)
    
    return 0


if __name__ == '__main__':
    exit(main())
