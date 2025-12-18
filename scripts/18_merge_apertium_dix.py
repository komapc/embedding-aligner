#!/usr/bin/env python3
"""
Merge BERT-generated dictionary entries into existing Apertium dictionary.

This script:
1. Parses both dictionaries (existing and new)
2. Checks for duplicate entries
3. Merges non-duplicates into existing dictionary
4. Sorts entries alphabetically
5. Writes updated dictionary
"""

import argparse
import re
from xml.etree import ElementTree as ET
from xml.dom import minidom
from typing import List, Set, Tuple

def extract_word_from_entry(entry: ET.Element) -> str:
    """Extract the Ido word (left side) from a dictionary entry."""
    l_element = entry.find('.//l')
    if l_element is not None:
        # Get text before any <s> tags
        text = l_element.text or ''
        return text.strip()
    return ''

def prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string."""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

def parse_dix_file(file_path: str) -> Tuple[ET.Element, List[ET.Element], Set[str]]:
    """
    Parse a .dix file and extract entries.
    
    Returns:
        - Root element
        - List of entry elements
        - Set of Ido words in entries
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    # Find the main section with entries
    section = root.find('.//section[@id="main"]')
    if section is None:
        section = root.find('.//section')
    
    entries = []
    words = set()
    
    if section is not None:
        for entry in section.findall('e'):
            entries.append(entry)
            word = extract_word_from_entry(entry)
            if word:
                words.add(word)
    
    return root, entries, words

def merge_dictionaries(
    existing_file: str,
    new_file: str,
    output_file: str,
    prefer_existing: bool = True,
    sort_entries: bool = True
) -> dict:
    """
    Merge new dictionary entries into existing dictionary.
    
    Args:
        existing_file: Path to existing .dix file
        new_file: Path to new .dix file with entries to add
        output_file: Path to write merged .dix file
        prefer_existing: If True, keep existing entry on conflicts
        sort_entries: If True, sort entries alphabetically
    
    Returns:
        Statistics dict with merge info
    """
    print(f"📖 Reading existing dictionary: {existing_file}")
    existing_root, existing_entries, existing_words = parse_dix_file(existing_file)
    
    print(f"📖 Reading new dictionary: {new_file}")
    new_root, new_entries, new_words = parse_dix_file(new_file)
    
    # Find the main section in existing file
    section = existing_root.find('.//section[@id="main"]')
    if section is None:
        section = existing_root.find('.//section')
    
    if section is None:
        raise ValueError("Could not find main section in existing dictionary")
    
    # Track statistics
    stats = {
        'existing_entries': len(existing_entries),
        'new_entries': len(new_entries),
        'duplicates': 0,
        'added': 0,
        'conflicts': 0
    }
    
    # Add new entries that don't exist
    added_entries = []
    for entry in new_entries:
        word = extract_word_from_entry(entry)
        
        if word in existing_words:
            stats['duplicates'] += 1
            if not prefer_existing:
                # Remove old entry and add new one
                for old_entry in section.findall('e'):
                    if extract_word_from_entry(old_entry) == word:
                        section.remove(old_entry)
                        break
                section.append(entry)
                stats['conflicts'] += 1
        else:
            section.append(entry)
            added_entries.append(word)
            stats['added'] += 1
    
    # Sort entries alphabetically by Ido word
    if sort_entries:
        print("🔤 Sorting entries alphabetically...")
        entries_with_words = []
        for entry in section.findall('e'):
            word = extract_word_from_entry(entry)
            entries_with_words.append((word.lower(), entry))
        
        entries_with_words.sort(key=lambda x: x[0])
        
        # Clear section and re-add sorted entries
        for entry in section.findall('e'):
            section.remove(entry)
        
        for _, entry in entries_with_words:
            section.append(entry)
    
    stats['final_entries'] = len(section.findall('e'))
    
    # Write output
    print(f"💾 Writing merged dictionary: {output_file}")
    xml_string = prettify_xml(existing_root)
    
    # Add XML declaration
    xml_string = '<?xml version="1.0" encoding="UTF-8"?>\n' + '\n'.join(xml_string.split('\n')[1:])
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(xml_string)
    
    return stats

def main():
    parser = argparse.ArgumentParser(
        description='Merge BERT dictionary entries into existing Apertium dictionary'
    )
    parser.add_argument(
        '--existing',
        required=True,
        help='Existing Apertium .dix file'
    )
    parser.add_argument(
        '--new',
        required=True,
        help='New .dix file with entries to add'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output .dix file (can be same as existing)'
    )
    parser.add_argument(
        '--prefer-existing',
        action='store_true',
        default=True,
        help='On conflicts, keep existing entry (default: True)'
    )
    parser.add_argument(
        '--no-sort',
        action='store_true',
        help='Do not sort entries alphabetically'
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("APERTIUM DICTIONARY MERGER")
    print("="*60)
    print()
    
    # Merge dictionaries
    stats = merge_dictionaries(
        args.existing,
        args.new,
        args.output,
        prefer_existing=args.prefer_existing,
        sort_entries=not args.no_sort
    )
    
    # Display statistics
    print()
    print("="*60)
    print("MERGE STATISTICS")
    print("="*60)
    print(f"Existing entries:    {stats['existing_entries']:>6}")
    print(f"New entries:         {stats['new_entries']:>6}")
    print(f"Duplicates skipped:  {stats['duplicates']:>6}")
    print(f"Added:               {stats['added']:>6}")
    print(f"Conflicts resolved:  {stats['conflicts']:>6}")
    print(f"Final total:         {stats['final_entries']:>6}")
    print("="*60)
    print()
    print(f"✅ Dictionary merged successfully!")
    print(f"   Output: {args.output}")
    print()
    print(f"Coverage increase: +{stats['added']} entries")
    print(f"  ({100 * stats['added'] / stats['existing_entries']:.1f}% growth)")

if __name__ == '__main__':
    main()

