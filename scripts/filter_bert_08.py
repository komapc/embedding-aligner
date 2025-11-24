#!/usr/bin/env python3
"""
Filter BERT translation candidates to only keep entries with similarity >= 0.8.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List

def filter_candidates(input_file: Path, output_file: Path, min_similarity: float = 0.80):
    """Filter candidates to only keep those with similarity >= min_similarity."""
    print(f"Loading candidates from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {len(data)} Ido words with candidates")
    
    # Count before
    total_before = sum(len(candidates) for candidates in data.values())
    below_threshold = sum(
        sum(1 for c in candidates if c.get('similarity', 0) < min_similarity)
        for candidates in data.values()
    )
    
    # Filter
    filtered = {}
    for ido_word, candidates in data.items():
        high_quality = [
            c for c in candidates
            if c.get('similarity', 0) >= min_similarity
        ]
        if high_quality:
            filtered[ido_word] = high_quality
    
    # Count after
    total_after = sum(len(candidates) for candidates in filtered.values())
    
    print(f"\nFiltering results:")
    print(f"  Words before: {len(data)}")
    print(f"  Words after:  {len(filtered)}")
    print(f"  Candidates before: {total_before}")
    print(f"  Candidates after:  {total_after}")
    print(f"  Removed: {total_before - total_after} candidates ({below_threshold} below {min_similarity})")
    print(f"  Reduction: {100*(total_before-total_after)/total_before:.1f}%")
    
    # Save filtered results
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved filtered candidates to {output_file}")
    
    return filtered

def main():
    parser = argparse.ArgumentParser(description='Filter BERT candidates by similarity threshold')
    parser.add_argument('--input', type=Path, required=True,
                        help='Input JSON file with BERT candidates')
    parser.add_argument('--output', type=Path, required=True,
                        help='Output JSON file for filtered candidates')
    parser.add_argument('--min-similarity', type=float, default=0.80,
                        help='Minimum similarity threshold (default: 0.80)')
    
    args = parser.parse_args()
    
    filter_candidates(args.input, args.output, args.min_similarity)

if __name__ == '__main__':
    main()

