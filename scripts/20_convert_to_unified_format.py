#!/usr/bin/env python3
"""
Convert BERT translation candidates to unified JSON format.

Takes the translation_candidates.json from embedding-aligner and converts it
to the unified source format used by the dictionary pipeline.

This script:
1. Reads BERT translation pairs with similarity scores
2. Filters by minimum similarity threshold (default 0.85)
3. Infers morphology from Ido word endings
4. Outputs unified JSON format compatible with the merge pipeline

Usage:
    python3 20_convert_to_unified_format.py \
        --input results/bert_ido_epo_alignment/translation_candidates.json \
        --output sources/source_bert_embeddings.json \
        --min-similarity 0.85
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


def infer_ido_morphology(lemma: str) -> Dict[str, str]:
    """
    Infer POS and paradigm from Ido word endings.
    
    Ido is highly regular:
    - Nouns end in -o (singular), -i (plural)
    - Adjectives end in -a
    - Adverbs end in -e
    - Verbs end in -ar (infinitive), -as (present), -is (past), -os (future)
    """
    lemma_lower = lemma.lower().strip()
    
    # Skip very short words or non-alphabetic
    if len(lemma_lower) < 2 or not lemma_lower.isalpha():
        return {}
    
    # Verb infinitives
    if lemma_lower.endswith('ar'):
        return {'pos': 'vblex', 'paradigm': 'ar__vblex'}
    
    # Verb conjugated forms - convert to infinitive base
    if lemma_lower.endswith('as') and len(lemma_lower) > 3:
        return {'pos': 'vblex', 'paradigm': 'ar__vblex'}
    
    if lemma_lower.endswith('is') and len(lemma_lower) > 3:
        return {'pos': 'vblex', 'paradigm': 'ar__vblex'}
    
    if lemma_lower.endswith('os') and len(lemma_lower) > 3:
        return {'pos': 'vblex', 'paradigm': 'ar__vblex'}
    
    if lemma_lower.endswith('us') and len(lemma_lower) > 3:
        return {'pos': 'vblex', 'paradigm': 'ar__vblex'}
    
    if lemma_lower.endswith('ez') and len(lemma_lower) > 3:
        return {'pos': 'vblex', 'paradigm': 'ar__vblex'}
    
    # Nouns (singular -o)
    if lemma_lower.endswith('o'):
        return {'pos': 'n', 'paradigm': 'o__n'}
    
    # Nouns (plural -i) - could also be other things, be conservative
    if lemma_lower.endswith('i') and len(lemma_lower) > 2:
        return {'pos': 'n', 'paradigm': 'o__n'}
    
    # Adjectives
    if lemma_lower.endswith('a'):
        return {'pos': 'adj', 'paradigm': 'a__adj'}
    
    # Adverbs
    if lemma_lower.endswith('e') and len(lemma_lower) > 2:
        return {'pos': 'adv', 'paradigm': 'e__adv'}
    
    # Unknown
    return {}


def similarity_to_confidence(similarity: float) -> float:
    """
    Convert BERT similarity score to confidence score.
    
    Cap at 0.85 since embeddings are less certain than human-curated sources.
    """
    return min(similarity * 0.90, 0.85)


def convert_bert_to_unified(
    input_path: Path,
    output_path: Path,
    min_similarity: float = 0.85,
    max_candidates: int = 3
) -> Dict[str, Any]:
    """
    Convert BERT translation candidates to unified format.
    """
    print(f"Loading BERT translations from {input_path}...")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        bert_data = json.load(f)
    
    print(f"Found {len(bert_data)} Ido words with translation candidates")
    
    entries = []
    stats = {
        'total_words': len(bert_data),
        'words_with_translations': 0,
        'words_with_morphology': 0,
        'total_translations': 0,
        'skipped_low_similarity': 0,
        'skipped_invalid': 0
    }
    
    for ido_word, candidates in bert_data.items():
        # Skip invalid entries
        if not ido_word or not isinstance(candidates, list):
            stats['skipped_invalid'] += 1
            continue
        
        # Skip special characters or very short words
        if len(ido_word) < 2 or ido_word.startswith('*') or ido_word == '-':
            stats['skipped_invalid'] += 1
            continue
        
        # Filter candidates by similarity
        valid_candidates = [
            c for c in candidates 
            if c.get('similarity', 0) >= min_similarity
        ][:max_candidates]
        
        if not valid_candidates:
            stats['skipped_low_similarity'] += 1
            continue
        
        # Build translations array
        translations = []
        for candidate in valid_candidates:
            epo_word = candidate.get('epo', '')
            similarity = candidate.get('similarity', 0)
            
            if not epo_word or len(epo_word) < 2:
                continue
            
            translations.append({
                'term': epo_word,
                'lang': 'eo',
                'confidence': round(similarity_to_confidence(similarity), 3),
                'source': 'bert_embeddings'
            })
        
        if not translations:
            continue
        
        # Infer morphology
        morphology = infer_ido_morphology(ido_word)
        
        # Build entry
        entry = {
            'lemma': ido_word,
            'source': 'bert_embeddings',
            'translations': translations
        }
        
        if morphology:
            entry['pos'] = morphology.get('pos')
            entry['morphology'] = {'paradigm': morphology.get('paradigm')}
            stats['words_with_morphology'] += 1
        
        entries.append(entry)
        stats['words_with_translations'] += 1
        stats['total_translations'] += len(translations)
    
    # Build unified format
    unified_data = {
        'metadata': {
            'source_name': 'bert_embeddings',
            'version': '1.0',
            'generation_date': datetime.now().isoformat(),
            'description': 'Translation pairs from BERT embedding alignment (XLM-RoBERTa fine-tuned on Ido)',
            'min_similarity_threshold': min_similarity,
            'statistics': {
                'total_entries': len(entries),
                'entries_with_translations': stats['words_with_translations'],
                'entries_with_morphology': stats['words_with_morphology'],
                'total_translations': stats['total_translations']
            }
        },
        'entries': entries
    }
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"CONVERSION COMPLETE")
    print(f"{'='*60}")
    print(f"Output: {output_path}")
    print(f"Entries: {len(entries):,}")
    print(f"With morphology: {stats['words_with_morphology']:,}")
    print(f"Translations: {stats['total_translations']:,}")
    print(f"Skipped (low similarity): {stats['skipped_low_similarity']:,}")
    print(f"Skipped (invalid): {stats['skipped_invalid']:,}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Convert BERT translation candidates to unified JSON format'
    )
    parser.add_argument(
        '--input', '-i',
        type=Path,
        default=Path('results/bert_ido_epo_alignment/translation_candidates.json'),
        help='Path to translation_candidates.json'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=Path('sources/source_bert_embeddings.json'),
        help='Path to write unified JSON output'
    )
    parser.add_argument(
        '--min-similarity',
        type=float,
        default=0.85,
        help='Minimum similarity score (default: 0.85)'
    )
    parser.add_argument(
        '--max-candidates',
        type=int,
        default=3,
        help='Maximum translation candidates per word (default: 3)'
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)
    
    convert_bert_to_unified(
        args.input,
        args.output,
        args.min_similarity,
        args.max_candidates
    )


if __name__ == '__main__':
    main()
