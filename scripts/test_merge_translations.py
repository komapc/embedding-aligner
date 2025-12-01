#!/usr/bin/env python3
"""Test merge translations module."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from merge_translations import merge_all_translations


def test_merge_all_translations():
    """Test merging multiple sources keeping all translations."""
    source1 = {
        "test": [
            {"translation": "testo", "similarity": 0.95, "source": "bert"}
        ]
    }
    
    source2 = {
        "test": [
            {"translation": "testo", "similarity": 0.90, "source": "vortaro"},
            {"translation": "provo", "similarity": 0.85, "source": "vortaro"}
        ]
    }
    
    merged, stats = merge_all_translations([source1, source2])
    
    # Should have all 3 translations
    assert "test" in merged
    assert len(merged["test"]) == 3, f"Expected 3 translations, got {len(merged['test'])}"
    
    # Check all sources are present
    sources = {t["source"] for t in merged["test"]}
    assert "bert" in sources
    assert "vortaro" in sources
    
    print("✅ Merge keeps all translations")
    print(f"   Merged {stats['total_words']} words with {stats['total_translations']} translations")


def test_merge_different_words():
    """Test merging sources with different words."""
    source1 = {"word1": [{"translation": "vorto1", "similarity": 0.95, "source": "bert"}]}
    source2 = {"word2": [{"translation": "vorto2", "similarity": 0.90, "source": "vortaro"}]}
    
    merged, stats = merge_all_translations([source1, source2])
    
    assert len(merged) == 2
    assert "word1" in merged
    assert "word2" in merged
    
    print("✅ Merge handles different words correctly")


if __name__ == "__main__":
    print("Testing merge translations...")
    print("=" * 60)
    
    test_merge_all_translations()
    test_merge_different_words()
    
    print("=" * 60)
    print("✅ All merge tests passed!")

