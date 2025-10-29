#!/usr/bin/env python3
"""
Prepare seed dictionary by splitting into train/validation sets.
Input: 50K dictionary file
Output: train_45k.txt (90%) and validation_5k.txt (10%)
"""

import random
from pathlib import Path

def split_dictionary(input_file, train_file, val_file, train_ratio=0.9):
    """Split dictionary into train and validation sets."""
    
    # Read all pairs
    pairs = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                parts = line.split()
                if len(parts) >= 2:
                    pairs.append(f"{parts[0]} {parts[1]}")
    
    print(f"Loaded {len(pairs)} translation pairs")
    
    # Shuffle and split
    random.seed(42)  # For reproducibility
    random.shuffle(pairs)
    
    split_idx = int(len(pairs) * train_ratio)
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]
    
    # Save train set
    with open(train_file, 'w', encoding='utf-8') as f:
        for pair in train_pairs:
            f.write(pair + '\n')
    print(f"Train set saved: {train_file} ({len(train_pairs)} pairs)")
    
    # Save validation set
    with open(val_file, 'w', encoding='utf-8') as f:
        for pair in val_pairs:
            f.write(pair + '\n')
    print(f"Validation set saved: {val_file} ({len(val_pairs)} pairs)")

def main():
    dict_dir = Path('data/dictionaries')
    
    # Look for seed dictionary
    input_file = dict_dir / 'seed_dictionary_50k.txt'
    
    if not input_file.exists():
        print(f"Error: Seed dictionary not found: {input_file}")
        print("\nPlease place your 50K Ido-Esperanto dictionary at:")
        print(f"  {input_file}")
        print("\nFormat: one pair per line, space-separated:")
        print("  ido_word esperanto_word")
        return
    
    train_file = dict_dir / 'train_45k.txt'
    val_file = dict_dir / 'validation_5k.txt'
    
    split_dictionary(input_file, train_file, val_file)
    
    print("\n✓ Dictionary preparation complete!")

if __name__ == '__main__':
    main()
