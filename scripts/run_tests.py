#!/usr/bin/env python3
"""
Run all tests for dictionary regeneration scripts.
"""

import sys
import subprocess
from pathlib import Path

TEST_FILES = [
    "test_format_converters.py",
    "test_merge_translations.py",
    "test_regeneration_pipeline.py"
]


def run_test(test_file):
    """Run a single test file."""
    script_dir = Path(__file__).parent
    test_path = script_dir / test_file
    
    if not test_path.exists():
        print(f"⚠️  Test file not found: {test_file}")
        return False
    
    print(f"\n{'='*70}")
    print(f"Running: {test_file}")
    print(f"{'='*70}")
    
    result = subprocess.run(
        [sys.executable, str(test_path)],
        cwd=script_dir,
        capture_output=False
    )
    
    return result.returncode == 0


def main():
    """Run all tests."""
    print("="*70)
    print("RUNNING ALL TESTS")
    print("="*70)
    
    results = []
    for test_file in TEST_FILES:
        passed = run_test(test_file)
        results.append((test_file, passed))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_file, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_file}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "="*70)
    if all_passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

