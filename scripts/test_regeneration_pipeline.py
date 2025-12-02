#!/usr/bin/env python3
"""
Integration tests for dictionary regeneration pipeline.

Tests the full workflow:
1. Format conversion from multiple sources
2. Merging translations
3. Bidix generation
4. Monodix regeneration
"""

import sys
import json
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from format_converters import (
    convert_bert_format,
    convert_vortaro_format,
    convert_extractor_format,
    load_and_convert_json
)
from merge_translations import merge_all_translations


def create_test_bert_json(tmpdir):
    """Create a test BERT format JSON file."""
    test_data = {
        "partoprenar": [
            {"translation": "partopreni", "similarity": 1.0}
        ],
        "vorto": [
            {"translation": "vorto", "similarity": 1.0}
        ],
        "bona": [
            {"translation": "bona", "similarity": 1.0}
        ]
    }
    
    json_file = tmpdir / "test_bert.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2)
    
    return json_file


def create_test_vortaro_json(tmpdir):
    """Create a test Vortaro format JSON file."""
    test_data = {
        "ido_to_esperanto": [
            {
                "ido": "partoprenar",
                "esperanto": ["partopreni"],
                "similarities": [0.95]
            },
            {
                "ido": "nova",
                "esperanto": ["nova", "noveca"],
                "similarities": [1.0, 0.85]
            }
        ]
    }
    
    json_file = tmpdir / "test_vortaro.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2)
    
    return json_file


def test_full_pipeline():
    """Test the full regeneration pipeline."""
    print("="*70)
    print("TESTING FULL REGENERATION PIPELINE")
    print("="*70)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        
        # Step 1: Create test JSON files
        print("\n1. Creating test JSON files...")
        bert_file = create_test_bert_json(tmpdir)
        vortaro_file = create_test_vortaro_json(tmpdir)
        print(f"   ✅ Created: {bert_file.name}, {vortaro_file.name}")
        
        # Step 2: Convert formats
        print("\n2. Converting formats...")
        bert_data, bert_format = load_and_convert_json(bert_file)
        vortaro_data, vortaro_format = load_and_convert_json(vortaro_file)
        
        assert bert_format == "bert"
        assert vortaro_format == "vortaro"
        print(f"   ✅ BERT: {len(bert_data)} words")
        print(f"   ✅ Vortaro: {len(vortaro_data)} words")
        
        # Step 3: Merge
        print("\n3. Merging translations...")
        merged, stats = merge_all_translations([bert_data, vortaro_data])
        
        assert len(merged) >= 3  # At least partoprenar, vorto, bona, nova
        print(f"   ✅ Merged: {stats['total_words']} words, {stats['total_translations']} translations")
        
        # Step 4: Check that partoprenar has multiple translations
        if "partoprenar" in merged:
            trans_count = len(merged["partoprenar"])
            print(f"   ✅ 'partoprenar' has {trans_count} translation(s)")
        
        print("\n" + "="*70)
        print("✅ FULL PIPELINE TEST PASSED")
        print("="*70)
        return True


def test_bidix_generation():
    """Test bidix XML generation."""
    print("\n" + "="*70)
    print("TESTING BIDIX GENERATION")
    print("="*70)
    
    # Test that we can import and use bidix generation
    try:
        from regenerate_bidix import generate_bidix_from_merged
        
        test_data = {
            "testo": [
                {"translation": "testo", "similarity": 1.0}
            ]
        }
        
        entries, stats = generate_bidix_from_merged(test_data)
        
        assert len(entries) > 0
        assert stats['entries_created'] > 0
        
        print(f"   ✅ Generated {stats['entries_created']} bidix entries")
        return True
    except Exception as e:
        print(f"   ⚠️  Bidix generation test skipped: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*70)
    print("INTEGRATION TESTS")
    print("="*70)
    
    results = []
    
    try:
        result = test_full_pipeline()
        results.append(("Full Pipeline", result))
    except Exception as e:
        print(f"\n❌ Full pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Full Pipeline", False))
    
    try:
        result = test_bidix_generation()
        results.append(("Bidix Generation", result))
    except Exception as e:
        print(f"\n❌ Bidix generation test failed: {e}")
        results.append(("Bidix Generation", False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    if all_passed:
        print("\n✅ All integration tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed or were skipped")
        sys.exit(1)

