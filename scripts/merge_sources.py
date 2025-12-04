#!/usr/bin/env python3
"""
Merge all source JSON files into unified merged files.

All sources must use the unified format. Implements intelligent deduplication
with multi-source provenance tracking.

Deduplication strategy:
- Same lemma + same translation → Merge sources, take max confidence
- Same lemma + different translations → Keep all variants
- Same lemma + different POS → Keep as separate entries, flag conflict
- Same lemma + different morphology → Prefer lexicon > wiktionary > bert

Morphology inference:
- If an entry has no morphology, infer from Ido word endings
- Ido is highly regular: -o (noun), -a (adj), -ar (verb), -e (adv)
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from collections import defaultdict

# Import validation
sys.path.insert(0, str(Path(__file__).parent))
from validate_schema import load_schema, validate_file


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
    if len(lemma_lower) < 2:
        return {}
    
    # Skip if not mostly alphabetic
    if not lemma_lower.replace('-', '').replace('.', '').isalpha():
        return {}
    
    # Verb infinitives (most specific)
    if lemma_lower.endswith('ar'):
        return {'pos': 'vblex', 'paradigm': 'ar__vblex'}
    
    # Verb conjugated forms
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
    
    # Nouns (plural -i)
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


def apply_morphology_inference(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply morphology inference to all entries that don't have morphology.
    """
    inferred_count = 0
    
    for entry in entries:
        # Skip if already has morphology
        if entry.get('morphology', {}).get('paradigm'):
            continue
        
        # Try to infer
        inferred = infer_ido_morphology(entry.get('lemma', ''))
        if inferred:
            entry['pos'] = inferred.get('pos')
            entry['morphology'] = {'paradigm': inferred.get('paradigm')}
            inferred_count += 1
    
    print(f"  Morphology inferred for {inferred_count:,} entries")
    return entries


def load_source_file(file_path: Path, schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Load and validate a source file."""
    print(f"Loading {file_path.name}...")
    
    is_valid, errors = validate_file(file_path, schema)
    if not is_valid:
        print(f"ERROR: {file_path.name} failed validation:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entries = data.get('entries', [])
    source_name = data.get('metadata', {}).get('source_name', file_path.stem)
    
    print(f"  ✅ Loaded {len(entries):,} entries from {source_name}")
    return entries


def deduplicate_translations(translations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate translations: merge identical ones, keep different ones.
    
    Returns translations with sources array and max confidence.
    """
    # Group by (term, lang)
    grouped = defaultdict(list)
    for trans in translations:
        key = (trans['term'], trans['lang'])
        grouped[key].append(trans)
    
    deduplicated = []
    for (term, lang), trans_group in grouped.items():
        if len(trans_group) == 1:
            # Single translation - convert to sources array
            trans = trans_group[0].copy()
            if 'source' in trans and 'sources' not in trans:
                trans['sources'] = [trans['source']]
                del trans['source']
            deduplicated.append(trans)
        else:
            # Multiple identical translations - merge
            merged_trans = {
                'term': term,
                'lang': lang,
                'confidence': max(t['confidence'] for t in trans_group),
                'sources': []
            }
            
            # Collect all sources
            for trans in trans_group:
                if 'source' in trans:
                    merged_trans['sources'].append(trans['source'])
                elif 'sources' in trans:
                    merged_trans['sources'].extend(trans['sources'])
            
            # Deduplicate sources
            merged_trans['sources'] = sorted(list(set(merged_trans['sources'])))
            deduplicated.append(merged_trans)
    
    return deduplicated


def merge_entry_group(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple entries with same lemma (handles entries with/without POS)."""
    base_entry = entries[0].copy()
    
    # Collect all translations
    all_translations = []
    for entry in entries:
        all_translations.extend(entry.get('translations', []))
    
    # Deduplicate translations
    merged_translations = deduplicate_translations(all_translations)
    base_entry['translations'] = merged_translations
    
    # Merge POS (prefer lexicon > wiktionary > bert)
    pos_priority = {'ido_lexicon': 3, 'io_wiktionary': 2, 'eo_wiktionary': 2, 'bert': 1}
    best_pos = None
    best_pos_priority = 0
    
    for entry in entries:
        if entry.get('pos'):
            source = entry.get('source', '')
            priority = pos_priority.get(source, 0)
            if priority > best_pos_priority:
                best_pos = entry['pos']
                best_pos_priority = priority
    
    if best_pos:
        base_entry['pos'] = best_pos
    
    # Merge morphology (prefer lexicon > wiktionary > bert)
    morphology_priority = {'ido_lexicon': 3, 'io_wiktionary': 2, 'eo_wiktionary': 2, 'bert': 1}
    best_morphology = None
    best_priority = 0
    
    for entry in entries:
        if 'morphology' in entry and entry['morphology'].get('paradigm'):
            source = entry.get('source', '')
            priority = morphology_priority.get(source, 0)
            if priority > best_priority:
                best_morphology = entry['morphology']
                best_priority = priority
    
    if best_morphology:
        base_entry['morphology'] = best_morphology
    
    # Collect all sources
    all_sources = list(set(entry.get('source') for entry in entries if entry.get('source')))
    if len(all_sources) > 1:
        base_entry['metadata'] = base_entry.get('metadata', {})
        base_entry['metadata']['merged_from_sources'] = sorted(all_sources)
    
    return base_entry


def deduplicate_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Intelligently deduplicate entries with multi-source provenance.
    
    Strategy:
    - Group by (lemma, pos)
    - Merge identical translations → sources array, max confidence
    - Keep different translations
    - Prefer lexicon morphology
    """
    # Group entries by lemma only (not pos)
    # This allows merging entries where one source has POS and another doesn't
    grouped = defaultdict(list)
    for entry in entries:
        key = entry['lemma'].strip().lower()  # Just lemma, not (lemma, pos)
        grouped[key].append(entry)
    
    deduplicated = []
    stats = {
        'original_count': len(entries),
        'merged_count': 0,
        'pos_conflicts': 0
    }
    
    for lemma, entry_group in grouped.items():
        if len(entry_group) == 1:
            # No duplicates
            entry = entry_group[0]
            # Convert single source to sources array in translations
            for trans in entry.get('translations', []):
                if 'source' in trans and 'sources' not in trans:
                    trans['sources'] = [trans['source']]
                    del trans['source']
            deduplicated.append(entry)
            continue
        
        # Multiple entries with same lemma - merge them
        merged_entry = merge_entry_group(entry_group)
        deduplicated.append(merged_entry)
        stats['merged_count'] += len(entry_group) - 1
    
    print(f"\nDeduplication stats:")
    print(f"  Original entries: {stats['original_count']:,}")
    print(f"  After deduplication: {len(deduplicated):,}")
    print(f"  Entries merged: {stats['merged_count']:,}")
    
    return deduplicated


def merge_all_sources(sources_dir: Path, schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge all source JSON files with intelligent deduplication.
    
    Returns merged data with deduplicated entries and multi-source provenance.
    """
    source_files = sorted(sources_dir.glob('source_*.json'))
    
    if not source_files:
        print(f"ERROR: No source_*.json files found in {sources_dir}")
        sys.exit(1)
    
    print(f"\n{'='*70}")
    print(f"MERGING {len(source_files)} SOURCE FILES")
    print(f"{'='*70}\n")
    
    all_entries = []
    source_stats = defaultdict(int)
    
    for source_file in source_files:
        entries = load_source_file(source_file, schema)
        all_entries.extend(entries)
        
        # Track statistics
        source_name = source_file.stem.replace('source_', '')
        source_stats[source_name] = len(entries)
    
    print(f"\n{'='*70}")
    print(f"DEDUPLICATING ENTRIES")
    print(f"{'='*70}")
    
    # Deduplicate with multi-source provenance
    deduplicated_entries = deduplicate_entries(all_entries)
    
    print(f"\n{'='*70}")
    print(f"INFERRING MORPHOLOGY")
    print(f"{'='*70}")
    
    # Apply morphology inference to entries without paradigms
    deduplicated_entries = apply_morphology_inference(deduplicated_entries)
    
    print(f"\n{'='*70}")
    print(f"MERGE COMPLETE")
    print(f"{'='*70}")
    print(f"Total entries after deduplication: {len(deduplicated_entries):,}")
    print(f"\nPer-source breakdown (before deduplication):")
    for source, count in sorted(source_stats.items()):
        print(f"  {source}: {count:,} entries")
    
    # Create merged metadata
    merged_metadata = {
        "source_name": "merged",
        "version": "1.0",
        "generation_date": datetime.now().isoformat(),
        "statistics": {
            "total_entries": len(deduplicated_entries),
            "original_entries_before_dedup": len(all_entries),
            "sources": dict(source_stats),
            "entries_with_translations": sum(1 for e in deduplicated_entries if e.get('translations')),
            "entries_with_morphology": sum(1 for e in deduplicated_entries if e.get('morphology', {}).get('paradigm'))
        }
    }
    
    return {
        "metadata": merged_metadata,
        "entries": deduplicated_entries
    }


def separate_bidix_monodix(merged_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Separate merged data into bidix (with translations) and monodix (all entries).
    
    Returns:
        (bidix_data, monodix_data)
    """
    entries = merged_data['entries']
    
    # Bidix: entries with Esperanto translations
    bidix_entries = [
        entry for entry in entries
        if any(t.get('lang') == 'eo' for t in entry.get('translations', []))
    ]
    
    # Monodix: all Ido entries (for morphological analysis)
    monodix_entries = entries
    
    bidix_metadata = {
        **merged_data['metadata'],
        "source_name": "merged_bidix",
        "statistics": {
            **merged_data['metadata']['statistics'],
            "total_entries": len(bidix_entries)
        }
    }
    
    monodix_metadata = {
        **merged_data['metadata'],
        "source_name": "merged_monodix",
        "statistics": {
            **merged_data['metadata']['statistics'],
            "total_entries": len(monodix_entries)
        }
    }
    
    return (
        {"metadata": bidix_metadata, "entries": bidix_entries},
        {"metadata": monodix_metadata, "entries": monodix_entries}
    )


def main():
    script_dir = Path(__file__).parent
    data_dir = script_dir.parent
    sources_dir = data_dir / 'sources'
    merged_dir = data_dir / 'merged'
    schema_path = data_dir / 'schema.json'
    
    if not sources_dir.exists():
        print(f"ERROR: Sources directory not found: {sources_dir}")
        sys.exit(1)
    
    if not schema_path.exists():
        print(f"ERROR: Schema not found: {schema_path}")
        sys.exit(1)
    
    schema = load_schema(schema_path)
    
    # Merge all sources
    merged_data = merge_all_sources(sources_dir, schema)
    
    # Separate into bidix and monodix
    bidix_data, monodix_data = separate_bidix_monodix(merged_data)
    
    # Save merged files
    merged_dir.mkdir(parents=True, exist_ok=True)
    
    bidix_path = merged_dir / 'merged_bidix.json'
    monodix_path = merged_dir / 'merged_monodix.json'
    
    print(f"\n{'='*70}")
    print(f"SAVING MERGED FILES")
    print(f"{'='*70}")
    
    with open(bidix_path, 'w', encoding='utf-8') as f:
        json.dump(bidix_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved bidix: {bidix_path}")
    print(f"   Entries: {len(bidix_data['entries']):,}")
    
    with open(monodix_path, 'w', encoding='utf-8') as f:
        json.dump(monodix_data, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved monodix: {monodix_path}")
    print(f"   Entries: {len(monodix_data['entries']):,}")
    
    print(f"\n{'='*70}")
    print(f"✅ MERGE COMPLETE")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
