#!/usr/bin/env python3
"""
Simplified Wikipedia XML parser for embedding training.
Extracts clean text from Wikipedia dumps with minimal complexity.
"""

import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator, Tuple, List
import argparse
import bz2
import gzip

# Pre-compile common patterns
WHITESPACE_RE = re.compile(r'\s+')
HEADER_RE = re.compile(r'^=+\s*.*?\s*=+\s*$', re.MULTILINE)

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
    
    skip_prefixes = ('MediaWiki:', 'Help:', 'Category:', 'Template:', 'User:', 
                     'Talk:', 'File:', 'Image:', 'Special:', 'Wikipedia:', 
                     'Wiktionary:', 'Wikivortaro:')
    return not title.startswith(skip_prefixes)

def clean_wikitext(text: str) -> str:
    """Clean MediaWiki markup to extract readable text."""
    if not text:
        return ""
    
    # Stop at reference sections
    ref_match = re.search(r'^=+\s*(?:References?|Referaji|External links?|Ligili|Videz anke)\s*=+', 
                          text, re.IGNORECASE | re.MULTILINE)
    if ref_match:
        text = text[:ref_match.start()]
    
    # Remove in order of importance
    text = re.sub(r'<!--.*?-->', '', text, flags=re.DOTALL)  # HTML comments
    text = re.sub(r'<ref[^>]*>.*?</ref>', '', text, flags=re.DOTALL | re.IGNORECASE)  # References
    text = re.sub(r'<ref[^>]*/>', '', text, flags=re.IGNORECASE)  # Self-closing refs
    text = re.sub(r'<source[^>]*>.*?</source>', '', text, flags=re.DOTALL | re.IGNORECASE)  # Source code
    text = re.sub(r'<math[^>]*>.*?</math>', 'formula', text, flags=re.DOTALL | re.IGNORECASE)  # Math
    text = re.sub(r'\[\[(?:Category|Kategorio|File|Image|Dosiero|Imajo|Arkivo):[^\]]+\]\]', '', text, flags=re.IGNORECASE)  # Categories/files
    text = re.sub(r'\(ifa:?\s*[^\)]+\)', '', text, flags=re.IGNORECASE)  # IPA pronunciations
    text = re.sub(r'\{\{formatnum:([^}]+)\}\}', r'\1', text, flags=re.IGNORECASE)  # Extract numbers
    
    # Remove all templates (iterative for nested ones)
    for _ in range(10):
        old = text
        text = re.sub(r'\{\{[^{}]*\}\}', '', text)
        if text == old:
            break
    
    # Handle wiki links: [[target|display]] -> display, [[target]] -> target
    text = re.sub(r'\[\[https?://[^\]]+\s+([^\]]+)\]\]', r'\1', text)  # URL links
    text = re.sub(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]', r'\1', text)  # Normal links
    text = text.replace('[[', '').replace(']]', '')  # Cleanup remaining brackets
    
    # Remove HTML and formatting
    text = re.sub(r'<[^>]+>', '', text)  # HTML tags
    text = HEADER_RE.sub('\n', text)  # Section headers
    text = text.replace("'''", "").replace("''", "")  # Bold/italic
    text = re.sub(r'\{\|.*?\|\}', '', text, flags=re.DOTALL)  # Tables
    text = re.sub(r'^\|.*?$', '', text, flags=re.MULTILINE)  # Table rows
    text = re.sub(r'^\*\s+', '', text, flags=re.MULTILINE)  # Bullet points
    text = re.sub(r'^\d{3,4}\)\s*', '', text, flags=re.MULTILINE)  # Numbered lists
    text = re.sub(r'[\u200E\u200F\u202A-\u202E]', '', text)  # Unicode marks
    
    # Normalize whitespace
    text = WHITESPACE_RE.sub(' ', text)
    text = re.sub(r'\n\n+', '\n', text)
    
    return text.strip()

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences with filtering."""
    if not text:
        return []
    
    sentences = []
    for line in text.split('\n'):
        line = line.strip()
        
        # Skip short, empty, or noisy lines
        if len(line) < 10:
            continue
        if line.startswith(('*', '|', '----')):
            continue
        if line.lower() == 'formula':
            continue
        if any(x in line.lower() for x in ['thumb|', 'arkivo:', 'file:', ', da ', 'http://', 'https://']):
            continue
        
        # Clean up
        line = re.sub(r'^\d{3,4}\)\s*', '', line)  # Remove year prefixes
        line = re.sub(r'\s*\([nmfd]\s*$', '', line)  # Remove incomplete markers
        line = line.replace('–', '-').replace('—', '-')  # Normalize dashes
        line = ' '.join(line.split())  # Normalize whitespace
        
        if len(line) < 10:
            continue
        
        # Simple sentence split (period + space + capital letter)
        # Don't split on abbreviations like "n." or inside parentheses
        parts = []
        current = []
        paren_depth = 0
        
        for i, char in enumerate(line):
            current.append(char)
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '.' and paren_depth == 0:
                # Check if abbreviation or real sentence end
                if i > 0 and i < len(line) - 2:
                    if line[i-1] in 'nmfdNMFD' and (i == 1 or not line[i-2].isalpha()):
                        continue  # Abbreviation
                    if line[i+1] == ' ' and line[i+2].isupper():
                        # Real sentence boundary
                        part = ''.join(current).strip()
                        if len(part) >= 10:
                            parts.append(part)
                        current = []
        
        # Add remaining
        if current:
            part = ''.join(current).strip()
            if len(part) >= 10:
                parts.append(part)
        
        # Fallback to simple split if no smart split
        if not parts:
            parts = [p.strip() for p in line.split('. ') if len(p.strip()) >= 10]
        
        sentences.extend(parts)
    
    return sentences

def process_wikipedia_xml(input_file: Path, output_file: Path, limit: int = None) -> dict:
    """Process Wikipedia XML dump and extract clean text."""
    print(f"Processing {input_file}...")
    start_time = time.time()
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    processed = skipped = total_sentences = 0
    
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for title, namespace, text in iter_wikipedia_pages(input_file):
            if limit and processed >= limit:
                break
            
            if not is_valid_page(title, namespace):
                skipped += 1
                continue
            
            clean_text = clean_wikitext(text)
            if not clean_text or len(clean_text) < 50:
                skipped += 1
                continue
            
            sentences = split_into_sentences(clean_text)
            if not sentences:
                skipped += 1
                continue
            
            for sentence in sentences:
                out_f.write(sentence.lower() + '\n')
                total_sentences += 1
            
            processed += 1
            if processed % 100 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                print(f"  Processed {processed} articles ({total_sentences} sentences, {rate:.1f} articles/sec)")
    
    elapsed = time.time() - start_time
    return {
        'processed_articles': processed,
        'skipped_articles': skipped,
        'total_sentences': total_sentences,
        'elapsed_seconds': elapsed,
        'articles_per_second': processed / elapsed if elapsed > 0 else 0
    }

def main():
    parser = argparse.ArgumentParser(description='Parse Wikipedia XML dump for embedding training')
    parser.add_argument('--input', type=Path, required=True, help='Input XML file (.bz2, .gz, or plain)')
    parser.add_argument('--output', type=Path, required=True, help='Output text file')
    parser.add_argument('--limit', type=int, help='Limit articles (for testing)')
    args = parser.parse_args()
    
    stats = process_wikipedia_xml(args.input, args.output, args.limit)
    
    print("\n" + "="*60)
    print("PROCESSING COMPLETE")
    print("="*60)
    print(f"Articles:  {stats['processed_articles']}")
    print(f"Skipped:   {stats['skipped_articles']}")
    print(f"Sentences: {stats['total_sentences']}")
    print(f"Time:      {stats['elapsed_seconds']:.2f} seconds")
    print(f"Speed:     {stats['articles_per_second']:.1f} articles/sec")
    print("="*60)
    print("\n✓ Done!")

if __name__ == '__main__':
    main()
