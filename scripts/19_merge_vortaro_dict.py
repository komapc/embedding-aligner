#!/usr/bin/env python3
"""
Merge BERT-generated translation pairs into existing vortaro dictionary.json.

This script:
1. Loads existing vortaro dictionary
2. Loads BERT translation pairs
3. Merges translations, marking BERT-generated entries
4. Preserves existing metadata and sources
5. Updates total word count
"""

import json
import argparse
from datetime import datetime
from typing import Dict, List, Set

def load_vortaro_dict(file_path: str) -> Dict:
    """Load existing vortaro dictionary."""
    print(f"📖 Loading existing vortaro: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    word_count = sum(1 for key in data.keys() if key != 'metadata')
    print(f"   Found {word_count} Ido words")
    return data

def load_bert_translations(file_path: str) -> Dict[str, List[str]]:
    """
    Load BERT translation pairs and convert to simple dict format.
    
    Returns:
        Dict mapping Ido word -> List of Esperanto translations
    """
    print(f"📖 Loading BERT translations: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    translations = {}
    for entry in data.get('ido_to_esperanto', []):
        ido_word = entry['ido']
        epo_words = entry['esperanto']
        translations[ido_word] = epo_words
    
    print(f"   Found {len(translations)} Ido words with {sum(len(v) for v in translations.values())} translations")
    return translations

def merge_dictionaries(
    existing: Dict,
    bert_translations: Dict[str, List[str]],
    prefer_existing: bool = False
) -> Dict:
    """
    Merge BERT translations into existing vortaro dictionary.
    
    Args:
        existing: Existing vortaro dictionary
        bert_translations: BERT translations (ido -> [esperanto])
        prefer_existing: If True, don't overwrite existing entries
    
    Returns:
        Merged dictionary with statistics
    """
    print("\n🔄 Merging dictionaries...")
    
    merged = existing.copy()
    stats = {
        'existing_words': sum(1 for k in existing.keys() if k != 'metadata'),
        'bert_words': len(bert_translations),
        'new_words': 0,
        'updated_words': 0,
        'new_translations': 0
    }
    
    for ido_word, epo_words in bert_translations.items():
        if ido_word in existing and ido_word != 'metadata':
            # Word exists - add new translations
            existing_epo = set(existing[ido_word].get('esperanto_words', []))
            new_epo = set(epo_words)
            
            if not prefer_existing or not existing_epo:
                # Add BERT translations that don't exist
                added = new_epo - existing_epo
                if added:
                    merged[ido_word]['esperanto_words'].extend(list(added))
                    stats['new_translations'] += len(added)
                    
                    # Add BERT as source
                    if 'sources' not in merged[ido_word]:
                        merged[ido_word]['sources'] = []
                    if 'bert_alignment' not in merged[ido_word]['sources']:
                        merged[ido_word]['sources'].append('bert_alignment')
                    
                    stats['updated_words'] += 1
        else:
            # New word - add it
            merged[ido_word] = {
                'esperanto_words': epo_words,
                'sources': ['bert_alignment'],
                'morfologio': []
            }
            stats['new_words'] += 1
    
    # Update metadata
    if 'metadata' not in merged:
        merged['metadata'] = {}
    
    merged['metadata']['total_words'] = sum(1 for k in merged.keys() if k != 'metadata')
    merged['metadata']['last_update'] = datetime.now().isoformat()
    
    # Add bert_alignment to sources list
    if 'sources' not in merged['metadata']:
        merged['metadata']['sources'] = []
    if 'bert_alignment' not in merged['metadata']['sources']:
        merged['metadata']['sources'].append('bert_alignment')
    
    merged['metadata']['bert_integration'] = {
        'date': datetime.now().isoformat(),
        'words_added': stats['new_words'],
        'words_updated': stats['updated_words'],
        'translations_added': stats['new_translations']
    }
    
    stats['final_words'] = merged['metadata']['total_words']
    
    return merged, stats

def main():
    parser = argparse.ArgumentParser(
        description='Merge BERT translations into vortaro dictionary'
    )
    parser.add_argument(
        '--existing',
        required=True,
        help='Existing vortaro dictionary.json'
    )
    parser.add_argument(
        '--bert',
        required=True,
        help='BERT translations JSON file'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output dictionary.json (can be same as existing)'
    )
    parser.add_argument(
        '--prefer-existing',
        action='store_true',
        help='Do not add BERT translations if word already has translations'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("VORTARO DICTIONARY MERGER")
    print("="*60)
    print()
    
    # Load dictionaries
    existing = load_vortaro_dict(args.existing)
    bert_translations = load_bert_translations(args.bert)
    
    # Merge
    merged, stats = merge_dictionaries(
        existing,
        bert_translations,
        prefer_existing=args.prefer_existing
    )
    
    # Write output
    print(f"\n💾 Writing merged dictionary: {args.output}")
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    
    # Display statistics
    print()
    print("="*60)
    print("MERGE STATISTICS")
    print("="*60)
    print(f"Existing words:        {stats['existing_words']:>6}")
    print(f"BERT words:            {stats['bert_words']:>6}")
    print(f"New words added:       {stats['new_words']:>6}")
    print(f"Words updated:         {stats['updated_words']:>6}")
    print(f"Translations added:    {stats['new_translations']:>6}")
    print(f"Final total:           {stats['final_words']:>6}")
    print("="*60)
    print()
    print(f"✅ Dictionary merged successfully!")
    print(f"   Output: {args.output}")
    print()
    print(f"Coverage increase: +{stats['new_words']} words, +{stats['new_translations']} translations")
    print(f"  ({100 * stats['new_words'] / stats['existing_words']:.1f}% growth in words)")

if __name__ == '__main__':
    main()

