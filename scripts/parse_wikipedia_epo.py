#!/usr/bin/env python3
"""
Parse Esperanto Wikipedia XML dump for embedding training.

Final production parser based on test results and user approval.
Removes all templates aggressively for clean corpus.

Based on Ido parser with Esperanto-specific adaptations.
"""

import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Tuple, List
import argparse
import bz2
import gzip

# Pre-compile regex patterns for performance
WHITESPACE_RE = re.compile(r'\s+')
MULTIPLE_NEWLINES_RE = re.compile(r'\n\n+')
HEADER_RE = re.compile(r'^=+\s*.*?\s*=+\s*$', re.MULTILINE)

# Esperanto-specific section headers to skip (references, external links, etc.)
SKIP_SECTIONS_RE = re.compile(
    r'^=+\s*(?:'
    r'References?|Referencoj|Fontoj|Citaĵoj|'
    r'External links?|Eksteraj ligiloj|'
    r'See also|Vidu ankaŭ|Vidu ankaux|'
    r'Notes?|Notoj|Rimarkoj|'
    r'Bibliography|Bibliografio|Literaturo|'
    r'Further reading'
    r')\s*=+',
    re.IGNORECASE | re.MULTILINE
)

def open_compressed(filepath: Path):
    """Open file, handling .bz2 and .gz compression."""
    if filepath.suffix == '.bz2':
        return bz2.open(filepath, 'rt', encoding='utf-8')
    elif filepath.suffix == '.gz':
        return gzip.open(filepath, 'rt', encoding='utf-8')
    return open(filepath, 'r', encoding='utf-8')

def iter_wikipedia_pages(xml_path: Path) -> Iterator[Tuple[str, str, str]]:
    """Iterate over Wikipedia XML dump, yielding (title, namespace, text) tuples."""
    with open_compressed(xml_path) as f:
        context = ET.iterparse(f, events=('end',))
        
        for event, elem in context:
            if not isinstance(elem.tag, str) or not elem.tag.endswith('page'):
                continue
            
            title = ns = text = ''
            for child in elem:
                if child.tag.endswith('title'):
                    title = child.text or ''
                elif child.tag.endswith('ns'):
                    ns = child.text or '0'
                elif child.tag.endswith('revision'):
                    for subchild in child:
                        if subchild.tag.endswith('text'):
                            text = subchild.text or ''
            
            yield title, ns, text
            elem.clear()

def is_valid_page(title: str, namespace: str) -> bool:
    """Check if page should be processed."""
    if namespace != '0' or not title or len(title) < 2:
        return False
    
    # Skip pages with these prefixes (both English and Esperanto forms)
    skip_prefixes = (
        'MediaWiki:', 'Help:', 'Helpo:', 
        'Category:', 'Kategorio:', 
        'Template:', 'Ŝablono:', 
        'User:', 'Uzanto:', 
        'Talk:', 'Diskuto:',
        'File:', 'Image:', 'Dosiero:', 'Bildo:', 
        'Special:', 'Speciala:',
        'Wikipedia:', 'Vikipedio:', 
        'Wiktionary:', 'Vikivortaro:'
    )
    return not title.startswith(skip_prefixes)

def extract_main_content(text: str) -> str:
    """Extract main article content, stopping at reference sections."""
    if not text:
        return ""
    
    # Find first skip section (Esperanto patterns)
    match = SKIP_SECTIONS_RE.search(text)
    if match:
        text = text[:match.start()]
    
    return text

def clean_wikitext(text: str) -> str:
    """Clean MediaWiki markup to extract readable text."""
    if not text:
        return ""
    
    # Extract main content first (before references)
    text = extract_main_content(text)
    
    # Remove HTML comments
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)
    
    # Remove references
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<ref[^>]*/>', '', text, flags=re.IGNORECASE)
    
    # Remove categories (Esperanto: Kategorio)
    text = re.sub(r'\[\[(?:Category|Kategorio):[^\]]+\]\]', '', text, flags=re.IGNORECASE)
    
    # Remove file/image links (Esperanto: Dosiero, Bildo)
    text = re.sub(r'\[\[(?:File|Image|Dosiero|Bildo|Arkivo):[^\]]*(?:\[\[[^\]]*\]\][^\]]*)*\]\]', '', text, flags=re.IGNORECASE)
    
    # Remove IPA pronunciation patterns
    text = re.sub(r'\(ifa:?\s*[^\)]+\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(ipa:?\s*[^\)]+\)', '', text, flags=re.IGNORECASE)
    
    # Extract numbers from {{formatnum:NUMBER}} templates (keep the number)
    text = re.sub(r'\{\{formatnum:([^}]+)\}\}', r'\1', text, flags=re.IGNORECASE)
    
    # Remove source code blocks completely
    text = re.sub(r'<source[^>]*>.*?</source>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<syntaxhighlight[^>]*>.*?</syntaxhighlight>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Replace math tags with "formulo" (Esperanto for formula)
    text = re.sub(r'<math[^>]*>.*?</math>', 'formulo', text, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove all templates (iterative for nested ones)
    # AGGRESSIVE: Remove ALL {{...}} templates
    for _ in range(10):
        old = text
        text = re.sub(r'\{\{[^{}]*\}\}', '', text)
        if text == old:
            break
    
    # Handle wiki links: [[target|display]] -> display, [[target]] -> target
    text = re.sub(r'\[\[https?://[^\]]+\s+([^\]]+)\]\]', r'\1', text)  # URL links
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', text)  # Normal links
    text = text.replace('[[', '').replace(']]', '')  # Cleanup remaining brackets
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove section headers
    text = HEADER_RE.sub('\n', text)
    
    # Remove bold/italic markup
    text = text.replace("'''", "").replace("''", "")
    
    # Remove table markup
    text = re.sub(r'\{\|.*?\|\}', '', text, flags=re.DOTALL)
    text = re.sub(r'^\|.*?$', '', text, flags=re.MULTILINE)
    
    # Remove bullet points from lists
    text = re.sub(r'^\*\s+', '', text, flags=re.MULTILINE)
    
    # Remove numbered list prefixes
    text = re.sub(r'^\d{3,4}\)\s*', '', text, flags=re.MULTILINE)
    
    # Remove Unicode directional marks
    text = re.sub(r'[\u200E\u200F\u202A-\u202E]', '', text)
    
    # Normalize whitespace
    text = WHITESPACE_RE.sub(' ', text)
    text = MULTIPLE_NEWLINES_RE.sub('\n', text)
    
    return text.strip()

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences with aggressive cleaning."""
    if not text:
        return []
    
    lines = text.split('\n')
    sentences = []
    
    for line in lines:
        line = line.strip()
        
        # Skip very short lines
        if len(line) < 10:
            continue
        
        # Skip horizontal rules
        if re.match(r'^-{4,}$', line):
            continue
        
        # Skip lines starting with special chars (table remnants, lists)
        if line.startswith(('*', '|', '----', '#')):
            continue
        
        # Skip lines with file/image references or captions
        if any(marker in line.lower() for marker in ['thumb|', 'dosiero:', 'bildo:', 'arkivo:', 'file:', ', da ', '|thumb', '|right', '|left', '|center']):
            continue
        
        # Skip lines starting with pipe (table remnants)
        if line.startswith('|'):
            continue
        
        # Remove URL fragments
        if 'http://' in line or 'https://' in line or line.startswith('[http'):
            continue
        
        # Skip lines that are just "formulo" (from math tags)
        if line.strip().lower() == 'formulo':
            continue
        
        # Remove numbered list prefixes (1918), 1650), etc.)
        line = re.sub(r'^\d{3,4}\)\s*', '', line)
        
        # Remove incomplete parenthetical markers at end: (n, (m, (f, (d
        line = re.sub(r'\s*\([nmfd]\s*$', '', line)
        
        # Normalize dashes (en-dash → hyphen)
        line = line.replace('–', '-').replace('—', '-')
        
        # Remove excessive whitespace
        line = ' '.join(line.split())
        
        # Final length check after cleaning
        if len(line) < 10:
            continue
        
        # Smart sentence splitting that respects parentheses and abbreviations
        parts = []
        current = []
        paren_depth = 0
        i = 0
        
        while i < len(line):
            char = line[i]
            current.append(char)
            
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '.' and paren_depth == 0:
                # Check if this is an abbreviation
                if i > 0 and i < len(line) - 1:
                    # Look back for single letter + period (abbreviations)
                    if i >= 1 and line[i-1] in 'nmfdNMFD' and (i == 1 or not line[i-2].isalpha()):
                        # This is an abbreviation, don't split
                        i += 1
                        continue
                    # Check if followed by space and capital letter (real sentence end)
                    if i < len(line) - 2 and line[i+1] == ' ' and line[i+2].isupper():
                        # Real sentence boundary
                        part = ''.join(current).strip()
                        if len(part) >= 10:
                            parts.append(part)
                        current = []
                        i += 1
                        continue
            
            i += 1
        
        # Add remaining text
        if current:
            part = ''.join(current).strip()
            if len(part) >= 10:
                parts.append(part)
        
        # If no smart splitting happened, fall back to simple split
        if not parts:
            parts = [p.strip() for p in line.split('. ') if len(p.strip()) >= 10]
        
        # Clean up any trailing periods
        parts = [p.rstrip('. ') for p in parts if p.strip()]
        
        sentences.extend(parts)
    
    return sentences

def process_wikipedia_xml(
    input_file: Path,
    output_file: Path,
    limit: int = None
) -> dict:
    """Process Wikipedia XML dump and extract clean text."""
    
    print(f"Processing {input_file}...")
    if limit:
        print(f"Limit: {limit} articles")
    else:
        print(f"Processing ALL articles (this will take ~40 minutes)")
    
    start_time = time.time()
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    processed_count = 0
    skipped_count = 0
    total_sentences = 0
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for title, namespace, text in iter_wikipedia_pages(input_file):
            if limit and processed_count >= limit:
                break
            
            if not is_valid_page(title, namespace):
                skipped_count += 1
                continue
            
            # Clean the wikitext
            clean_text = clean_wikitext(text)
            
            if not clean_text or len(clean_text) < 50:
                skipped_count += 1
                continue
            
            # Split into sentences
            sentences = split_into_sentences(clean_text)
            
            if not sentences:
                skipped_count += 1
                continue
            
            # Write sentences (lowercase for embeddings)
            for sentence in sentences:
                out_f.write(sentence.lower() + '\n')
                total_sentences += 1
            
            processed_count += 1
            
            # Progress indicator
            if processed_count % 1000 == 0:
                elapsed = time.time() - start_time
                rate = processed_count / elapsed if elapsed > 0 else 0
                eta_seconds = (limit - processed_count) / rate if limit and rate > 0 else 0
                eta_minutes = eta_seconds / 60
                print(f"  Processed {processed_count:,} articles "
                      f"({total_sentences:,} sentences, {rate:.1f} articles/sec, "
                      f"ETA: {eta_minutes:.1f} min)")
    
    elapsed = time.time() - start_time
    
    stats = {
        'input_file': str(input_file),
        'output_file': str(output_file),
        'processed_articles': processed_count,
        'skipped_articles': skipped_count,
        'total_sentences': total_sentences,
        'elapsed_seconds': elapsed,
        'articles_per_second': processed_count / elapsed if elapsed > 0 else 0
    }
    
    return stats

def main():
    parser = argparse.ArgumentParser(
        description='Parse Esperanto Wikipedia XML dump for embedding training'
    )
    parser.add_argument(
        '--input',
        type=Path,
        required=True,
        help='Input XML file (can be .bz2 or .gz compressed)'
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
        help='Limit number of articles to process (for testing)'
    )
    
    args = parser.parse_args()
    
    # Process
    stats = process_wikipedia_xml(
        args.input,
        args.output,
        limit=args.limit
    )
    
    # Print statistics
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(f"Input:           {stats['input_file']}")
    print(f"Output:          {stats['output_file']}")
    print(f"Articles:        {stats['processed_articles']:,}")
    print(f"Skipped:         {stats['skipped_articles']:,}")
    print(f"Sentences:       {stats['total_sentences']:,}")
    print(f"Time:            {stats['elapsed_seconds']:.2f} seconds")
    print(f"                 ({stats['elapsed_seconds']/60:.2f} minutes)")
    print(f"Speed:           {stats['articles_per_second']:.1f} articles/sec")
    
    # Word count
    word_count = 0
    with open(args.output, 'r', encoding='utf-8') as f:
        for line in f:
            word_count += len(line.split())
    
    print(f"Total words:     {word_count:,}")
    print(f"Avg words/sent:  {word_count/stats['total_sentences']:.1f}")
    print("="*60)
    print("\n✓ Done!")

if __name__ == '__main__':
    main()

