#!/usr/bin/env python3
"""
Unified script to regenerate ALL dictionaries from BERT alignment JSON.

This script automates the complete pipeline:
1. BERT JSON → bidix (apertium-ido-epo.ido-epo.dix)
2. Extract lemmas from bidix → update YAML lexicon
3. YAML → monodix (apertium-ido.ido.dix)
4. Rebuild both analyzers

Usage:
    python3 regenerate_all_from_bert.py \
        --bert-json results/bert_aligned_clean_0.60/bert_candidates.json \
        --yaml ../../apdata/ido_lexicon.yaml \
        --bidix ../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix \
        --monodix ../../apertium/apertium-ido/apertium-ido.ido.dix \
        [--rebuild]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Set, Tuple

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Install with: pip install pyyaml")
    sys.exit(1)


def run_command(cmd: list, cwd: Path = None, description: str = None):
    """Run a command and handle errors."""
    if description:
        print(f"\n{description}...")
    
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ ERROR running: {' '.join(cmd)}")
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        return False
    
    if result.stdout:
        print(result.stdout)
    
    return True


def extract_lemmas_from_bidix(bidix_file: Path) -> Dict[str, str]:
    """
    Extract Ido lemmas and their POS tags from bidix.
    
    Returns:
        dict mapping lemma -> pos (e.g., {'partoprenar': 'vblex', 'vorto': 'n'})
    """
    import xml.etree.ElementTree as ET
    
    print(f"Extracting lemmas from bidix: {bidix_file}")
    
    tree = ET.parse(bidix_file)
    root = tree.getroot()
    
    lemmas = {}
    
    # Find all entries
    for entry in root.findall('.//e'):
        l_elem = entry.find('.//l')
        if l_elem is None:
            continue
        
        # Get lemma text (before any <s> tag)
        lemma_text = ''
        if l_elem.text:
            lemma_text = l_elem.text.strip()
        
        # Get POS tag
        s_elem = l_elem.find('s')
        pos = None
        if s_elem is not None:
            pos = s_elem.get('n')
        
        if lemma_text and pos:
            # Normalize: use existing entry if present, or add new
            if lemma_text not in lemmas or not lemmas[lemma_text]:
                lemmas[lemma_text] = pos
    
    print(f"✅ Extracted {len(lemmas)} lemmas from bidix")
    return lemmas


def update_yaml_from_bidix_lemmas(yaml_file: Path, bidix_lemmas: Dict[str, str], 
                                   existing_paradigms: Dict[str, str] = None) -> bool:
    """
    Update YAML lexicon with new lemmas from bidix.
    
    Maps POS tags to paradigm names based on existing paradigms.
    """
    print(f"\nUpdating YAML lexicon: {yaml_file}")
    
    # Load existing YAML
    if yaml_file.exists():
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
    
    # Ensure structure exists
    if 'entries' not in data:
        data['entries'] = []
    
    if 'paradigms' not in data:
        data['paradigms'] = {}
    
    # Map POS to paradigm (based on existing paradigms)
    pos_to_paradigm = {
        'n': 'noun_o',
        'adj': 'adj_a',
        'adv': 'adv_e',
        'vblex': 'verb_ar',
        'pr': 'prep',
        'det': 'det',
        'cnjcoo': 'conj_coo',
        'cnjsub': 'conj_sub',
    }
    
    # Ensure paradigms exist
    paradigm_mappings = {
        'noun_o': 'o__n',
        'adj_a': 'a__adj',
        'adv_e': 'e__adv',
        'verb_ar': 'ar__vblex',
        'prep': '__pr',
        'det': '__det',
        'conj_coo': '__cnjcoo',
        'conj_sub': '__cnjsub',
    }
    
    for name, pardef in paradigm_mappings.items():
        if name not in data['paradigms']:
            data['paradigms'][name] = pardef
    
    # Track existing lemmas
    existing_lemmas = {e['lemma'] for e in data['entries'] if 'lemma' in e}
    
    # Add new lemmas
    added = 0
    for lemma, pos in bidix_lemmas.items():
        if lemma in existing_lemmas:
            continue
        
        paradigm = pos_to_paradigm.get(pos)
        if not paradigm:
            print(f"⚠️  Skipping {lemma} (unknown POS: {pos})")
            continue
        
        data['entries'].append({
            'lemma': lemma,
            'pos': pos,
            'paradigm': paradigm,
            'source': 'bidix'
        })
        added += 1
    
    # Sort entries by lemma
    data['entries'].sort(key=lambda x: x.get('lemma', ''))
    
    # Add metadata
    if 'meta' not in data:
        data['meta'] = {}
    data['meta']['last_updated'] = 'auto-generated from bidix'
    
    # Write back
    with open(yaml_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"✅ Added {added} new lemmas to YAML (total: {len(data['entries'])})")
    return True


def regenerate_bidix_from_bert(bert_json: Path, output_dir: Path, 
                                min_similarity: float = 0.70) -> Path:
    """Regenerate bidix from BERT alignment JSON."""
    print(f"\n{'='*60}")
    print("STEP 1: Regenerating bidix from BERT JSON")
    print(f"{'='*60}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run the format script
    format_script = Path(__file__).parent / '17_format_for_apertium.py'
    
    cmd = [
        sys.executable,
        str(format_script),
        '--input', str(bert_json),
        '--output', str(output_dir),
        '--min-similarity', str(min_similarity),
        '--max-candidates', '1',
        '--add-pos-tags'
    ]
    
    if not run_command(cmd, description="Formatting BERT candidates for Apertium"):
        return None
    
    bidix_output = output_dir / 'ido-epo.dix'
    if not bidix_output.exists():
        print(f"❌ ERROR: Bidix output not created: {bidix_output}")
        return None
    
    print(f"✅ Bidix generated: {bidix_output}")
    return bidix_output


def copy_bidix_to_repo(bidix_source: Path, bidix_target: Path):
    """Copy generated bidix to apertium-ido-epo repo."""
    print(f"\nCopying bidix to repo...")
    print(f"  From: {bidix_source}")
    print(f"  To:   {bidix_target}")
    
    import shutil
    shutil.copy2(bidix_source, bidix_target)
    print(f"✅ Bidix copied to repo")


def regenerate_monodix_from_yaml(yaml_file: Path, monodix_file: Path):
    """Regenerate monodix from YAML lexicon."""
    print(f"\n{'='*60}")
    print("STEP 2: Regenerating monodix from YAML")
    print(f"{'='*60}")
    
    generate_script = Path(__file__).parent / 'generate_ido_monodix_from_yaml.py'
    
    cmd = [
        sys.executable,
        str(generate_script),
        '--yaml', str(yaml_file),
        '--monodix', str(monodix_file)
    ]
    
    if not run_command(cmd, description="Generating monodix from YAML"):
        return False
    
    print(f"✅ Monodix regenerated from YAML")
    return True


def rebuild_analyzers(apertium_ido_epo_dir: Path, apertium_ido_dir: Path):
    """Rebuild both monolingual and bilingual analyzers."""
    print(f"\n{'='*60}")
    print("STEP 3: Rebuilding analyzers")
    print(f"{'='*60}")
    
    # Rebuild apertium-ido (monolingual)
    print("\nRebuilding Ido monolingual analyzer...")
    if not run_command(['make', 'clean'], cwd=apertium_ido_dir):
        return False
    if not run_command(['make', '-j4'], cwd=apertium_ido_dir):
        return False
    
    # Rebuild apertium-ido-epo (bilingual)
    print("\nRebuilding Ido-Esperanto bilingual analyzer...")
    if not run_command(['make', 'clean'], cwd=apertium_ido_epo_dir):
        return False
    if not run_command(['make', '-j4'], cwd=apertium_ido_epo_dir):
        return False
    
    print(f"\n✅ All analyzers rebuilt successfully")
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Regenerate all dictionaries from BERT alignment JSON'
    )
    parser.add_argument(
        '--bert-json',
        required=True,
        type=Path,
        help='BERT alignment candidates JSON file'
    )
    parser.add_argument(
        '--yaml',
        default=Path('../../apdata/ido_lexicon.yaml'),
        type=Path,
        help='YAML lexicon file (default: ../../apdata/ido_lexicon.yaml)'
    )
    parser.add_argument(
        '--bidix',
        default=Path('../../apertium/apertium-ido-epo/apertium-ido-epo.ido-epo.dix'),
        type=Path,
        help='Target bidix file (default: ../../apertium/apertium-ido-epo/...)'
    )
    parser.add_argument(
        '--monodix',
        default=Path('../../apertium/apertium-ido/apertium-ido.ido.dix'),
        type=Path,
        help='Target monodix file (default: ../../apertium/apertium-ido/...)'
    )
    parser.add_argument(
        '--min-similarity',
        type=float,
        default=0.70,
        help='Minimum similarity threshold for BERT candidates (default: 0.70)'
    )
    parser.add_argument(
        '--rebuild',
        action='store_true',
        help='Rebuild analyzers after regeneration (default: False)'
    )
    parser.add_argument(
        '--output-dir',
        default=Path('results/apertium_format_fixed'),
        type=Path,
        help='Output directory for intermediate bidix (default: results/apertium_format_fixed)'
    )
    
    args = parser.parse_args()
    
    # Resolve all paths relative to script location
    script_dir = Path(__file__).parent
    bert_json = (script_dir / args.bert_json).resolve() if not args.bert_json.is_absolute() else args.bert_json
    yaml_file = (script_dir / args.yaml).resolve() if not args.yaml.is_absolute() else args.yaml
    bidix_file = (script_dir / args.bidix).resolve() if not args.bidix.is_absolute() else args.bidix
    monodix_file = (script_dir / args.monodix).resolve() if not args.monodix.is_absolute() else args.monodix
    output_dir = (script_dir / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    
    # Verify inputs
    if not bert_json.exists():
        print(f"❌ ERROR: BERT JSON not found: {bert_json}")
        sys.exit(1)
    
    print("="*70)
    print("REGENERATE ALL DICTIONARIES FROM BERT JSON")
    print("="*70)
    print(f"\nInput:")
    print(f"  BERT JSON: {bert_json}")
    print(f"\nOutput:")
    print(f"  YAML lexicon: {yaml_file}")
    print(f"  Bidix: {bidix_file}")
    print(f"  Monodix: {monodix_file}")
    print(f"\nOptions:")
    print(f"  Min similarity: {args.min_similarity}")
    print(f"  Rebuild analyzers: {args.rebuild}")
    
    # Step 1: Regenerate bidix from BERT JSON
    bidix_output = regenerate_bidix_from_bert(
        bert_json,
        output_dir,
        min_similarity=args.min_similarity
    )
    
    if not bidix_output:
        print("\n❌ FAILED: Could not generate bidix from BERT JSON")
        sys.exit(1)
    
    # Step 2: Copy bidix to repo
    copy_bidix_to_repo(bidix_output, bidix_file)
    
    # Step 3: Extract lemmas from bidix and update YAML
    print(f"\n{'='*60}")
    print("STEP 3: Extracting lemmas from bidix → updating YAML")
    print(f"{'='*60}")
    
    bidix_lemmas = extract_lemmas_from_bidix(bidix_file)
    
    # Load existing paradigms from YAML to avoid overwriting
    existing_paradigms = {}
    if yaml_file.exists():
        with open(yaml_file, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f) or {}
            existing_paradigms = yaml_data.get('paradigms', {})
    
    if not update_yaml_from_bidix_lemmas(yaml_file, bidix_lemmas, existing_paradigms):
        print("\n⚠️  WARNING: Could not update YAML, continuing anyway...")
    
    # Step 4: Regenerate monodix from updated YAML
    if not regenerate_monodix_from_yaml(yaml_file, monodix_file):
        print("\n❌ FAILED: Could not regenerate monodix from YAML")
        sys.exit(1)
    
    # Step 5: Rebuild analyzers (if requested)
    if args.rebuild:
        apertium_ido_epo_dir = bidix_file.parent
        apertium_ido_dir = monodix_file.parent
        
        if not rebuild_analyzers(apertium_ido_epo_dir, apertium_ido_dir):
            print("\n❌ FAILED: Could not rebuild analyzers")
            sys.exit(1)
    
    print("\n" + "="*70)
    print("✅ REGENERATION COMPLETE")
    print("="*70)
    print(f"\nNext steps:")
    if not args.rebuild:
        print("1. Rebuild analyzers manually:")
        print(f"   cd {bidix_file.parent} && make clean && make")
        print(f"   cd {monodix_file.parent} && make clean && make")
    print("2. Test translation:")
    print(f"   cd {bidix_file.parent} && echo 'test' | apertium -d . ido-epo")
    print("\nAll dictionaries regenerated from BERT JSON! ✅")


if __name__ == '__main__':
    main()

