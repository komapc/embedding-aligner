#!/usr/bin/env python3
"""
Preprocess Wikipedia dumps into clean text corpora.
Extracts text, tokenizes, and prepares for FastText training.
"""

import os
import sys
import subprocess
from pathlib import Path

def extract_wikipedia(input_file, output_dir, language):
    """Extract Wikipedia dump using WikiExtractor."""
    print(f"Extracting {language} Wikipedia...")
    
    cmd = [
        'python', '-m', 'wikiextractor.WikiExtractor',
        input_file,
        '-o', output_dir,
        '--processes', '4',
        '--no-templates',
        '--quiet'
    ]
    
    subprocess.run(cmd, check=True)
    print(f"Extraction complete: {output_dir}")

def combine_extracted_files(extract_dir, output_file):
    """Combine all extracted wiki files into single corpus."""
    print(f"Combining files into {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as outf:
        for wiki_file in Path(extract_dir).rglob('wiki_*'):
            with open(wiki_file, 'r', encoding='utf-8') as inf:
                for line in inf:
                    line = line.strip()
                    if line and not line.startswith('<'):  # Skip XML tags
                        outf.write(line + '\n')
    
    print(f"Combined corpus saved: {output_file}")

def preprocess_corpus(input_file, output_file):
    """Basic preprocessing: lowercase, remove extra whitespace."""
    print(f"Preprocessing {input_file}...")
    
    with open(input_file, 'r', encoding='utf-8') as inf:
        with open(output_file, 'w', encoding='utf-8') as outf:
            for line in inf:
                # Basic cleaning
                line = line.strip().lower()
                # Remove multiple spaces
                line = ' '.join(line.split())
                if line:
                    outf.write(line + '\n')
    
    print(f"Preprocessed corpus saved: {output_file}")

def main():
    # Paths
    raw_dir = Path('data/raw')
    processed_dir = Path('data/processed')
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Process Ido
    print("\n=== Processing Ido Wikipedia ===")
    ido_dump = raw_dir / 'iowiki-latest-pages-articles.xml.bz2'
    ido_extract_dir = processed_dir / 'ido_extracted'
    ido_combined = processed_dir / 'ido_combined.txt'
    ido_final = processed_dir / 'ido_corpus.txt'
    
    if ido_dump.exists():
        extract_wikipedia(str(ido_dump), str(ido_extract_dir), 'Ido')
        combine_extracted_files(ido_extract_dir, ido_combined)
        preprocess_corpus(ido_combined, ido_final)
        print(f"✓ Ido corpus ready: {ido_final}")
    else:
        print(f"✗ Ido dump not found: {ido_dump}")
    
    # Process Esperanto
    print("\n=== Processing Esperanto Wikipedia ===")
    epo_dump = raw_dir / 'eowiki-latest-pages-articles.xml.bz2'
    epo_extract_dir = processed_dir / 'epo_extracted'
    epo_combined = processed_dir / 'epo_combined.txt'
    epo_final = processed_dir / 'epo_corpus.txt'
    
    if epo_dump.exists():
        extract_wikipedia(str(epo_dump), str(epo_extract_dir), 'Esperanto')
        combine_extracted_files(epo_extract_dir, epo_combined)
        preprocess_corpus(epo_combined, epo_final)
        print(f"✓ Esperanto corpus ready: {epo_final}")
    else:
        print(f"✗ Esperanto dump not found: {epo_dump}")
    
    print("\n=== Preprocessing Complete ===")
    print(f"Ido corpus: {ido_final}")
    print(f"Esperanto corpus: {epo_final}")

if __name__ == '__main__':
    main()
