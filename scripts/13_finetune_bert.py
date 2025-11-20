#!/usr/bin/env python3
"""
Fine-tune XLM-RoBERTa on Ido corpus for better cross-lingual embeddings.

This script:
1. Loads pre-trained XLM-RoBERTa-base
2. Prepares Ido corpus for Masked Language Modeling (MLM)
3. Fine-tunes the model for 3 epochs
4. Saves the fine-tuned model

Usage:
    python scripts/13_finetune_bert.py \
        --corpus data/processed/ido_wikipedia_plus_wikisource.txt \
        --output models/bert-ido-finetuned \
        --epochs 3 \
        --batch-size 16

Expected time: 3-4 hours on GPU (g4dn.xlarge)
"""

import argparse
import logging
import math
import os
import time
from pathlib import Path
from typing import List

import torch
from transformers import (
    XLMRobertaForMaskedLM,
    XLMRobertaTokenizer,
    DataCollatorForLanguageModeling,
    Trainer,
    TrainingArguments,
)
from datasets import Dataset

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_corpus(corpus_path: Path, max_length: int = 256, sample_percent: int = None) -> List[str]:
    """
    Load and preprocess corpus for BERT fine-tuning.
    
    Args:
        corpus_path: Path to corpus file (one sentence per line)
        max_length: Maximum sequence length (will be tokenized later)
        sample_percent: If set, only load this percentage of corpus (for testing)
    
    Returns:
        List of sentences
    """
    logger.info(f"Loading corpus from {corpus_path}")
    if sample_percent:
        logger.info(f"⚠️  Test mode: Loading only {sample_percent}% of corpus")
    
    sentences = []
    short_count = 0
    long_count = 0
    total_lines = 0
    import random
    random.seed(42)  # For reproducible sampling
    
    with open(corpus_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_lines += 1
            
            # Sample percentage for testing - SKIP early to save memory
            if sample_percent and random.randint(1, 100) > sample_percent:
                continue
            
            sentence = line.strip()
            
            # Skip very short sentences (< 3 words)
            if len(sentence.split()) < 3:
                short_count += 1
                continue
            
            # Skip very long sentences (> 512 tokens will be truncated anyway)
            if len(sentence.split()) > 512:
                long_count += 1
                continue
            
            sentences.append(sentence)
            
            # Log progress - adjust for sampling
            log_interval = 5000 if sample_percent else 50000
            if len(sentences) % log_interval == 0:
                logger.info(f"Loaded {len(sentences):,} sentences")
    
    logger.info(f"Total lines read: {total_lines:,}")
    logger.info(f"Corpus loaded: {len(sentences):,} sentences")
    logger.info(f"Filtered out: {short_count:,} too short, {long_count:,} too long")
    
    return sentences


def prepare_dataset(sentences: List[str], tokenizer, max_length: int = 256) -> Dataset:
    """
    Tokenize sentences and create HuggingFace Dataset.
    
    Args:
        sentences: List of text sentences
        tokenizer: XLM-RoBERTa tokenizer
        max_length: Maximum sequence length
    
    Returns:
        HuggingFace Dataset ready for training
    """
    logger.info(f"Tokenizing {len(sentences):,} sentences...")
    start_time = time.time()
    
    # Tokenize in batches for speed
    tokenized = tokenizer(
        sentences,
        truncation=True,
        padding=False,  # Will be done by data collator
        max_length=max_length,
        return_special_tokens_mask=True,
    )
    
    # Create dataset
    dataset = Dataset.from_dict(tokenized)
    
    elapsed = time.time() - start_time
    logger.info(f"Tokenization complete in {elapsed:.2f} seconds")
    
    return dataset


def train_model(
    dataset: Dataset,
    output_dir: Path,
    num_epochs: int = 3,
    batch_size: int = 16,
    learning_rate: float = 2e-5,
    warmup_steps: int = 500,
    save_steps: int = 1000,
):
    """
    Fine-tune XLM-RoBERTa on the dataset.
    
    Args:
        dataset: Tokenized dataset
        output_dir: Where to save the fine-tuned model
        num_epochs: Number of training epochs
        batch_size: Batch size per device
        learning_rate: Learning rate
        warmup_steps: Number of warmup steps
        save_steps: Save checkpoint every N steps
    """
    logger.info("Initializing model and training...")
    
    # Load pre-trained model
    logger.info("Loading XLM-RoBERTa-base...")
    model = XLMRobertaForMaskedLM.from_pretrained('xlm-roberta-base')
    tokenizer = XLMRobertaTokenizer.from_pretrained('xlm-roberta-base')
    
    # Check for GPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")
    
    if device == "cpu":
        logger.warning("⚠️  Training on CPU will be VERY slow (20-30 hours)")
        logger.warning("⚠️  Strongly recommend using GPU (g4dn.xlarge on EC2)")
    
    # Data collator for MLM
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=0.15,  # Mask 15% of tokens
    )
    
    # Training arguments
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        overwrite_output_dir=True,
        num_train_epochs=num_epochs,
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=2,  # Effective batch = 32
        learning_rate=learning_rate,
        warmup_steps=warmup_steps,
        weight_decay=0.01,
        logging_dir=str(output_dir / 'logs'),
        logging_steps=100,
        save_steps=save_steps,
        save_total_limit=3,  # Keep only 3 checkpoints
        fp16=device == "cuda",  # Mixed precision if GPU
        report_to="none",  # Disable wandb/tensorboard
        remove_unused_columns=False,
    )
    
    # Initialize trainer
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        data_collator=data_collator,
    )
    
    # Train
    logger.info("Starting training...")
    logger.info(f"Total epochs: {num_epochs}")
    logger.info(f"Batch size: {batch_size} (effective: {batch_size * 2})")
    logger.info(f"Learning rate: {learning_rate}")
    logger.info(f"Warmup steps: {warmup_steps}")
    
    start_time = time.time()
    
    train_result = trainer.train()
    
    elapsed = time.time() - start_time
    logger.info(f"Training completed in {elapsed:.2f} seconds ({elapsed/60:.2f} minutes)")
    
    # Log training metrics
    logger.info(f"Final training loss: {train_result.training_loss:.4f}")
    
    # Calculate perplexity
    perplexity = math.exp(train_result.training_loss)
    logger.info(f"Final perplexity: {perplexity:.2f}")
    
    # Save final model
    logger.info(f"Saving final model to {output_dir}")
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    
    logger.info("✅ Fine-tuning complete!")
    
    return trainer


def main():
    parser = argparse.ArgumentParser(description='Fine-tune XLM-RoBERTa on Ido corpus')
    parser.add_argument('--corpus', required=True, type=Path,
                        help='Path to corpus file (one sentence per line)')
    parser.add_argument('--output', required=True, type=Path,
                        help='Output directory for fine-tuned model')
    parser.add_argument('--epochs', type=int, default=3,
                        help='Number of training epochs (default: 3)')
    parser.add_argument('--batch-size', type=int, default=16,
                        help='Batch size per device (default: 16)')
    parser.add_argument('--learning-rate', type=float, default=2e-5,
                        help='Learning rate (default: 2e-5)')
    parser.add_argument('--warmup-steps', type=int, default=500,
                        help='Number of warmup steps (default: 500)')
    parser.add_argument('--max-length', type=int, default=256,
                        help='Maximum sequence length (default: 256)')
    parser.add_argument('--save-steps', type=int, default=10000,
                        help='Save checkpoint every N steps (default: 10000)')
    parser.add_argument('--test-mode', action='store_true',
                        help='Run in test mode with small sample')
    parser.add_argument('--sample-percent', type=int, default=None,
                        help='Percentage of corpus to use (default: None = 100%)')
    
    args = parser.parse_args()
    
    # Test mode: reduce epochs
    if args.test_mode:
        logger.info("⚠️  TEST MODE: Using 5% corpus, 1 epoch")
        args.epochs = 1
        args.save_steps = 100  # Save more frequently in test mode
    
    # Verify corpus exists
    if not args.corpus.exists():
        logger.error(f"Corpus file not found: {args.corpus}")
        return
    
    # Create output directory
    args.output.mkdir(parents=True, exist_ok=True)
    
    # Load corpus
    sample_pct = args.sample_percent  # Use sample_percent if provided, regardless of test_mode
    sentences = load_corpus(args.corpus, args.max_length, sample_pct)
    
    # Load tokenizer
    logger.info("Loading tokenizer...")
    tokenizer = XLMRobertaTokenizer.from_pretrained('xlm-roberta-base')
    
    # Prepare dataset
    dataset = prepare_dataset(sentences, tokenizer, args.max_length)
    
    # Train model
    trainer = train_model(
        dataset,
        args.output,
        num_epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        save_steps=args.save_steps,
    )
    
    logger.info("All done!")


if __name__ == '__main__':
    main()

