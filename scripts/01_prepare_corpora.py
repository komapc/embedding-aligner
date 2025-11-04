#!/usr/bin/env python3
"""
Step 1: Prepare and clean corpora for embedding training.

Input:
    - data/raw/ido_corpus.txt
    - data/raw/epo_corpus.txt

Output:
    - data/processed/ido_clean.txt
    - data/processed/epo_clean.txt
"""

import re
import logging
from pathlib import Path
from typing import Iterator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """
    Clean and normalize text.
    
    Args:
        text: Raw text string
        
    Returns:
        Cleaned text string
    """
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def tokenize_sentence(sentence: str) -> str:
    """
    Tokenize sentence (simple whitespace tokenization).
    
    Args:
        sentence: Input sentence
        
    Returns:
        Tokenized sentence
    """
    # Lowercase for consistency
    sentence = sentence.lower()
    
    # Add space before punctuation for better tokenization
    sentence = re.sub(r'([.,!?;:])', r' \1 ', sentence)
    
    # Remove extra spaces
    sentence = re.sub(r'\s+', ' ', sentence).strip()
    
    return sentence


def process_corpus(input_path: Path, output_path: Path, min_length: int = 3) -> dict:
    """
    Process corpus file: clean, tokenize, deduplicate.
    
    Args:
        input_path: Path to raw corpus
        output_path: Path to save cleaned corpus
        min_length: Minimum sentence length in tokens
        
    Returns:
        Statistics dictionary
    """
    stats = {
        'total_lines': 0,
        'cleaned_lines': 0,
        'duplicates_removed': 0,
        'short_sentences_removed': 0,
        'total_tokens': 0
    }
    
    seen_sentences = set()
    cleaned_sentences = []
    
    logger.info(f"Reading from {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            stats['total_lines'] += 1
            
            # Clean text
            cleaned = clean_text(line)
            
            if not cleaned:
                continue
            
            # Tokenize
            tokenized = tokenize_sentence(cleaned)
            
            # Check minimum length
            tokens = tokenized.split()
            if len(tokens) < min_length:
                stats['short_sentences_removed'] += 1
                continue
            
            # Check for duplicates
            if tokenized in seen_sentences:
                stats['duplicates_removed'] += 1
                continue
            
            seen_sentences.add(tokenized)
            cleaned_sentences.append(tokenized)
            stats['total_tokens'] += len(tokens)
    
    stats['cleaned_lines'] = len(cleaned_sentences)
    
    # Write output
    logger.info(f"Writing to {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        for sentence in cleaned_sentences:
            f.write(sentence + '\n')
    
    return stats


def main():
    """Main execution function."""
    logger.info("Starting corpus preparation...")
    
    # Define paths
    base_dir = Path(__file__).parent.parent
    raw_dir = base_dir / 'data' / 'raw'
    processed_dir = base_dir / 'data' / 'processed'
    
    # Ensure directories exist
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Process Ido corpus
    logger.info("Processing Ido corpus...")
    ido_input = raw_dir / 'ido_corpus.txt'
    ido_output = processed_dir / 'ido_clean.txt'
    
    if ido_input.exists():
        ido_stats = process_corpus(ido_input, ido_output)
        logger.info(f"Ido corpus stats: {ido_stats}")
    else:
        logger.warning(f"Ido corpus not found at {ido_input}")
    
    # Process Esperanto corpus
    logger.info("Processing Esperanto corpus...")
    epo_input = raw_dir / 'epo_corpus.txt'
    epo_output = processed_dir / 'epo_clean.txt'
    
    if epo_input.exists():
        epo_stats = process_corpus(epo_input, epo_output)
        logger.info(f"Esperanto corpus stats: {epo_stats}")
    else:
        logger.warning(f"Esperanto corpus not found at {epo_input}")
    
    logger.info("Corpus preparation complete!")


if __name__ == '__main__':
    main()
