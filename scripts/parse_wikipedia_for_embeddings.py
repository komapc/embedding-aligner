#!/usr/bin/env python3
"""
Parse Wikipedia JSON dumps to extract clean text for embedding training.
Focuses on extracting readable content while ignoring:
- Categories
- References
- Templates (cosmetic)
- Navigation elements
- Metadata

Handles MediaWiki syntax like [[links]] properly.
"""

import json
import re
import time
from pathlib import Path
from typing import List, Dict, Any
import argparse

# Pre-compile regex patterns for performance
# Remove category links
CATEGORY_RE = re.compile(r'\[\[(?:Category|Kategorio|Kategorii):[^\]]+\]\]', re.IGNORECASE)

# Remove file/image links and captions (completely ignore all image-related content)
# This matches [[File:...]] or [[Image:...]] with any content including nested brackets
FILE_RE = re.compile(r'\[\[(?:File|Image|Dosiero|Imajo|Arkivo|Fichier):[^\]]*(?:\[\[[^\]]*\]\][^\]]*)*\]\]', re.IGNORECASE)

# Handle wiki links: [[target|display]] -> display, [[target]] -> target
LINK_WITH_PIPE_RE = re.compile(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]')

# Remove templates (most are cosmetic/navigation)
# Keep simple ones, remove complex nested ones
TEMPLATE_RE = re.compile(r'\{\{[^}]+\}\}')

# Remove HTML comments
COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)

# Remove HTML tags
HTML_TAG_RE = re.compile(r'<[^>]+>')

# Remove reference tags and content
REF_RE = re.compile(r'<ref[^>]*>.*?</ref>', re.DOTALL | re.IGNORECASE)
REF_SELF_CLOSING_RE = re.compile(r'<ref[^>]*/>', re.IGNORECASE)

# Remove section headers (== Header ==)
HEADER_RE = re.compile(r'^=+\s*.*?\s*=+\s*$', re.MULTILINE)

# Normalize whitespace
WHITESPACE_RE = re.compile(r'\s+')

# Detect reference sections to skip
REFERENCE_SECTION_RE = re.compile(
    r'^=+\s*(?:References|Referaji|Referensi|Bibliografio|Ligili|Videz anke)\s*=+',
    re.IGNORECASE | re.MULTILINE
)

# Questions to collect about uncertain templates
QUESTIONS = []

def clean_wikitext(text: str, collect_questions: bool = False) -> str:
    """Clean MediaWiki markup to extract readable text."""
    if not text:
        return ""
    
    # Remove HTML comments first
    text = COMMENT_RE.sub('', text)
    
    # Remove references
    text = REF_RE.sub('', text)
    text = REF_SELF_CLOSING_RE.sub('', text)
    
    # Remove categories
    text = CATEGORY_RE.sub('', text)
    
    # Remove file/image links and all captions (completely ignore)
    text = FILE_RE.sub('', text)
    
    # Also remove any remaining image-related templates
    text = re.sub(r'\{\{(?:Image|File|Thumb|Thumbnail)[^}]*\}\}', '', text, flags=re.IGNORECASE)
    
    # Handle wiki links: keep display text
    text = LINK_WITH_PIPE_RE.sub(r'\1', text)
    
    # Remove section headers
    text = HEADER_RE.sub('', text)
    
    # Handle templates - collect questions about uncertain ones
    if collect_questions:
        templates = TEMPLATE_RE.findall(text)
        for tpl in templates[:10]:  # Limit to avoid spam
            # Check if it's a complex template we're unsure about
            if '|' in tpl and len(tpl) > 20:
                if tpl not in QUESTIONS:
                    QUESTIONS.append(tpl)
    
    # Remove templates
    text = TEMPLATE_RE.sub('', text)
    
    # Remove HTML tags
    text = HTML_TAG_RE.sub('', text)
    
    # Remove apostrophes used for bold/italic ('''bold''' or ''italic'')
    text = text.replace("'''", "").replace("''", "")
    
    # Normalize whitespace
    text = WHITESPACE_RE.sub(' ', text)
    
    return text.strip()

def extract_main_content(text: str) -> str:
    """Extract main content, stopping at reference sections."""
    if not text:
        return ""
    
    # Find reference section
    match = REFERENCE_SECTION_RE.search(text)
    if match:
        # Take only content before references
        text = text[:match.start()]
    
    return text

def process_wikipedia_json(
    input_file: Path,
    output_file: Path,
    limit: int = None,
    collect_questions: bool = False
) -> Dict[str, Any]:
    """Process Wikipedia JSON and extract clean text."""
    
    print(f"Processing {input_file}...")
    start_time = time.time()
    
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    entries = data.get('entries', [])
    total_entries = len(entries)
    
    if limit:
        entries = entries[:limit]
        print(f"Processing first {limit} of {total_entries} entries")
    else:
        print(f"Processing all {total_entries} entries")
    
    sentences = []
    processed_count = 0
    skipped_count = 0
    
    for entry in entries:
        lemma = entry.get('lemma', '')
        classification = entry.get('classification', '')
        
        # Skip if it's just a proper noun without content
        # (these are usually just titles from langlinks)
        if not lemma:
            skipped_count += 1
            continue
        
        # For now, just collect the lemma as a sentence
        # In real Wikipedia dumps, we'd have article text
        # This JSON appears to be from langlinks, not full articles
        
        # Create a simple sentence from the lemma
        # (In full Wikipedia XML, we'd extract article content)
        clean_lemma = clean_wikitext(lemma, collect_questions)
        
        if clean_lemma and len(clean_lemma) > 1:
            sentences.append(clean_lemma.lower())
            processed_count += 1
        else:
            skipped_count += 1
    
    # Write output
    with open(output_file, 'w', encoding='utf-8') as f:
        for sentence in sentences:
            f.write(sentence + '\n')
    
    elapsed = time.time() - start_time
    
    stats = {
        'input_file': str(input_file),
        'output_file': str(output_file),
        'total_entries': total_entries,
        'processed': processed_count,
        'skipped': skipped_count,
        'output_lines': len(sentences),
        'elapsed_seconds': elapsed,
        'entries_per_second': processed_count / elapsed if elapsed > 0 else 0
    }
    
    return stats

def main():
    parser = argparse.ArgumentParser(
        description='Parse Wikipedia JSON for embedding training'
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input JSON file (e.g., source_io_wikipedia.json)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        required=True,
        help='Output text file for embeddings'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=500,
        help='Limit number of articles to process (default: 500)'
    )
    parser.add_argument(
        '--collect-questions',
        action='store_true',
        help='Collect questions about uncertain templates'
    )
    
    args = parser.parse_args()
    
    # Process
    stats = process_wikipedia_json(
        args.input,
        args.output,
        limit=args.limit,
        collect_questions=args.collect_questions
    )
    
    # Print statistics
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(f"Input:           {stats['input_file']}")
    print(f"Output:          {stats['output_file']}")
    print(f"Total entries:   {stats['total_entries']}")
    print(f"Processed:       {stats['processed']}")
    print(f"Skipped:         {stats['skipped']}")
    print(f"Output lines:    {stats['output_lines']}")
    print(f"Time:            {stats['elapsed_seconds']:.2f} seconds")
    print(f"Speed:           {stats['entries_per_second']:.1f} entries/sec")
    print("="*60)
    
    # Estimate full processing time
    if args.limit and stats['total_entries'] > args.limit:
        estimated_full_time = (stats['total_entries'] / stats['entries_per_second'])
        print(f"\nEstimated time for all {stats['total_entries']} entries:")
        print(f"  {estimated_full_time:.1f} seconds ({estimated_full_time/60:.1f} minutes)")
    
    # Print questions about templates
    if args.collect_questions and QUESTIONS:
        print("\n" + "="*60)
        print("QUESTIONS ABOUT TEMPLATES")
        print("="*60)
        print("Found these complex templates. Should they be kept or removed?")
        for i, tpl in enumerate(QUESTIONS[:20], 1):
            print(f"\n{i}. {tpl[:100]}...")
    
    print("\n✓ Done!")

if __name__ == '__main__':
    main()
