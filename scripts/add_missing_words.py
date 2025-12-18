#!/usr/bin/env python3
"""
Add missing words to Apertium dictionary for sentence translation improvement.
"""

import argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom

# Missing words and their translations
MISSING_WORDS = {
    'partoprenis': {
        'epo': 'partoprenis',
        'paradigm': 'is__vblex',
        'pos': 'vblex',
        'comment': 'past tense of partoprenar (to participate)'
    },
    'vorti': {
        'epo': 'vortoj',
        'paradigm': 'i__n_pl',
        'pos': 'n',
        'comment': 'plural of vorto (words)'
    },
    'detali': {
        'epo': 'detaloj',
        'paradigm': 'i__n_pl',
        'pos': 'n',
        'comment': 'plural of detalo (details)'
    },
    'questiono': {
        'epo': 'demando',
        'paradigm': 'o__n',
        'pos': 'n',
        'comment': 'question'
    },
    'remplacigar': {
        'epo': 'anstataŭigi',
        'paradigm': 'ar__vblex',
        'pos': 'vblex',
        'comment': 'to replace'
    },
    'adjuntar': {
        'epo': 'aldoni',
        'paradigm': 'ar__vblex',
        'pos': 'vblex',
        'comment': 'to add/attach'
    },
    'existanta': {
        'epo': 'ekzistantaj',
        'paradigm': 'anta__adj',
        'pos': 'adj',
        'comment': 'existing (present participle adjective)'
    }
}

def create_dix_entry(ido_word: str, epo_word: str, paradigm: str, pos: str, comment: str = None):
    """Create a .dix entry element."""
    entry = ET.Element('e')
    
    if comment:
        comment_elem = ET.Comment(f' {comment} ')
        entry.append(comment_elem)
    
    pair = ET.SubElement(entry, 'p')
    left = ET.SubElement(pair, 'l')
    right = ET.SubElement(pair, 'r')
    
    left.text = ido_word
    s_left = ET.SubElement(left, 's')
    s_left.set('n', pos)
    
    right.text = epo_word
    s_right = ET.SubElement(right, 's')
    s_right.set('n', pos)
    
    return entry

def add_words_to_dix(dix_file: Path, output_file: Path, words: dict):
    """Add missing words to .dix file."""
    print(f"Loading dictionary from {dix_file}...")
    tree = ET.parse(dix_file)
    root = tree.getroot()
    
    # Find main section
    main_section = root.find('.//section[@id="main"]')
    if main_section is None:
        main_section = root.find('.//section')
    
    if main_section is None:
        raise ValueError("No section found in dictionary")
    
    # Get existing words
    existing_words = set()
    for entry in main_section.findall('e'):
        l_elem = entry.find('.//l')
        if l_elem is not None and l_elem.text:
            existing_words.add(l_elem.text.strip())
    
    print(f"Found {len(existing_words)} existing entries")
    
    # Add missing words
    added = 0
    skipped = 0
    
    for ido_word, word_data in words.items():
        if ido_word in existing_words:
            print(f"  ⏭️  Skipping {ido_word} (already exists)")
            skipped += 1
            continue
        
        epo_word = word_data['epo']
        paradigm = word_data['paradigm']
        pos = word_data['pos']
        comment = word_data.get('comment', '')
        
        entry = create_dix_entry(ido_word, epo_word, paradigm, pos, comment)
        main_section.append(entry)
        print(f"  ✅ Added {ido_word} → {epo_word} ({pos})")
        added += 1
    
    print(f"\nAdded {added} words, skipped {skipped}")
    
    # Save dictionary
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Pretty print
    xml_string = ET.tostring(root, encoding='unicode')
    reparsed = minidom.parseString(xml_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")
    
    # Remove extra newlines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    xml_string = '\n'.join(lines)
    
    # Ensure XML declaration
    if not xml_string.startswith('<?xml'):
        xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_string
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    
    print(f"\n✅ Saved dictionary to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Add missing words to Apertium dictionary')
    parser.add_argument('--dix', type=Path, required=True,
                        help='Input .dix file')
    parser.add_argument('--output', type=Path, required=True,
                        help='Output .dix file')
    parser.add_argument('--words', type=str, nargs='+',
                        help='Specific words to add (default: all missing words)')
    
    args = parser.parse_args()
    
    words_to_add = MISSING_WORDS
    if args.words:
        words_to_add = {k: v for k, v in MISSING_WORDS.items() if k in args.words}
    
    add_words_to_dix(args.dix, args.output, words_to_add)

if __name__ == '__main__':
    main()





