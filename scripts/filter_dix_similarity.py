#!/usr/bin/env python3
"""
Filter Apertium .dix file to remove entries with similarity < 0.8.
Similarity scores are stored in XML comments like: <!-- similarity: 0.xxxx -->
"""

import re
import argparse
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.dom import minidom

def extract_similarity(entry: ET.Element) -> float:
    """Extract similarity score from entry comment."""
    # Get all text content including comments
    text = ET.tostring(entry, encoding='unicode')
    
    # Look for similarity comment
    match = re.search(r'similarity:\s*([0-9.]+)', text)
    if match:
        return float(match.group(1))
    return None

def filter_dix_file(input_file: Path, output_file: Path, min_similarity: float = 0.80):
    """Filter .dix file to remove entries with similarity < min_similarity."""
    print(f"Loading dictionary from {input_file}...")
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    # Find main section
    main_section = root.find('.//section[@id="main"]')
    if main_section is None:
        main_section = root.find('.//section')
    
    if main_section is None:
        print("❌ No section found in dictionary")
        return
    
    entries_before = len(main_section.findall('e'))
    print(f"Found {entries_before} entries")
    
    # Filter entries
    removed = 0
    kept = 0
    
    for entry in list(main_section.findall('e')):
        similarity = extract_similarity(entry)
        
        if similarity is not None:
            if similarity < min_similarity:
                main_section.remove(entry)
                removed += 1
            else:
                kept += 1
        else:
            # No similarity comment - keep it (not from BERT)
            kept += 1
    
    entries_after = len(main_section.findall('e'))
    
    print(f"\nFiltering results:")
    print(f"  Entries before: {entries_before}")
    print(f"  Entries after:  {entries_after}")
    print(f"  Removed: {removed} entries with similarity < {min_similarity}")
    print(f"  Kept: {kept} entries")
    
    # Save filtered dictionary
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
    
    print(f"\n✅ Saved filtered dictionary to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Filter .dix file by similarity threshold')
    parser.add_argument('--input', type=Path, required=True,
                        help='Input .dix file')
    parser.add_argument('--output', type=Path, required=True,
                        help='Output .dix file')
    parser.add_argument('--min-similarity', type=float, default=0.80,
                        help='Minimum similarity threshold (default: 0.80)')
    
    args = parser.parse_args()
    
    filter_dix_file(args.input, args.output, args.min_similarity)

if __name__ == '__main__':
    main()

