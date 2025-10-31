# Ido Wikipedia Parsing Results

## Summary

✓ **Successfully processed full Ido Wikipedia dump**

### Output Statistics

- **Input**: `iowiki-latest-pages-articles.xml.bz2`
- **Output**: `data/processed/ido_corpus_full.txt`
- **Total sentences**: 392,333 lines
- **Suspicious templates found**: 28,328 unique template types

### Processing Details

**Ignored (as requested):**
- ✓ All `{{Biografio}}` templates
- ✓ All `{{#ifexist:...}}` templates  
- ✓ All images and file links
- ✓ Categories
- ✓ References sections
- ✓ HTML comments and tags

**Extracted:**
- Clean article text
- Proper handling of `[[wiki links]]` (kept visible text)
- Lowercase sentences for embedding training

## Sample Output

First few sentences from the corpus:

```
{{linguo 26 denaska parolanti en finlando nam ido esas "decendanto" di esperanto
pos sua komenco, ido recevis suporto di uli de la esperanto-komunitato
tamen, problemi eventis pos la subita morto en 1914 di un ek sua maxim influanta adepti, louis couturat
en 1928, otto jespersen abandonis ido-movado por developar sua propra linguo novial
```

## Suspicious Templates - Questions for Review

Found **28,328 unique template types** that weren't in the known-safe list.

### Major Categories Detected:

1. **Formatting/Numbers** (MANY - probably safe to remove):
   - `{{formatnum:...}}` - thousands of these for number formatting
   - `{{#expr:...}}` - mathematical expressions
   - `{{nowrap}}`, `{{small}}`, `{{center}}`

2. **Navigation/Metadata** (safe to remove):
   - `{{DEFAULTSORT:...}}`
   - `{{CompactTOC...}}`
   - `{{Bots}}`
   - `{{indexo}}`

3. **Dates/Time** (probably safe to remove):
   - `{{Agosto}}`, `{{Aprilo}}`, `{{Julio}}`, etc. (month names)
   - `{{1ma yarcento}}`, `{{20ma yarcento}}`, etc. (centuries)
   - `{{CURRENTTIME}}`

4. **Geographic/Administrative** (uncertain - might contain useful text):
   - `{{10 maxim grand urbi}}` (10 largest cities)
   - `{{20 maxim populoza}}` (20 most populous)
   - `{{Chef-urbi di Usana stati}}` (US state capitals)
   - `{{Chefministri di...}}` (Prime ministers of...)
   - `{{provinci di Finlando}}`, `{{regioni di Francia}}`, etc.

5. **Lists/Tables** (uncertain):
   - `{{liste horizontale}}`
   - `{{tabelo di sucedo}}`
   - `{{periodala tabelo}}`

6. **Content Markers** (probably safe to remove):
   - `{{nekompleta}}` (incomplete)
   - `{{tradukenda}}` (needs translation)
   - `{{stub}}`
   - `{{revizo}}` (revision)
   - `{{Bezonas tradukuro}}` (needs translation)

7. **Infoboxes/Structured Data** (uncertain - might have useful text):
   - `{{Aeroportuo}}` (airport)
   - `{{Auto}}` (car)
   - `{{koreanname}}`, `{{vi-nom}}` (name templates)

8. **Portal/Navigation** (safe to remove):
   - `{{portalaro}}`
   - `{{portalo kompozanto}}`
   - `{{videz anke}}` (see also)

## Recommendations

### Definitely Remove (cosmetic/metadata):
- All `{{formatnum:...}}` templates (number formatting)
- All date/century templates
- Navigation templates
- Stub/revision markers
- `{{DEFAULTSORT}}`, `{{Bots}}`, etc.

### Uncertain - Need Your Decision:

**Question 1**: Geographic list templates like `{{10 maxim grand urbi}}`, `{{Chef-urbi di Usana stati}}`
- These might expand to useful lists of city names
- Or they might just be navigation boxes
- **Keep or remove?**

**Question 2**: Infobox templates like `{{Aeroportuo}}`, `{{Auto}}`
- Might contain structured data with useful vocabulary
- Or might be mostly metadata
- **Keep or remove?**

**Question 3**: Name templates like `{{koreanname}}`, `{{vi-nom}}`
- Might contain alternative spellings/translations
- Or might be formatting only
- **Keep or remove?**

**Question 4**: List templates like `{{liste horizontale}}`, `{{tabelo di sucedo}}`
- Might contain useful content
- Or might be layout only
- **Keep or remove?**

## Next Steps

1. **Review the questions above** and decide which template categories to keep/remove
2. **Update the parser** with your decisions
3. **Re-run on full corpus** (takes ~2 minutes)
4. **Proceed with Esperanto Wikipedia** (similar process)
5. **Train FastText embeddings** on clean corpora

## Files Generated

- `data/processed/ido_corpus_full.txt` - Clean text corpus (392K sentences)
- `data/processed/suspicious_templates.txt` - Full list of 28K templates for review
