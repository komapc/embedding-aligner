#!/usr/bin/env python3
"""
Format converters for different JSON dictionary sources.

Converts BERT, Vortaro, and Extractor JSON formats to a common normalized format.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


def convert_bert_format(data: Dict[str, Any], source_name: str = "bert") -> Dict[str, List[Dict[str, Any]]]:
    """
    Convert BERT alignment format to normalized format.
    
    Input format:
    {
        "ido_word": [
            {"translation": "epo_word", "similarity": 0.95}
        ]
    }
    
    Output format:
    {
        "ido_word": [
            {"translation": "epo_word", "similarity": 0.95, "source": "bert"}
        ]
    }
    """
    normalized = {}
    
    for ido_word, candidates in data.items():
        if not isinstance(candidates, list):
            continue
        
        normalized[ido_word] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            
            translation = candidate.get('translation') or candidate.get('epo', '')
            similarity = candidate.get('similarity', 1.0)
            
            if translation:
                normalized[ido_word].append({
                    'translation': translation,
                    'similarity': float(similarity),
                    'source': source_name
                })
    
    return normalized


def convert_vortaro_format(data: Dict[str, Any], source_name: str = "vortaro") -> Dict[str, List[Dict[str, Any]]]:
    """
    Convert Vortaro format to normalized format.
    
    Input format:
    {
        "ido_to_esperanto": [
            {
                "ido": "word",
                "esperanto": ["word1", "word2"],
                "similarities": [0.95, 0.90]
            }
        ]
    }
    
    Output format:
    {
        "ido_word": [
            {"translation": "epo_word1", "similarity": 0.95, "source": "vortaro"},
            {"translation": "epo_word2", "similarity": 0.90, "source": "vortaro"}
        ]
    }
    """
    normalized = {}
    
    # Get the list of translations
    translations_list = data.get('ido_to_esperanto', [])
    if not isinstance(translations_list, list):
        return normalized
    
    for entry in translations_list:
        if not isinstance(entry, dict):
            continue
        
        ido_word = entry.get('ido', '').strip()
        esperanto_list = entry.get('esperanto', [])
        similarities = entry.get('similarities', [])
        
        if not ido_word:
            continue
        
        if not isinstance(esperanto_list, list):
            continue
        
        # Initialize entry if not exists
        if ido_word not in normalized:
            normalized[ido_word] = []
        
        # Add each Esperanto translation
        for idx, epo_word in enumerate(esperanto_list):
            if not epo_word or not isinstance(epo_word, str):
                continue
            
            similarity = 1.0
            if isinstance(similarities, list) and idx < len(similarities):
                similarity = float(similarities[idx])
            
            normalized[ido_word].append({
                'translation': epo_word.strip(),
                'similarity': similarity,
                'source': source_name
            })
    
    return normalized


def convert_extractor_format(data: List[Dict[str, Any]], source_name: str = "extractor") -> Dict[str, List[Dict[str, Any]]]:
    """
    Convert Extractor format to normalized format.
    
    Input format:
    [
        {
            "lemma": "word",
            "language": "io",
            "senses": [
                {
                    "translations": [
                        {"lang": "eo", "term": "word"}
                    ]
                }
            ]
        }
    ]
    
    Output format:
    {
        "ido_word": [
            {"translation": "epo_word", "similarity": 1.0, "source": "extractor"}
        ]
    }
    """
    normalized = {}
    
    if not isinstance(data, list):
        return normalized
    
    for entry in data:
        if not isinstance(entry, dict):
            continue
        
        # Only process Ido entries
        language = entry.get('language', '').lower()
        if language not in ('io', 'ido'):
            continue
        
        lemma = entry.get('lemma', '').strip()
        if not lemma:
            continue
        
        # Extract translations from senses
        senses = entry.get('senses', [])
        if not isinstance(senses, list):
            continue
        
        if lemma not in normalized:
            normalized[lemma] = []
        
        for sense in senses:
            if not isinstance(sense, dict):
                continue
            
            translations = sense.get('translations', [])
            if not isinstance(translations, list):
                continue
            
            for trans in translations:
                if not isinstance(trans, dict):
                    continue
                
                # Only Esperanto translations
                lang = trans.get('lang', '').lower()
                if lang not in ('eo', 'esperanto'):
                    continue
                
                term = trans.get('term', '').strip()
                if term:
                    normalized[lemma].append({
                        'translation': term,
                        'similarity': 1.0,  # Extractor doesn't have similarity scores
                        'source': source_name
                    })
    
    return normalized


def detect_format(data: Any) -> Optional[str]:
    """
    Auto-detect the format of JSON data.
    
    Returns: 'bert', 'vortaro', 'extractor', or None if unknown
    """
    if isinstance(data, dict):
        # Check for BERT format
        if data:
            first_key = list(data.keys())[0]
            first_val = data[first_key]
            if isinstance(first_val, list) and len(first_val) > 0:
                if isinstance(first_val[0], dict):
                    if 'translation' in first_val[0] or 'epo' in first_val[0]:
                        return 'bert'
                    if 'similarity' in first_val[0]:
                        return 'bert'
        
        # Check for Vortaro format
        if 'ido_to_esperanto' in data:
            return 'vortaro'
    
    elif isinstance(data, list):
        # Check for Extractor format
        if len(data) > 0:
            first_item = data[0]
            if isinstance(first_item, dict):
                if 'lemma' in first_item and 'senses' in first_item:
                    return 'extractor'
    
    return None


def load_and_convert_json(file_path: Path, format_type: Optional[str] = None, source_name: Optional[str] = None) -> Tuple[Dict[str, List[Dict[str, Any]]], str]:
    """
    Load JSON file, detect or use specified format, and convert to normalized format.
    
    Returns:
        (normalized_data, detected_format)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Auto-detect format if not specified
    if format_type is None:
        format_type = detect_format(data)
        if format_type is None:
            raise ValueError(f"Could not detect format for {file_path}. Please specify --format.")
    
    # Use filename as source name if not provided
    if source_name is None:
        source_name = file_path.stem
    
    # Convert based on format
    if format_type == 'bert':
        normalized = convert_bert_format(data, source_name)
    elif format_type == 'vortaro':
        normalized = convert_vortaro_format(data, source_name)
    elif format_type == 'extractor':
        normalized = convert_extractor_format(data, source_name)
    else:
        raise ValueError(f"Unknown format: {format_type}. Supported: bert, vortaro, extractor")
    
    return normalized, format_type


if __name__ == '__main__':
    # Test the converters
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: format_converters.py <json_file> [format]")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    format_type = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        normalized, detected = load_and_convert_json(file_path, format_type)
        print(f"✅ Converted {file_path}")
        print(f"   Format: {detected}")
        print(f"   Words: {len(normalized)}")
        
        # Show first few entries
        for i, (word, trans) in enumerate(list(normalized.items())[:3]):
            print(f"   {word}: {len(trans)} translations")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

