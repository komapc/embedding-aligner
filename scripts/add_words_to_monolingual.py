#!/usr/bin/env python3
"""
Add missing words to monolingual Ido dictionary.
"""

from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom

# Words to add with their paradigms
WORDS_TO_ADD = {
    'partoprenis': 'is__vblex',  # past tense
    'vorti': 'i__n_pl',  # plural
    'detali': 'i__n_pl',  # plural
    'questiono': 'o__n',
    'remplacigar': 'ar__vblex',
    'adjuntar': 'ar__vblex',
    'existanta': 'anta__adj',  # present participle adjective
}

def add_words_to_monolingual(dix_file: Path, output_file: Path, words: dict):
    """Add words to monolingual dictionary."""
    print(f"Loading monolingual dictionary from {dix_file}...")
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
        i_elem = entry.find('i')
        if i_elem is not None and i_elem.text:
            existing_words.add(i_elem.text.strip())
    
    print(f"Found {len(existing_words)} existing entries")
    
    # Add missing words
    added = 0
    skipped = 0
    
    for word, paradigm in words.items():
        if word in existing_words:
            print(f"  ⏭️  Skipping {word} (already exists)")
            skipped += 1
            continue
        
        # Create entry
        entry = ET.Element('e')
        lemma = ET.SubElement(entry, 'i')
        lemma.text = word
        par = ET.SubElement(entry, 'par')
        par.set('n', paradigm)
        
        main_section.append(entry)
        print(f"  ✅ Added {word} (paradigm: {paradigm})")
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
    import argparse
    parser = argparse.ArgumentParser(description='Add words to monolingual dictionary')
    parser.add_argument('--dix', type=Path, required=True,
                        help='Input monolingual .dix file')
    parser.add_argument('--output', type=Path, required=True,
                        help='Output .dix file')
    
    args = parser.parse_args()
    add_words_to_monolingual(args.dix, args.output, WORDS_TO_ADD)

if __name__ == '__main__':
    main()





