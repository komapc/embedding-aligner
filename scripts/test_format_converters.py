#!/usr/bin/env python3
"""Test format converters module."""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent))

from format_converters import (
    convert_bert_format,
    convert_vortaro_format,
    convert_extractor_format,
    detect_format
)


def test_bert_format():
    """Test BERT format conversion."""
    bert_data = {
        "test": [
            {"translation": "testo", "similarity": 0.95}
        ]
    }
    result = convert_bert_format(bert_data, "test_source")
    
    assert "test" in result
    assert len(result["test"]) == 1
    assert result["test"][0]["translation"] == "testo"
    assert result["test"][0]["similarity"] == 0.95
    assert result["test"][0]["source"] == "test_source"
    
    print("✅ BERT format converter works")


def test_vortaro_format():
    """Test Vortaro format conversion."""
    vortaro_data = {
        "ido_to_esperanto": [
            {
                "ido": "testo",
                "esperanto": ["testo", "provo"],
                "similarities": [0.95, 0.90]
            }
        ]
    }
    result = convert_vortaro_format(vortaro_data, "vortaro_test")
    
    assert "testo" in result
    assert len(result["testo"]) == 2
    assert result["testo"][0]["translation"] == "testo"
    assert result["testo"][0]["similarity"] == 0.95
    assert result["testo"][1]["translation"] == "provo"
    
    print("✅ Vortaro format converter works")


def test_extractor_format():
    """Test Extractor format conversion."""
    extractor_data = [
        {
            "lemma": "testo",
            "language": "io",
            "senses": [
                {
                    "translations": [
                        {"lang": "eo", "term": "testo"}
                    ]
                }
            ]
        }
    ]
    result = convert_extractor_format(extractor_data, "extractor_test")
    
    assert "testo" in result
    assert len(result["testo"]) == 1
    assert result["testo"][0]["translation"] == "testo"
    assert result["testo"][0]["source"] == "extractor_test"
    
    print("✅ Extractor format converter works")


def test_format_detection():
    """Test format auto-detection."""
    bert_data = {"word": [{"translation": "..."}]}
    assert detect_format(bert_data) == "bert"
    
    vortaro_data = {"ido_to_esperanto": []}
    assert detect_format(vortaro_data) == "vortaro"
    
    extractor_data = [{"lemma": "...", "senses": []}]
    assert detect_format(extractor_data) == "extractor"
    
    print("✅ Format detection works")


if __name__ == "__main__":
    print("Testing format converters...")
    print("=" * 60)
    
    test_bert_format()
    test_vortaro_format()
    test_extractor_format()
    test_format_detection()
    
    print("=" * 60)
    print("✅ All format converter tests passed!")

