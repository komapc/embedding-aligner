#!/usr/bin/env python3
"""
Filter vortaro dictionary.json to remove BERT entries with similarity < 0.8.
Note: Vortaro dictionary may not store similarity scores directly.
This script removes entries that only have "bert_alignment" as source
if we can't verify their similarity >= 0.8.
"""

import json
import argparse
from pathlib import Path
from typing import Dict, Any

def filter_vortaro(input_file: Path, output_file: Path, bert_candidates_file: Path = None, min_similarity: float = 0.80):
    """Filter vortaro dictionary to remove low-quality BERT entries."""
    print(f"Loading vortaro dictionary from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data.get('metadata', {})
    total_words = len([k for k in data.keys() if k != 'metadata'])
    print(f"Loaded {total_words} words")
    
    # Load BERT candidates if provided to check similarities
    bert_similarities = {}
    if bert_candidates_file and bert_candidates_file.exists():
        print(f"Loading BERT candidates from {bert_candidates_file}...")
        with open(bert_candidates_file, 'r', encoding='utf-8') as f:
            bert_data = json.load(f)
        
        # Build similarity map: (ido_word, epo_word) -> similarity
        for ido_word, candidates in bert_data.items():
            for cand in candidates:
                epo_word = cand.get('translation', cand.get('epo', ''))
                similarity = cand.get('similarity', 0)
                if epo_word:
                    key = (ido_word.lower(), epo_word.lower())
                    # Keep highest similarity
                    if key not in bert_similarities or similarity > bert_similarities[key]:
                        bert_similarities[key] = similarity
        
        print(f"Loaded {len(bert_similarities)} BERT translation pairs with similarities")
    
    # Filter entries
    removed_words = 0
    removed_translations = 0
    kept_words = 0
    
    filtered_data = {'metadata': metadata.copy()}
    
    for word, entry in data.items():
        if word == 'metadata':
            continue
        
        if not isinstance(entry, dict):
            filtered_data[word] = entry
            kept_words += 1
            continue
        
        sources = entry.get('sources', [])
        esperanto_words = entry.get('esperanto_words', [])
        
        # Check if this entry has BERT alignment
        has_bert = 'bert_alignment' in sources
        
        if has_bert:
            # Filter Esperanto words based on similarity
            filtered_epo_words = []
            for epo_word in esperanto_words:
                # Check similarity if we have BERT data
                if bert_similarities:
                    key = (word.lower(), epo_word.lower())
                    similarity = bert_similarities.get(key, None)
                    
                    if similarity is not None:
                        if similarity >= min_similarity:
                            filtered_epo_words.append(epo_word)
                        else:
                            removed_translations += 1
                    else:
                        # Not in BERT candidates - keep it (might be from other source)
                        filtered_epo_words.append(epo_word)
                else:
                    # No BERT data - be conservative and keep it
                    filtered_epo_words.append(epo_word)
            
            # If no Esperanto words left, remove the word entirely
            if filtered_epo_words:
                entry_copy = entry.copy()
                entry_copy['esperanto_words'] = filtered_epo_words
                filtered_data[word] = entry_copy
                kept_words += 1
            else:
                removed_words += 1
        else:
            # Not a BERT entry - keep it
            filtered_data[word] = entry
            kept_words += 1
    
    # Update metadata
    filtered_data['metadata']['total_words'] = kept_words
    filtered_data['metadata']['last_update'] = __import__('datetime').datetime.now().isoformat()
    filtered_data['metadata']['filtered_bert'] = {
        'min_similarity': min_similarity,
        'words_removed': removed_words,
        'translations_removed': removed_translations
    }
    
    print(f"\nFiltering results:")
    print(f"  Words before: {total_words}")
    print(f"  Words after:  {kept_words}")
    print(f"  Words removed: {removed_words}")
    print(f"  Translations removed: {removed_translations}")
    
    # Save filtered dictionary
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(filtered_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved filtered dictionary to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Filter vortaro dictionary by BERT similarity')
    parser.add_argument('--input', type=Path, required=True,
                        help='Input dictionary.json file')
    parser.add_argument('--output', type=Path, required=True,
                        help='Output dictionary.json file')
    parser.add_argument('--bert-candidates', type=Path,
                        help='BERT candidates JSON file to check similarities')
    parser.add_argument('--min-similarity', type=float, default=0.80,
                        help='Minimum similarity threshold (default: 0.80)')
    
    args = parser.parse_args()
    
    filter_vortaro(args.input, args.output, args.bert_candidates, args.min_similarity)

if __name__ == '__main__':
    main()

