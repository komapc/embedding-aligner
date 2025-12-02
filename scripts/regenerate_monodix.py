#!/usr/bin/env python3
"""
Regenerate monolingual dictionary (monodix) from bidix.

Extracts Ido lemmas from bidix, updates YAML lexicon, and regenerates monodix.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict
import xml.etree.ElementTree as ET
import yaml

# Import monodix generation from existing script
sys.path.insert(0, str(Path(__file__).parent))
try:
    # Try to import from generate_ido_monodix_from_yaml.py
    from importlib import util
    spec = util.spec_from_file_location(
        "generate_monodix_module",
        Path(__file__).parent / "generate_ido_monodix_from_yaml.py"
    )
    if spec and spec.loader:
        generate_module = util.module_from_spec(spec)
        spec.loader.exec_module(generate_module)
        generate_monodix = generate_module.generate_monodix
    else:
        generate_monodix = None
except Exception:
    generate_monodix = None


def extract_lemmas_from_bidix(bidix_file: Path) -> Dict[str, str]:
    """
    Extract Ido lemmas and their POS tags from bidix.
    
    Returns:
        dict mapping lemma -> pos (e.g., {'partoprenar': 'vblex', 'vorto': 'n'})
    """
    import xml.etree.ElementTree as ET
    
    print(f"Extracting lemmas from bidix: {bidix_file}")
    
    if not bidix_file.exists():
        raise FileNotFoundError(f"Bidix file not found: {bidix_file}")
    
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
            # Use first POS if multiple, or preserve existing
            if lemma_text not in lemmas or not lemmas[lemma_text]:
                lemmas[lemma_text] = pos
    
    print(f"✅ Extracted {len(lemmas)} lemmas from bidix")
    return lemmas


def update_yaml_from_bidix_lemmas(yaml_file: Path, bidix_lemmas: Dict[str, str], 
                                   existing_paradigms: Dict[str, str] = None) -> tuple:
    """
    Update YAML lexicon with new lemmas from bidix.
    
    Maps POS tags to paradigm names based on existing paradigms.
    
    Returns:
        (success: bool, stats: dict)
    """
    print(f"\nUpdating YAML lexicon: {yaml_file}")
    
    # Load existing YAML
    if yaml_file.exists():
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}
        print(f"⚠️  YAML file does not exist, creating new one")
    
    # Ensure structure exists
    if 'entries' not in data:
        data['entries'] = []
    
    if 'paradigms' not in data:
        data['paradigms'] = {}
    
    # Map POS to paradigm
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
    
    stats = {
        'existing': len(existing_lemmas),
        'new': 0,
        'skipped_unknown_pos': 0
    }
    
    # Add new lemmas
    for lemma, pos in bidix_lemmas.items():
        if lemma in existing_lemmas:
            continue
        
        paradigm = pos_to_paradigm.get(pos)
        if not paradigm:
            stats['skipped_unknown_pos'] += 1
            continue
        
        data['entries'].append({
            'lemma': lemma,
            'pos': pos,
            'paradigm': paradigm,
            'source': 'bidix'
        })
        stats['new'] += 1
    
    # Sort entries by lemma
    data['entries'].sort(key=lambda x: x.get('lemma', ''))
    
    # Add metadata
    if 'meta' not in data:
        data['meta'] = {}
    data['meta']['last_updated'] = 'auto-generated from bidix'
    
    # Write back
    yaml_file.parent.mkdir(parents=True, exist_ok=True)
    with open(yaml_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    
    print(f"✅ YAML updated: {stats['existing']} existing, {stats['new']} new, {stats['skipped_unknown_pos']} skipped (unknown POS)")
    return True, stats


def generate_monodix_from_yaml(yaml_file: Path, monodix_file: Path) -> bool:
    """
    Generate monodix from YAML using existing script logic.
    
    Reuses generate_ido_monodix_from_yaml.py functionality.
    """
    if generate_monodix:
        # Use existing function if available
        try:
            generate_monodix(yaml_file, monodix_file)
            return True
        except Exception as e:
            print(f"⚠️  Error using existing generate function: {e}")
            print("   Falling back to basic generation...")
    
    # Fallback: basic generation
    print(f"\nGenerating monodix from YAML...")
    
    # Load YAML
    with open(yaml_file, 'r', encoding='utf-8') as f:
        yaml_data = yaml.safe_load(f) or {}
    
    # Load existing monodix
    if monodix_file.exists():
        tree = ET.parse(monodix_file)
        root = tree.getroot()
    else:
        print(f"⚠️  Monodix file does not exist: {monodix_file}")
        return False
    
    # This is a simplified version - full implementation should reuse
    # generate_ido_monodix_from_yaml.py logic
    print(f"✅ Monodix structure loaded, entries need to be regenerated")
    print(f"   Note: Full regeneration should use generate_ido_monodix_from_yaml.py")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description='Regenerate monolingual dictionary from bidix'
    )
    parser.add_argument(
        '--bidix',
        required=True,
        type=Path,
        help='Input bidix file path'
    )
    parser.add_argument(
        '--yaml',
        default=Path('../../apdata/ido_lexicon.yaml'),
        type=Path,
        help='YAML lexicon file (default: ../../apdata/ido_lexicon.yaml)'
    )
    parser.add_argument(
        '--output',
        default=Path('../../apertium/apertium-ido/apertium-ido.ido.dix'),
        type=Path,
        help='Output monodix file (default: ../../apertium/apertium-ido/...)'
    )
    
    args = parser.parse_args()
    
    # Resolve paths relative to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent  # Go up from scripts/ to workspace root
    
    # Resolve bidix (absolute or relative to current dir)
    if args.bidix.is_absolute():
        bidix_file = args.bidix
    else:
        bidix_file = (Path.cwd() / args.bidix).resolve()
    
    # Resolve yaml (relative to script or absolute)
    if args.yaml.is_absolute():
        yaml_file = args.yaml
    else:
        # Try relative to project root first
        yaml_candidate = project_root / args.yaml
        if yaml_candidate.exists():
            yaml_file = yaml_candidate.resolve()
        else:
            yaml_file = (script_dir / args.yaml).resolve()
    
    # Resolve monodix (relative to project root or absolute)
    if args.output.is_absolute():
        monodix_file = args.output
    else:
        # Try relative to project root
        monodix_candidate = project_root / args.output
        if monodix_candidate.exists() or monodix_candidate.parent.exists():
            monodix_file = monodix_candidate.resolve()
        else:
            monodix_file = (script_dir / args.output).resolve()
    
    print("="*70)
    print("REGENERATE MONODIX FROM BIDIX")
    print("="*70)
    print(f"\nInput:")
    print(f"  Bidix: {bidix_file}")
    print(f"  YAML:  {yaml_file}")
    print(f"\nOutput:")
    print(f"  Monodix: {monodix_file}")
    
    # Step 1: Extract lemmas from bidix
    print(f"\n{'='*70}")
    print("STEP 1: Extracting lemmas from bidix")
    print(f"{'='*70}")
    
    try:
        bidix_lemmas = extract_lemmas_from_bidix(bidix_file)
    except Exception as e:
        print(f"❌ ERROR extracting lemmas: {e}")
        sys.exit(1)
    
    # Step 2: Update YAML lexicon
    print(f"\n{'='*70}")
    print("STEP 2: Updating YAML lexicon")
    print(f"{'='*70}")
    
    try:
        success, yaml_stats = update_yaml_from_bidix_lemmas(yaml_file, bidix_lemmas)
        if not success:
            print(f"❌ ERROR updating YAML")
            sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR updating YAML: {e}")
        sys.exit(1)
    
    # Step 3: Generate monodix from YAML
    print(f"\n{'='*70}")
    print("STEP 3: Generating monodix from YAML")
    print(f"{'='*70}")
    
    # Use the existing generate_ido_monodix_from_yaml.py script
    generate_script = Path(__file__).parent / 'generate_ido_monodix_from_yaml.py'
    
    if not generate_script.exists():
        print(f"❌ ERROR: generate_ido_monodix_from_yaml.py not found at {generate_script}")
        sys.exit(1)
    
    import subprocess
    cmd = [
        sys.executable,
        str(generate_script),
        '--yaml', str(yaml_file),
        '--monodix', str(monodix_file)
    ]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ ERROR generating monodix:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    
    print(result.stdout)
    
    print(f"\n{'='*70}")
    print("✅ MONODIX REGENERATION COMPLETE")
    print(f"{'='*70}")
    print(f"\nNext steps:")
    print(f"1. Rebuild analyzer: cd {monodix_file.parent} && make clean && make")
    print(f"2. Test: echo 'test' | lt-proc {monodix_file.parent}/ido.automorf.bin")


if __name__ == '__main__':
    main()

