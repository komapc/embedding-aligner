#!/usr/bin/env python3
"""
Parse Wikipedia XML dumps to extract clean text for embedding training.

Handles full Wikipedia XML dumps with article content.
Ignores:
- Categories, templates, references
- Navigation elements
- Metadata and markup

Properly handles MediaWiki syntax like [[links]].
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
CATEGORY_RE = re.compile(r'\[\[(?:Category|Kategorio|Kategorii):[^\]]+\]\]', re.IGNORECASE)
FILE_RE = re.compile(r'\[\[(?:File|Image|Dosiero|Imajo|Arkivo):[^\]]+\]\]', re.IGNORECASE)
LINK_WITH_PIPE_RE = re.compile(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]')
COMMENT_RE = re.compile(r'<!--.*?-->', re.DOTALL)
HTML_TAG_RE = re.compile(r'<[^>]+>')
REF_RE = re.compile(r'<ref[^>]*>.*?</ref>', re.DOTALL | re.IGNORECASE)
REF_SELF_CLOSING_RE = re.compile(r'<ref[^>]*/>', re.IGNORECASE)
HEADER_RE = re.compile(r'^=+\s*.*?\s*=+\s*$', re.MULTILINE)
WHITESPACE_RE = re.compile(r'\s+')
MULTIPLE_NEWLINES_RE = re.compile(r'\n\n+')

# Templates to explicitly ignore (remove completely)
# User specified: Biografio, #ifexist, geographic lists, infoboxes, name templates, tabelo di sucedo
IGNORE_TEMPLATES_RE = re.compile(
    r'\{\{(?:'
    r'Biografio|biografio|#ifexist|'
    r'\d+ maxim grand urbi|\d+ maxim populoza|'  # Geographic lists
    r'Chef-urbi|Chefministri|provinci di|regioni di|stati di|stati en|'  # Geographic/admin
    r'Aeroportuo|Auto|koreanname|vi-nom|'  # Infoboxes and name templates
    r'tabelo di sucedo|'  # Table of succession
    r'formatnum|#expr|CURRENTTIME|'  # Number/date formatting
    r'\d+ma yarcento|\d+ma yarmilo|'  # Centuries/millennia
    r'Agosto|Aprilo|Julio|Junio|Marto|Mayo|Oktobro|Septembro|'  # Months
    r'DEFAULTSORT|CompactTOC|Bots|indexo|portalaro|portalo|'  # Navigation/metadata
    r'nekompleta|tradukenda|stub|revizo|Bezonas tradukuro|'  # Content markers
    r'videz anke|wikivortaro|'  # See also links
    r'nowrap|small|center|sidebar|'  # Formatting
    r'party color|vgrelease|spoiler'  # Misc cosmetic
    r')[^}]*\}\}',
    re.IGNORECASE | re.DOTALL
)

# Pattern to extract content from {{liste horizontale|...}}
LISTE_HORIZONTALE_RE = re.compile(r'\{\{liste horizontale\|([^}]+)\}\}', re.IGNORECASE)

# Pattern to find all templates for suspicious structure detection
ALL_TEMPLATES_RE = re.compile(r'\{\{([^}|]+)(?:\|[^}]*)?\}\}', re.DOTALL)

# Section headers to skip (references, external links, etc.)
SKIP_SECTIONS_RE = re.compile(
    r'^=+\s*(?:References?|Referaji|Referensi|Bibliografio|'
    r'External links?|Ligili|Videz anke|See also|'
    r'Notes?|Noti|Further reading|Literatura)'
    r'\s*=+',
    re.IGNORECASE | re.MULTILINE
)

# Collect questions about templates
TEMPLATE_QUESTIONS = set()

def open_compressed(filepath: Path):
    """Open file, handling .bz2 and .gz compression."""
    if filepath.suffix == '.bz2':
        return bz2.open(filepath, 'rt', encoding='utf-8')
    elif filepath.suffix == '.gz':
        return gzip.open(filepath, 'rt', encoding='utf-8')
    else:
        return open(filepath, 'r', encoding='utf-8')

def iter_wikipedia_pages(xml_path: Path) -> Iterator[Tuple[str, str, str]]:
    """
    Iterate over Wikipedia XML dump, yielding (title, namespace, text) tuples.
    """
    with open_compressed(xml_path) as f:
        context = ET.iterparse(f, events=('end',))
        
        for event, elem in context:
            if not isinstance(elem.tag, str):
                continue
            
            # Match tags regardless of namespace
            if elem.tag.endswith('page'):
                title_elem = None
                ns_elem = None
                text_elem = None
                
                for child in elem:
                    if child.tag.endswith('title'):
                        title_elem = child
                    elif child.tag.endswith('ns'):
                        ns_elem = child
                    elif child.tag.endswith('revision'):
                        for subchild in child:
                            if subchild.tag.endswith('text'):
                                text_elem = subchild
                
                title = title_elem.text if title_elem is not None else ''
                ns = ns_elem.text if ns_elem is not None else '0'
                text = text_elem.text if text_elem is not None else ''
                
                yield title or '', ns or '0', text or ''
                
                # Clear element to save memory
                elem.clear()

def is_valid_page(title: str, namespace: str) -> bool:
    """Check if page should be processed."""
    # Only process main namespace (0)
    if namespace != '0':
        return False
    
    # Skip special pages
    skip_prefixes = [
        'MediaWiki:', 'Help:', 'Category:', 'Template:',
        'User:', 'Talk:', 'File:', 'Image:', 'Special:',
        'Wikipedia:', 'Wiktionary:', 'Wikivortaro:'
    ]
    
    for prefix in skip_prefixes:
        if title.startswith(prefix):
            return False
    
    return bool(title and len(title) > 1)

def extract_main_content(text: str) -> str:
    """Extract main article content, stopping at reference sections."""
    if not text:
        return ""
    
    # Find first skip section
    match = SKIP_SECTIONS_RE.search(text)
    if match:
        text = text[:match.start()]
    
    return text

def clean_wikitext(text: str, collect_questions: bool = False) -> str:
    """Clean MediaWiki markup to extract readable text."""
    if not text:
        return ""
    
    # Extract main content first (before references)
    text = extract_main_content(text)
    
    # Remove HTML comments
    text = COMMENT_RE.sub('', text)
    
    # Remove references
    text = REF_RE.sub('', text)
    text = REF_SELF_CLOSING_RE.sub('', text)
    
    # Remove categories
    text = CATEGORY_RE.sub('', text)
    
    # Remove file/image links (all formats)
    text = FILE_RE.sub('', text)
    
    # Remove IPA pronunciation patterns (do this early, before other cleaning)
    # Matches: (ifa: ...), (ifa ...), and similar patterns
    text = re.sub(r'\(ifa:?\s*[^\)]+\)', '', text, flags=re.IGNORECASE)
    
    # Extract numbers from {{formatnum:NUMBER}} templates (keep the number)
    text = re.sub(r'\{\{formatnum:([^}]+)\}\}', r'\1', text, flags=re.IGNORECASE)
    
    # Remove specific templates (user-specified to remove)
    # Color codes, math expressions, wikidata, timelines
    text = re.sub(r'\{\{#[0-9A-Fa-f]{6}\}\}', '', text)  # {{#8888FF}}
    text = re.sub(r'\{\{#expr:[^}]+\}\}', '', text, flags=re.IGNORECASE)  # {{#expr:...}}
    text = re.sub(r'\{\{#property:[^}]+\}\}', '', text, flags=re.IGNORECASE)  # {{#property:...}}
    text = re.sub(r'\{\{#tag:[^}]+\}\}', '', text, flags=re.IGNORECASE)  # {{#tag:...}}
    
    # Remove country/region codes
    text = re.sub(r'\{\{[A-Z]{2,3}-[A-Z]{2,3}(?:-[A-Za-z]+)?\}\}', '', text)  # {{AUT-HUN}}, {{BR-PR}}
    
    # Remove abbreviation templates
    text = re.sub(r'\{\{Abbr[^}]*\}\}', '', text, flags=re.IGNORECASE)
    
    # Remove audio templates
    text = re.sub(r'\{\{Audio[^}]*\}\}', '', text, flags=re.IGNORECASE)
    
    # Remove DISPLAYTITLE
    text = re.sub(r'\{\{DISPLAYTITLE:[^}]+\}\}', '', text, flags=re.IGNORECASE)
    
    # Remove category-like templates (Cienci, linguistiko, medicino, etc.)
    text = re.sub(r'\{\{(?:Cienci|linguistiko|medicino|muzik-jenro|kantisto|politikisto)\}\}', '', text, flags=re.IGNORECASE)
    
    # Remove list/navigation templates
    text = re.sub(r'\{\{Batalii [^}]+\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{Chef-urbi [^}]+\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{Chefministri [^}]+\}\}', '', text, flags=re.IGNORECASE)
    
    # Remove editorial markers
    text = re.sub(r'\{\{Citation needed\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{Bezonas tradukuro\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{Anciena informi\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{tradukenda\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{nekompleta\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{stub\}\}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{revizo\}\}', '', text, flags=re.IGNORECASE)
    
    # Collect suspicious templates if requested (after specific removals)
    if collect_questions:
        templates = ALL_TEMPLATES_RE.findall(text)
        for tpl_name in templates:
            tpl_name = tpl_name.strip()
            # Skip known templates
            if tpl_name.lower() in ['biografio', '#ifexist', 'cite', 'citation', 
                                     'reflist', 'commons', 'commonscat', 'authority control',
                                     'coord', 'geo', 'persondata', 'defaultsort',
                                     'lang', 'eo', 'io', 'en', 'fr', 'de', 'formatnum']:
                continue
            if len(tpl_name) > 3 and len(tpl_name) < 50:
                TEMPLATE_QUESTIONS.add(tpl_name)
    
    # Remove all remaining templates (generic cleanup)
    max_iterations = 10
    for _ in range(max_iterations):
        old_text = text
        text = re.sub(r'\{\{[^{}]*\}\}', '', text)
        if text == old_text:
            break
    
    # Handle wiki links: keep display text
    # First remove links with URLs: [[http://example.com text]] -> text
    text = re.sub(r'\[\[https?://[^\]]+\s+([^\]]+)\]\]', r'\1', text)
    # Then handle normal wiki links: [[target|display]] -> display, [[target]] -> target
    text = LINK_WITH_PIPE_RE.sub(r'\1', text)
    # Remove any remaining brackets (shouldn't be any, but just in case)
    text = text.replace('[[', '').replace(']]', '')
    
    # Remove HTML tags
    text = HTML_TAG_RE.sub('', text)
    
    # Remove section headers
    text = HEADER_RE.sub('\n', text)
    
    # Remove bold/italic markup
    text = text.replace("'''", "").replace("''", "")
    
    # Remove table markup
    text = re.sub(r'\{\|.*?\|\}', '', text, flags=re.DOTALL)
    text = re.sub(r'^\|.*?$', '', text, flags=re.MULTILINE)
    
    # Remove bullet points from lists
    text = re.sub(r'^\*\s+', '', text, flags=re.MULTILINE)
    
    # Remove IPA pronunciation patterns - must be before whitespace normalization
    text = re.sub(r'\(ifa:\s*[^\)]+\)', '', text, flags=re.IGNORECASE)
    
    # Remove Unicode directional marks
    text = re.sub(r'[\u200E\u200F\u202A-\u202E]', '', text)
    
    # Remove numbered list prefixes that appear after bullet removal
    text = re.sub(r'^\d{3,4}\)\s*', '', text, flags=re.MULTILINE)
    
    # Normalize whitespace
    text = WHITESPACE_RE.sub(' ', text)
    text = MULTIPLE_NEWLINES_RE.sub('\n', text)
    
    return text.strip()

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences with aggressive cleaning."""
    if not text:
        return []
    
    # Split on newlines and periods
    lines = text.split('\n')
    sentences = []
    
    for line in lines:
        line = line.strip()
        
        # Skip very short lines
        if len(line) < 10:
            continue
        
        # Skip horizontal rules (---- or more)
        if re.match(r'^-{4,}$', line):
            continue
        
        # Skip lines starting with asterisk (bullet points that survived)
        if line.startswith('*'):
            continue
        
        # Remove numbered list prefixes (1918), 1650), etc.) - these appear after bullet removal
        line = re.sub(r'^\d{3,4}\)\s*', '', line)
        
        # Remove incomplete parenthetical markers at end: (n, (m, (f, (d
        line = re.sub(r'\s*\([nmfd]\s*$', '', line)
        
        # Skip lines with image/file references or captions
        if any(marker in line.lower() for marker in ['thumb|', 'arkivo:', 'file:', '|thumb', '|right', '|left', ', da ', '|center']):
            continue
        
        # Skip lines starting with pipe (table remnants)
        if line.startswith('|'):
            continue
        
        # Remove URL fragments
        if 'http://' in line or 'https://' in line or line.startswith('[http'):
            continue
        
        # Normalize dashes (en-dash → hyphen)
        line = line.replace('–', '-').replace('—', '-')
        
        # Remove excessive whitespace
        line = ' '.join(line.split())
        
        # Final length check after cleaning
        if len(line) < 10:
            continue
        
        # Smart sentence splitting that respects parentheses and abbreviations
        # Don't split on periods inside parentheses or after abbreviations like "n."
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
                # Check if this is an abbreviation (n., m., etc.)
                if i > 0 and i < len(line) - 1:
                    # Look back for single letter + period
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
        
        sentences.extend(parts)
    
    return sentences

def process_wikipedia_xml(
    input_file: Path,
    output_file: Path,
    limit: int = None,
    collect_questions: bool = False
) -> dict:
    """Process Wikipedia XML dump and extract clean text."""
    
    print(f"Processing {input_file}...")
    print(f"This may take a while for large dumps...")
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
            clean_text = clean_wikitext(text, collect_questions)
            
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
            if processed_count % 100 == 0:
                elapsed = time.time() - start_time
                rate = processed_count / elapsed if elapsed > 0 else 0
                print(f"  Processed {processed_count} articles "
                      f"({total_sentences} sentences, {rate:.1f} articles/sec)")
    
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
        description='Parse Wikipedia XML dump for embedding training'
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
    parser.add_argument(
        '--collect-questions',
        action='store_true',
        help='Collect questions about uncertain templates'
    )
    
    args = parser.parse_args()
    
    # Process
    stats = process_wikipedia_xml(
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
    print(f"Articles:        {stats['processed_articles']}")
    print(f"Skipped:         {stats['skipped_articles']}")
    print(f"Sentences:       {stats['total_sentences']}")
    print(f"Time:            {stats['elapsed_seconds']:.2f} seconds")
    print(f"Speed:           {stats['articles_per_second']:.1f} articles/sec")
    print("="*60)
    
    # Print suspicious templates
    if args.collect_questions and TEMPLATE_QUESTIONS:
        print("\n" + "="*60)
        print("SUSPICIOUS TEMPLATES FOUND")
        print("="*60)
        print(f"Found {len(TEMPLATE_QUESTIONS)} unique template types")
        print("These templates were encountered but not in the known-safe list:")
        print("\nShould these be kept or removed?")
        print("-" * 60)
        for i, tpl in enumerate(sorted(TEMPLATE_QUESTIONS), 1):
            print(f"{i:3d}. {{{{{tpl}}}}}")
        
        # Save to file for review
        questions_file = args.output.parent / 'suspicious_templates.txt'
        with open(questions_file, 'w', encoding='utf-8') as f:
            f.write("# Suspicious Templates Found in Ido Wikipedia\n")
            f.write(f"# Total: {len(TEMPLATE_QUESTIONS)} unique templates\n\n")
            for tpl in sorted(TEMPLATE_QUESTIONS):
                f.write(f"{{{{{tpl}}}}}\n")
        print(f"\nSaved to: {questions_file}")
    
    print("\n✓ Done!")

if __name__ == '__main__':
    main()
