#!/usr/bin/env python3
"""
Convert BERT translation pairs to Apertium .dix dictionary format.

This script generates valid Apertium XML dictionary entries from
BERT alignment results, including POS tagging when possible.
"""

import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from xml.etree import ElementTree as ET
from xml.dom import minidom

def load_translation_candidates(input_file: str) -> Dict[str, List[Dict]]:
    """Load translation candidates from JSON."""
    print(f"Loading translation candidates from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"✅ Loaded {len(data)} Ido words with candidates")
    return data

def guess_pos_ido(word: str) -> str:
    """
    Guess part-of-speech for Ido word based on suffix.
    
    Ido morphology rules:
    - -ar: verb infinitive (manjar, irar)
    - -o: noun (hundo, libro)
    - -a: adjective (bela, granda)
    - -e: adverb (rapide, bone)
    - -i: verb (past participle or irregular)
    """
    if word.endswith('ar'):
        return 'vblex'  # lexical verb
    elif word.endswith('o'):
        return 'n'      # noun
    elif word.endswith('a'):
        return 'adj'    # adjective
    elif word.endswith('e'):
        return 'adv'    # adverb
    elif word.endswith('is') or word.endswith('as') or word.endswith('os'):
        return 'vblex'  # conjugated verb
    else:
        return 'unknown'

def guess_pos_esperanto(word: str) -> str:
    """
    Guess part-of-speech for Esperanto word based on suffix.
    
    Esperanto morphology rules:
    - -i: verb infinitive (manĝi, iri)
    - -o: noun (hundo, libro)
    - -a: adjective (bela, granda)
    - -e: adverb (rapide, bone)
    """
    if word.endswith('i'):
        return 'vblex'  # lexical verb
    elif word.endswith('o'):
        return 'n'      # noun
    elif word.endswith('a'):
        return 'adj'    # adjective
    elif word.endswith('e'):
        return 'adv'    # adverb
    elif word.endswith('as') or word.endswith('is') or word.endswith('os'):
        return 'vblex'  # conjugated verb
    else:
        return 'unknown'

def pos_tags_match(ido_word: str, epo_word: str) -> bool:
    """Check if POS tags match between Ido and Esperanto words."""
    ido_pos = guess_pos_ido(ido_word)
    epo_pos = guess_pos_esperanto(epo_word)
    
    # Unknown tags don't match
    if ido_pos == 'unknown' or epo_pos == 'unknown':
        return False
    
    return ido_pos == epo_pos

def create_dix_entry(ido_word: str, epo_word: str, similarity: float, add_pos: bool = True, skip_pos_mismatch: bool = True) -> Optional[ET.Element]:
    """
    Create an Apertium .dix dictionary entry.
    
    Format:
    <e><p><l>ido_word</l><r>epo_word</r></p></e>
    
    With POS:
    <e><p><l>ido_word<s n="pos"/></l><r>epo_word<s n="pos"/></r></p></e>
    """
    # Check POS match, but don't skip if skip_pos_mismatch is False
    if add_pos and skip_pos_mismatch and not pos_tags_match(ido_word, epo_word):
        return None
    
    entry = ET.Element('e')
    
    # Add comment with similarity score
    comment = ET.Comment(f' similarity: {similarity:.4f} ')
    entry.append(comment)
    
    pair = ET.SubElement(entry, 'p')
    left = ET.SubElement(pair, 'l')
    right = ET.SubElement(pair, 'r')
    
    if add_pos:
        pos_ido = guess_pos_ido(ido_word)
        pos_epo = guess_pos_esperanto(epo_word)
        
        if pos_ido != 'unknown' and pos_epo != 'unknown' and pos_ido == pos_epo:
            # Add POS tags
            left.text = ido_word
            s_left = ET.SubElement(left, 's')
            s_left.set('n', pos_ido)
            
            right.text = epo_word
            s_right = ET.SubElement(right, 's')
            s_right.set('n', pos_epo)
        else:
            # No POS tags
            left.text = ido_word
            right.text = epo_word
    else:
        left.text = ido_word
        right.text = epo_word
    
    return entry

def create_dix_document(
    entries: List[ET.Element],
    direction: str = 'ido-epo'
) -> ET.Element:
    """Create complete Apertium .dix XML document."""
    root = ET.Element('dictionary')
    
    # Add alphabet (empty for now)
    alphabet = ET.SubElement(root, 'alphabet')
    
    # Add symbol definitions (sdefs)
    sdefs = ET.SubElement(root, 'sdefs')
    
    # Common POS tags
    pos_tags = {
        'n': 'Noun',
        'vblex': 'Lexical verb',
        'adj': 'Adjective',
        'adv': 'Adverb',
        'prn': 'Pronoun',
        'det': 'Determiner',
        'prep': 'Preposition',
        'cnjcoo': 'Coordinating conjunction',
        'cnjsub': 'Subordinating conjunction',
        'num': 'Numeral'
    }
    
    for tag, description in pos_tags.items():
        sdef = ET.SubElement(sdefs, 'sdef')
        sdef.set('n', tag)
        # Don't add comments inside sdef - they must be empty elements
    
    # Add main section with entries
    section = ET.SubElement(root, 'section')
    section.set('id', 'main')
    section.set('type', 'standard')
    
    for entry in entries:
        section.append(entry)
    
    return root

def prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string."""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def filter_and_format(
    data: Dict[str, List[Dict]],
    min_similarity: float = 0.80,
    max_candidates: int = 1,
    add_pos_tags: bool = True,
    bidirectional: bool = True
) -> Tuple[List[ET.Element], Dict]:
    """Filter candidates and create .dix entries."""
    print(f"\nFormatting for Apertium...")
    print(f"  Min similarity: {min_similarity}")
    print(f"  Max candidates: {max_candidates}")
    print(f"  Add POS tags: {add_pos_tags}")
    print(f"  Bidirectional: {bidirectional}")
    
    entries = []
    stats = {
        'total_processed': 0,
        'entries_created': 0,
        'cognates': 0,
        'with_pos': 0,
        'without_pos': 0,
        'skipped_pos_mismatch': 0
    }
    
    for ido_word, candidates in sorted(data.items()):
        stats['total_processed'] += 1
        
        # Filter by similarity
        high_quality = [
            c for c in candidates
            if c['similarity'] >= min_similarity
        ]
        
        # Take top N candidates
        for candidate in high_quality[:max_candidates]:
            epo_word = candidate.get('translation', candidate.get('epo', ''))
            similarity = candidate['similarity']
            
            if not epo_word:
                continue
            
            # Create entry (allow entries without matching POS tags - don't skip them)
            entry = create_dix_entry(ido_word, epo_word, similarity, add_pos_tags, skip_pos_mismatch=False)
            
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
            else:
                stats['skipped_pos_mismatch'] += 1
    
    print(f"\n✅ Created {stats['entries_created']} dictionary entries")
    print(f"   Cognates: {stats['cognates']} ({100*stats['cognates']/stats['entries_created']:.1f}%)")
    print(f"   With POS: {stats['with_pos']} ({100*stats['with_pos']/stats['entries_created']:.1f}%)")
    print(f"   Without POS: {stats['without_pos']}")
    print(f"   Skipped (POS mismatch): {stats['skipped_pos_mismatch']}")
    
    return entries, stats

def main():
    parser = argparse.ArgumentParser(
        description='Convert BERT translation pairs to Apertium .dix format'
    )
    parser.add_argument(
        '--input',
        required=True,
        help='Input JSON file with translation candidates'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output directory for .dix files'
    )
    parser.add_argument(
        '--min-similarity',
        type=float,
        default=0.80,
        help='Minimum similarity threshold (default: 0.80)'
    )
    parser.add_argument(
        '--max-candidates',
        type=int,
        default=1,
        help='Maximum candidates per word (default: 1)'
    )
    parser.add_argument(
        '--add-pos-tags',
        action='store_true',
        help='Add POS tags based on morphology'
    )
    parser.add_argument(
        '--bidirectional',
        action='store_true',
        help='Create bidirectional entries (ido↔epo)'
    )
    parser.add_argument(
        '--format',
        choices=['xml', 'dix'],
        default='dix',
        help='Output format (default: dix)'
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("APERTIUM .DIX FORMATTER")
    print("="*60)
    
    # Load data
    data = load_translation_candidates(args.input)
    
    # Filter and format
    entries, stats = filter_and_format(
        data,
        min_similarity=args.min_similarity,
        max_candidates=args.max_candidates,
        add_pos_tags=args.add_pos_tags,
        bidirectional=args.bidirectional
    )
    
    # Create .dix document
    dix_root = create_dix_document(entries, direction='ido-epo')
    
    # Save to file
    output_file = output_dir / 'ido-epo.dix'
    xml_string = prettify_xml(dix_root)
    
    # Add XML declaration
    xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n' + '\n'.join(xml_string.split('\n')[1:])
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    
    print(f"\n✅ Saved .dix to {output_file}")
    
    # Save statistics
    stats_file = output_dir / 'apertium_format_stats.json'
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2)
    print(f"✅ Statistics saved to {stats_file}")
    
    print("\n" + "="*60)
    print("✅ APERTIUM FORMATTING COMPLETE")
    print("="*60)
    print(f"\nOutput: {output_file}")
    print(f"Entries: {stats['entries_created']}")
    print("\nNext steps:")
    print("1. Validate XML: xmllint --noout --dtdvalid /path/to/dix.dtd ido-epo.dix")
    print("2. Merge with existing dictionary")
    print("3. Compile and test")

if __name__ == '__main__':
    main()

