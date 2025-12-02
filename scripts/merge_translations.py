#!/usr/bin/env python3
"""
Merge multiple normalized translation dictionaries keeping all alternatives.

All translations from all sources are preserved - no deduplication.
"""

from typing import Dict, List, Any, Set
from collections import defaultdict


def merge_all_translations(sources: List[Dict[str, List[Dict[str, Any]]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Merge multiple normalized translation dictionaries.
    
    For each Ido word, combines ALL translations from all sources.
    Keeps all translations even if duplicates exist.
    
    Args:
        sources: List of normalized format dicts, each with format:
            {
                "ido_word": [
                    {"translation": "epo_word", "similarity": 0.95, "source": "bert"}
                ]
            }
    
    Returns:
        Merged dictionary with all translations preserved
    """
    merged = defaultdict(list)
    stats = {
        'total_words': 0,
        'words_with_multiple_sources': 0,
        'total_translations': 0,
        'sources': set()
    }
    
    # Collect all translations for each Ido word
    for source_dict in sources:
        for ido_word, translations in source_dict.items():
            if not translations:
                continue
            
            # Add all translations from this source
            for trans in translations:
                merged[ido_word].append(trans)
                stats['sources'].add(trans.get('source', 'unknown'))
                stats['total_translations'] += 1
    
    # Convert defaultdict to regular dict and sort
    result = {}
    for ido_word in sorted(merged.keys()):
        translations = merged[ido_word]
        result[ido_word] = translations
        
        # Count words with multiple sources
        sources_for_word = {t.get('source', 'unknown') for t in translations}
        if len(sources_for_word) > 1:
            stats['words_with_multiple_sources'] += 1
    
    stats['total_words'] = len(result)
    
    return result, stats


def merge_translations_with_stats(sources: List[Dict[str, List[Dict[str, Any]]]], 
                                  source_names: List[str] = None) -> tuple:
    """
    Merge translations and return detailed statistics.
    
    Args:
        sources: List of normalized format dicts
        source_names: Optional list of source names for statistics
    
    Returns:
        (merged_dict, statistics_dict)
    """
    if source_names is None:
        source_names = [f"source_{i}" for i in range(len(sources))]
    
    merged, stats = merge_all_translations(sources)
    
    # Add per-source statistics
    per_source_counts = defaultdict(int)
    per_source_words = defaultdict(set)
    
    for idx, source_dict in enumerate(sources):
        source_name = source_names[idx]
        for ido_word, translations in source_dict.items():
            per_source_counts[source_name] += len(translations)
            per_source_words[source_name].add(ido_word)
    
    stats['per_source'] = {
        name: {
            'translations': per_source_counts[name],
            'words': len(per_source_words[name])
        }
        for name in source_names
    }
    
    return merged, stats


def print_merge_stats(stats: Dict[str, Any]):
    """Print formatted merge statistics."""
    print("\n" + "="*60)
    print("MERGE STATISTICS")
    print("="*60)
    print(f"Total Ido words: {stats['total_words']:,}")
    print(f"Total translations: {stats['total_translations']:,}")
    print(f"Words with multiple sources: {stats['words_with_multiple_sources']:,}")
    print(f"\nSources: {', '.join(sorted(stats['sources']))}")
    
    if 'per_source' in stats:
        print("\nPer-source breakdown:")
        for source_name, source_stats in stats['per_source'].items():
            print(f"  {source_name}:")
            print(f"    Words: {source_stats['words']:,}")
            print(f"    Translations: {source_stats['translations']:,}")


if __name__ == '__main__':
    # Test the merger
    import json
    from pathlib import Path
    
    # Sample test data
    source1 = {
        "test": [
            {"translation": "testo", "similarity": 0.95, "source": "bert"}
        ]
    }
    
    source2 = {
        "test": [
            {"translation": "testo", "similarity": 0.90, "source": "vortaro"},
            {"translation": "provo", "similarity": 0.85, "source": "vortaro"}
        ]
    }
    
    merged, stats = merge_all_translations([source1, source2])
    
    print("Merged result:")
    print(json.dumps(merged, indent=2))
    
    print_merge_stats(stats)
    
    assert len(merged["test"]) == 3, "Should have 3 translations (all kept)"
    print("\n✅ Test passed: All translations preserved")

