# Corpus Improvements Needed

Based on analysis of `ido_corpus_final.txt`, here are identified issues and suggested fixes:

## Critical Issues

### 1. **Bullet points not removed** ✓ HIGH PRIORITY
- **Problem**: Lines starting with `* ` (asterisk + space)
- **Example**: `* principo di unikeso: a singla formo...`
- **Fix**: Strip leading `* ` from all lines
- **Impact**: ~10,000+ lines affected

### 2. **IPA pronunciation markers** ✓ HIGH PRIORITY
- **Problem**: IPA phonetic transcriptions like `(ifa: ˈvarʂava)`, `(ifa: ˈbɔʐa ˈvɔla)`
- **Example**: `warszawa (ifa: ˈvarʂava) esas la maxim populoza urbo`
- **Fix**: Remove all `(ifa: ...)` patterns
- **Impact**: Hundreds of lines with IPA noise

### 3. **Unicode directional marks** ✓ MEDIUM PRIORITY
- **Problem**: U+200E (LTR mark), U+200F (RTL mark) invisible characters
- **Example**: `carlos prío socarrás‏‎, prezidanto di kuba`
- **Fix**: Remove all Unicode directional formatting characters (U+200E, U+200F, U+202A-U+202E)
- **Impact**: Hundreds of lines

### 4. **Incomplete wiki markup** ✓ HIGH PRIORITY
- **Problem**: Leftover `[[` and `]]` brackets
- **Example**: `[[arkivo:river amstel by night...]]`, `[[kategorio:dio`
- **Fix**: Remove all remaining `[[...]]` patterns
- **Impact**: Several hundred lines

### 5. **Table/image captions** ✓ HIGH PRIORITY
- **Problem**: Image markup like `thumb|200px|blazono di mongolia`
- **Example**: `[[arkivo:lutoslawski3.jpg|thumb|right|275px|witold...]]`
- **Fix**: Remove lines containing `thumb|`, `arkivo:`, `file:`
- **Impact**: Hundreds of lines

### 6. **Incomplete parenthetical notes** ✓ MEDIUM PRIORITY
- **Problem**: Birth/death markers cut off: `(n`, `(m`, `(f`, `(d`
- **Example**: `carp, chefministro di rumania (n`
- **Fix**: Remove trailing `(n`, `(m`, `(f`, `(d` at end of lines
- **Impact**: Thousands of lines (from date lists)

### 7. **Numbered list items** ✓ MEDIUM PRIORITY
- **Problem**: Lines starting with numbers and parentheses: `1918)`, `1650)`
- **Example**: `1918) * 6ma di januaro - pierre charles...`
- **Fix**: Remove leading year patterns `^\d{3,4}\)`
- **Impact**: Hundreds of lines

### 8. **Colon-prefixed labels** ✓ LOW PRIORITY
- **Problem**: Lines starting with labels like `noti:`, `exemple:`, `file:`, `arkivo:`
- **Example**: `exemple: patro (m.) -> patrino (f.)`
- **Fix**: Remove label prefix or entire line if it's metadata
- **Impact**: Hundreds of lines

### 9. **Superscript numbers** ✓ LOW PRIORITY
- **Problem**: Unicode superscript ² (56,472 occurrences!)
- **Example**: Area measurements, mathematical notation
- **Fix**: Convert `²` to `2` or remove
- **Impact**: Tens of thousands of occurrences

### 10. **Very short lines** ✓ MEDIUM PRIORITY
- **Problem**: Lines with < 5 characters (not useful for embeddings)
- **Example**: Single letters, punctuation
- **Fix**: Remove lines shorter than 10 characters
- **Impact**: Unknown quantity

### 11. **Pipe characters from tables** ✓ MEDIUM PRIORITY
- **Problem**: Leftover table markup with `|`
- **Example**: Lines starting with `|`
- **Fix**: Remove lines starting with `|` or containing excessive `|` characters
- **Impact**: Hundreds of lines

### 12. **URL fragments** ✓ LOW PRIORITY
- **Problem**: Partial URLs and web references
- **Example**: `http://www.ido.li/`, `[http://www.crazyverse.com/ido...]`
- **Fix**: Remove lines containing `http://`, `https://`, `[http`
- **Impact**: Hundreds of lines

### 13. **Template remnants** ✓ MEDIUM PRIORITY
- **Problem**: Still some `{{` and `}}` left
- **Example**: First line starts with `{{linguo`
- **Fix**: More aggressive template removal
- **Impact**: Unknown, but visible in first line

### 14. **Dash character inconsistency** ✓ LOW PRIORITY
- **Problem**: Mix of `-` (hyphen), `–` (en-dash, 17,472 occurrences), `—` (em-dash)
- **Example**: Date ranges, compound words
- **Fix**: Normalize all to simple hyphen `-`
- **Impact**: Tens of thousands

### 15. **Special linguistic characters** ✓ INFO ONLY
- **Problem**: IPA and special linguistic symbols: ˈ (9,350), ɔ (5,897), ɛ (4,589), ʂ (2,000)
- **Example**: From IPA transcriptions
- **Fix**: Already handled by removing `(ifa: ...)` patterns
- **Impact**: Will be cleaned with IPA removal

## Priority Order for Implementation

1. **HIGH**: Remove `* ` bullet points
2. **HIGH**: Remove IPA patterns `(ifa: ...)`
3. **HIGH**: Remove incomplete wiki markup `[[...]]`
4. **HIGH**: Remove image/file references
5. **MEDIUM**: Remove Unicode directional marks
6. **MEDIUM**: Remove incomplete parenthetical `(n`, `(m`, etc.
7. **MEDIUM**: Remove very short lines (< 10 chars)
8. **MEDIUM**: Remove numbered list prefixes
9. **LOW**: Remove/normalize superscripts
10. **LOW**: Remove URL fragments
11. **LOW**: Normalize dashes

## Estimated Impact

- **Before**: 392,319 lines
- **After cleanup**: ~350,000-370,000 lines (10-15% reduction)
- **Quality improvement**: Significant - removes noise and metadata

## Implementation

Update `clean_wikitext()` function in `parse_wikipedia_xml.py` with these additional cleaning steps.
