#!/usr/bin/env python3
"""
Improve vortaro dictionary quality by:
1. Using BERT similarity scores to rank translations
2. Removing low-similarity or incorrect translations
3. Keeping only the best translation(s) per word
4. Prioritizing exact matches and high-similarity candidates
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

def load_bert_candidates(bert_file: Path) -> Dict[str, List[Dict]]:
    """Load BERT candidates with similarity scores."""
    print(f"Loading BERT candidates from {bert_file}...")
    with open(bert_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} Ido words with BERT candidates")
    return data

def build_similarity_map(bert_candidates: Dict[str, List[Dict]]) -> Dict[tuple, float]:
    """
    Build map of (ido_word, epo_word) -> similarity.
    Returns highest similarity for each pair.
    """
    similarity_map = {}
    for ido_word, candidates in bert_candidates.items():
        for cand in candidates:
            epo_word = cand.get('translation', cand.get('epo', ''))
            similarity = cand.get('similarity', 0)
            if epo_word:
                key = (ido_word.lower(), epo_word.lower())
                # Keep highest similarity
                if key not in similarity_map or similarity > similarity_map[key]:
                    similarity_map[key] = similarity
    return similarity_map

def is_exact_match(ido_word: str, epo_word: str) -> bool:
    """Check if Ido and Esperanto words are identical (cognates)."""
    return ido_word.lower() == epo_word.lower()

def improve_vortaro_entry(
    ido_word: str,
    entry: Dict,
    similarity_map: Dict[tuple, float],
    max_translations: int = 3,
    min_similarity: float = 0.80
) -> Dict:
    """
    Improve a single vortaro entry by:
    - Ranking translations by similarity
    - Prioritizing exact matches
    - Removing low-similarity translations
    - Keeping only top N translations
    """
    epo_words = entry.get('esperanto_words', [])
    sources = entry.get('sources', [])
    
    # Check if this entry has BERT alignment
    has_bert = 'bert_alignment' in sources
    
    if not has_bert or not epo_words:
        # Not a BERT entry or no translations - keep as is
        return entry
    
    # Build list of translations with similarities
    translations_with_sim = []
    for epo_word in epo_words:
        key = (ido_word.lower(), epo_word.lower())
        similarity = similarity_map.get(key, None)
        
        # If not in BERT map, might be from other source - keep it but with lower priority
        if similarity is None:
            # Check if it's an exact match (cognate)
            if is_exact_match(ido_word, epo_word):
                similarity = 1.0  # Perfect match
            else:
                # From other source, keep but with lower priority
                similarity = 0.5  # Unknown similarity, lower priority
    
        translations_with_sim.append({
            'word': epo_word,
            'similarity': similarity,
            'exact_match': is_exact_match(ido_word, epo_word)
        })
    
    # Sort by: exact matches first, then by similarity descending
    translations_with_sim.sort(key=lambda x: (
        not x['exact_match'],  # Exact matches first (False < True)
        -x['similarity']  # Higher similarity first
    ))
    
    # Filter: keep only translations with similarity >= min_similarity
    # OR exact matches (even if similarity unknown)
    filtered = [
        t['word'] for t in translations_with_sim
        if t['similarity'] is not None and (
            t['similarity'] >= min_similarity or t['exact_match']
        )
    ]
    
    # Limit to max_translations
    filtered = filtered[:max_translations]
    
    # Create improved entry
    improved_entry = entry.copy()
    improved_entry['esperanto_words'] = filtered
    
    return improved_entry

def improve_vortaro_dictionary(
    vortaro_file: Path,
    bert_candidates_file: Path,
    output_file: Path,
    max_translations: int = 3,
    min_similarity: float = 0.80
):
    """Improve entire vortaro dictionary."""
    print(f"Loading vortaro dictionary from {vortaro_file}...")
    with open(vortaro_file, 'r', encoding='utf-8') as f:
        vortaro = json.load(f)
    
    metadata = vortaro.get('metadata', {})
    total_words = len([k for k in vortaro.keys() if k != 'metadata'])
    print(f"Loaded {total_words} words")
    
    # Load BERT candidates
    bert_candidates = load_bert_candidates(bert_candidates_file)
    similarity_map = build_similarity_map(bert_candidates)
    print(f"Built similarity map with {len(similarity_map)} translation pairs")
    
    # Improve entries
    print("\nImproving entries...")
    improved = {'metadata': metadata.copy()}
    stats = {
        'total_words': 0,
        'improved_words': 0,
        'removed_translations': 0,
        'kept_translations': 0,
        'exact_matches': 0
    }
    
    for word, entry in vortaro.items():
        if word == 'metadata':
            continue
        
        stats['total_words'] += 1
        
        if not isinstance(entry, dict):
            improved[word] = entry
            continue
        
        improved_entry = improve_vortaro_entry(
            word, entry, similarity_map, max_translations, min_similarity
        )
        
        original_count = len(entry.get('esperanto_words', []))
        improved_count = len(improved_entry.get('esperanto_words', []))
        
        if improved_count < original_count:
            stats['improved_words'] += 1
            stats['removed_translations'] += original_count - improved_count
        
        stats['kept_translations'] += improved_count
        
        # Check for exact matches
        epo_words = improved_entry.get('esperanto_words', [])
        if any(is_exact_match(word, epo) for epo in epo_words):
            stats['exact_matches'] += 1
        
        improved[word] = improved_entry
    
    # Update metadata
    improved['metadata']['total_words'] = stats['total_words']
    improved['metadata']['last_update'] = __import__('datetime').datetime.now().isoformat()
    improved['metadata']['quality_improvement'] = {
        'date': __import__('datetime').datetime.now().isoformat(),
        'words_improved': stats['improved_words'],
        'translations_removed': stats['removed_translations'],
        'translations_kept': stats['kept_translations'],
        'exact_matches': stats['exact_matches'],
        'max_translations_per_word': max_translations,
        'min_similarity': min_similarity
    }
    
    print(f"\nImprovement results:")
    print(f"  Words processed: {stats['total_words']}")
    print(f"  Words improved: {stats['improved_words']}")
    print(f"  Translations removed: {stats['removed_translations']}")
    print(f"  Translations kept: {stats['kept_translations']}")
    print(f"  Exact matches: {stats['exact_matches']}")
    
    # Save improved dictionary
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(improved, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved improved dictionary to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Improve vortaro dictionary quality using BERT similarities')
    parser.add_argument('--vortaro', type=Path, required=True,
                        help='Input vortaro dictionary.json')
    parser.add_argument('--bert-candidates', type=Path, required=True,
                        help='BERT candidates JSON file with similarity scores')
    parser.add_argument('--output', type=Path, required=True,
                        help='Output dictionary.json')
    parser.add_argument('--max-translations', type=int, default=3,
                        help='Maximum translations per word (default: 3)')
    parser.add_argument('--min-similarity', type=float, default=0.80,
                        help='Minimum similarity threshold (default: 0.80)')
    
    args = parser.parse_args()
    
    improve_vortaro_dictionary(
        args.vortaro,
        args.bert_candidates,
        args.output,
        args.max_translations,
        args.min_similarity
    )

if __name__ == '__main__':
    main()





