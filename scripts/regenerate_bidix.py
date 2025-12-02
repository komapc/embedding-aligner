#!/usr/bin/env python3
"""
Regenerate bilingual dictionary (bidix) from multiple JSON sources.

Converts BERT, Vortaro, and Extractor JSON formats to unified bidix XML.
Keeps all translation alternatives from all sources.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from xml.etree import ElementTree as ET
from xml.dom import minidom

# Import format converters and merger
from format_converters import load_and_convert_json, detect_format
from merge_translations import merge_translations_with_stats, print_merge_stats

# Import bidix generation functions from existing script
sys.path.insert(0, str(Path(__file__).parent))
try:
    # Import from 17_format_for_apertium.py using importlib.util
    from importlib import util
    format_script = Path(__file__).parent / '17_format_for_apertium.py'
    spec = util.spec_from_file_location("format_module", format_script)
    format_module = util.module_from_spec(spec)
    spec.loader.exec_module(format_module)
    
    create_dix_entry = format_module.create_dix_entry
    create_dix_document = format_module.create_dix_document
    prettify_xml = format_module.prettify_xml
    guess_pos_ido = format_module.guess_pos_ido
    guess_pos_esperanto = format_module.guess_pos_esperanto
except Exception as e:
    # Fallback: define minimal versions if import fails
    print(f"⚠️  Warning: Could not import from 17_format_for_apertium.py: {e}")
    print("   Using fallback implementations...")
    
    def create_dix_entry(ido_word: str, epo_word: str, similarity: float, 
                         add_pos: bool = True, skip_pos_mismatch: bool = False):
        entry = ET.Element('e')
        comment = ET.Comment(f' similarity: {similarity:.4f} ')
        entry.append(comment)
        pair = ET.SubElement(entry, 'p')
        left = ET.SubElement(pair, 'l')
        right = ET.SubElement(pair, 'r')
        left.text = ido_word
        right.text = epo_word
        return entry
    
    def create_dix_document(entries, direction='ido-epo'):
        root = ET.Element('dictionary')
        alphabet = ET.SubElement(root, 'alphabet')
        sdefs = ET.SubElement(root, 'sdefs')
        # Add common POS tag definitions
        pos_tags = ['n', 'vblex', 'adj', 'adv', 'pr', 'det', 'cnjcoo', 'cnjsub', 'num']
        for tag in pos_tags:
            sdef = ET.SubElement(sdefs, 'sdef')
            sdef.set('n', tag)
        section = ET.SubElement(root, 'section', id='main', type='standard')
        for entry in entries:
            section.append(entry)
        return root
    
    def prettify_xml(elem):
        rough_string = ET.tostring(elem, encoding='unicode')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")


def generate_bidix_from_merged(merged_data: Dict[str, List[Dict[str, Any]]], 
                                min_similarity: float = 0.0,
                                max_translations_per_word: Optional[int] = None,
                                add_pos_tags: bool = True) -> List[ET.Element]:
    """
    Generate bidix XML entries from merged normalized data.
    
    Args:
        merged_data: Merged normalized format dictionary
        min_similarity: Minimum similarity threshold (0.0 = keep all)
        max_translations_per_word: Max translations per word (None = keep all)
        add_pos_tags: Whether to add POS tags
    
    Returns:
        List of XML entry elements
    """
    entries = []
    stats = {
        'total_words': len(merged_data),
        'entries_created': 0,
        'entries_skipped_low_similarity': 0,
        'cognates': 0,
        'with_pos': 0,
        'without_pos': 0
    }
    
    for ido_word, translations in sorted(merged_data.items()):
        # Filter by similarity
        filtered = [t for t in translations if t.get('similarity', 1.0) >= min_similarity]
        
        if not filtered:
            stats['entries_skipped_low_similarity'] += len(translations)
            continue
        
        # Limit translations per word if specified
        if max_translations_per_word:
            # Sort by similarity (highest first) and take top N
            filtered.sort(key=lambda x: x.get('similarity', 0), reverse=True)
            filtered = filtered[:max_translations_per_word]
        
        # Create entry for each translation (keep all alternatives)
        for trans in filtered:
            epo_word = trans['translation']
            similarity = trans.get('similarity', 1.0)
            
            if not epo_word:
                continue
            
            # Create entry
            entry = create_dix_entry(
                ido_word, 
                epo_word, 
                similarity, 
                add_pos=add_pos_tags,
                skip_pos_mismatch=False  # Keep all, don't skip
            )
            
            if entry is not None:
                entries.append(entry)
                stats['entries_created'] += 1
                
                # Check if cognate
                if ido_word == epo_word:
                    stats['cognates'] += 1
                
                # Count POS tagging
                has_pos = entry.find('.//s') is not None
                if has_pos:
                    stats['with_pos'] += 1
                else:
                    stats['without_pos'] += 1
    
    return entries, stats


def main():
    parser = argparse.ArgumentParser(
        description='Regenerate bilingual dictionary from multiple JSON sources'
    )
    parser.add_argument(
        '--json',
        action='append',
        required=True,
        type=Path,
        dest='json_files',
        help='JSON source file (can be specified multiple times)'
    )
    parser.add_argument(
        '--format',
        action='append',
        type=str,
        dest='formats',
        help='Format type for each JSON file (bert|vortaro|extractor). Auto-detected if not specified.'
    )
    parser.add_argument(
        '--output',
        required=True,
        type=Path,
        help='Output bidix XML file path'
    )
    parser.add_argument(
        '--min-similarity',
        type=float,
        default=0.0,
        help='Minimum similarity threshold (default: 0.0 = keep all)'
    )
    parser.add_argument(
        '--max-translations',
        type=int,
        default=None,
        help='Maximum translations per word (default: None = keep all)'
    )
    parser.add_argument(
        '--add-pos-tags',
        action='store_true',
        default=True,
        help='Add POS tags based on morphology (default: True)'
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    script_dir = Path(__file__).parent
    json_files = [f.resolve() if not f.is_absolute() else f for f in args.json_files]
    output_file = args.output.resolve() if not args.output.is_absolute() else args.output
    
    print("="*70)
    print("REGENERATE BIDIX FROM JSON SOURCES")
    print("="*70)
    print(f"\nInput files ({len(json_files)}):")
    for i, json_file in enumerate(json_files):
        format_str = f" (format: {args.formats[i]})" if args.formats and i < len(args.formats) else ""
        print(f"  {i+1}. {json_file}{format_str}")
    print(f"\nOutput: {output_file}")
    print(f"Min similarity: {args.min_similarity}")
    if args.max_translations:
        print(f"Max translations per word: {args.max_translations}")
    
    # Step 1: Load and convert all JSON files
    print(f"\n{'='*70}")
    print("STEP 1: Loading and converting JSON files")
    print(f"{'='*70}")
    
    normalized_sources = []
    source_names = []
    
    for i, json_file in enumerate(json_files):
        if not json_file.exists():
            print(f"❌ ERROR: File not found: {json_file}")
            sys.exit(1)
        
        format_type = args.formats[i] if args.formats and i < len(args.formats) else None
        source_name = json_file.stem
        
        print(f"\nProcessing {i+1}/{len(json_files)}: {json_file.name}")
        try:
            normalized, detected_format = load_and_convert_json(json_file, format_type, source_name)
            used_format = format_type or detected_format
            print(f"  Format: {used_format}")
            print(f"  Words: {len(normalized):,}")
            total_trans = sum(len(trans) for trans in normalized.values())
            print(f"  Translations: {total_trans:,}")
            
            normalized_sources.append(normalized)
            source_names.append(source_name)
        except Exception as e:
            print(f"❌ ERROR processing {json_file}: {e}")
            sys.exit(1)
    
    # Step 2: Merge all sources
    print(f"\n{'='*70}")
    print("STEP 2: Merging all sources")
    print(f"{'='*70}")
    
    merged, merge_stats = merge_translations_with_stats(normalized_sources, source_names)
    print_merge_stats(merge_stats)
    
    # Step 3: Generate bidix XML
    print(f"\n{'='*70}")
    print("STEP 3: Generating bidix XML")
    print(f"{'='*70}")
    
    entries, bidix_stats = generate_bidix_from_merged(
        merged,
        min_similarity=args.min_similarity,
        max_translations_per_word=args.max_translations,
        add_pos_tags=args.add_pos_tags
    )
    
    print(f"\n✅ Created {bidix_stats['entries_created']:,} bidix entries")
    print(f"   Words: {bidix_stats['total_words']:,}")
    print(f"   Cognates: {bidix_stats['cognates']:,}")
    print(f"   With POS: {bidix_stats['with_pos']:,}")
    print(f"   Without POS: {bidix_stats['without_pos']:,}")
    if bidix_stats['entries_skipped_low_similarity'] > 0:
        print(f"   Skipped (low similarity): {bidix_stats['entries_skipped_low_similarity']:,}")
    
    # Step 4: Create bidix document and save
    print(f"\n{'='*70}")
    print("STEP 4: Saving bidix file")
    print(f"{'='*70}")
    
    dix_root = create_dix_document(entries, direction='ido-epo')
    xml_string = prettify_xml(dix_root)
    
    # Add XML declaration
    xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n' + '\n'.join(xml_string.split('\n')[1:])
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    
    print(f"\n✅ Saved bidix to: {output_file}")
    print(f"\n{'='*70}")
    print("✅ BIDIX REGENERATION COMPLETE")
    print(f"{'='*70}")
    print(f"\nNext steps:")
    print(f"1. Validate XML: xmllint --noout {output_file}")
    print(f"2. Regenerate monodix: python3 regenerate_monodix.py --bidix {output_file}")
    print(f"3. Rebuild analyzer: cd {output_file.parent} && make clean && make")


if __name__ == '__main__':
    main()

