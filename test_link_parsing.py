#!/usr/bin/env python3
"""Test link parsing for Wikipedia parser."""

import re

# Test cases
test_cases = [
    # (input, expected_output)
    ("Vivis sub la [[povreso-lineo]] 3.8%", "Vivis sub la povreso-lineo 3.8%"),
    ("[[povreso-lineo]]", "povreso-lineo"),
    ("[[target|display text]]", "display text"),
    ("[[http://example.com text]]", "text"),
    ("normal [[link]] text", "normal link text"),
    ("[[Category:Test]]", ""),  # Should be removed earlier
]

def test_link_parsing():
    """Test the link parsing logic."""
    
    # Pattern 1: Remove URL links first
    url_pattern = re.compile(r'\[\[https?://[^\]]+\s+([^\]]+)\]\]')
    
    # Pattern 2: Handle wiki links with pipe
    pipe_pattern = re.compile(r'\[\[(?:[^\]|]+\|)?([^\]]+)\]\]')
    
    print("Testing link parsing:")
    print("=" * 60)
    
    for input_text, expected in test_cases:
        # Apply patterns in order
        result = url_pattern.sub(r'\1', input_text)
        result = pipe_pattern.sub(r'\1', result)
        
        status = "✓" if result == expected else "✗"
        print(f"{status} Input:    {input_text}")
        print(f"  Expected: {expected}")
        print(f"  Got:      {result}")
        print()

if __name__ == '__main__':
    test_link_parsing()
