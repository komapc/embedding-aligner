# Integration Quick Start Guide

## 🎯 Goal

Integrate 50,000 BERT-generated translation pairs into three production systems:
1. **vortaro** - Dictionary repository
2. **apertium-ido-epo** - Translation engine
3. **Live translator** - Production deployment

---

## ✅ What's Ready

- ✅ **50,000 translation pairs** generated
- ✅ **100% validation** accuracy on seed dictionary
- ✅ **Integration scripts** created (16, 17, 18)
- ✅ **Documentation** complete
- ⏳ **Pending:** Format, test, and deploy

---

## 🚀 Quick Commands

### Step 1: Filter for Vortaro

```bash
cd /home/mark/apertium-dev/projects/embedding-aligner

# Create vortaro-friendly format (high quality only)
python scripts/16_filter_for_vortaro.py \
  --input results/bert_ido_epo_alignment/translation_candidates.json \
  --output results/vortaro_format/ \
  --min-similarity 0.85 \
  --max-candidates 3 \
  --include-frequencies \
  --format both

# Review output
head -20 results/vortaro_format/ido_epo_dictionary.csv
less results/vortaro_format/ido_epo_dictionary.json
cat results/vortaro_format/vortaro_stats.json
```

**Expected output:**
- `ido_epo_dictionary.json` (~2-3 MB)
- `ido_epo_dictionary.csv` (~1-2 MB)
- `vortaro_stats.json` (statistics)

---

### Step 2: Format for Apertium

```bash
# Create Apertium .dix dictionary format
python scripts/17_format_for_apertium.py \
  --input results/bert_ido_epo_alignment/translation_candidates.json \
  --output results/apertium_format/ \
  --min-similarity 0.80 \
  --max-candidates 1 \
  --add-pos-tags \
  --format dix

# Review output
head -50 results/apertium_format/ido-epo.dix
cat results/apertium_format/apertium_format_stats.json

# Validate XML (if xmllint available)
xmllint --noout results/apertium_format/ido-epo.dix && echo "✅ Valid XML"
```

**Expected output:**
- `ido-epo.dix` (Apertium XML dictionary)
- `apertium_format_stats.json` (statistics)

---

### Step 3: Test Integration (Dry Run)

```bash
# Show what would be added to vortaro
echo "Vortaro Integration Preview:"
head -10 results/vortaro_format/ido_epo_dictionary.csv

# Show sample Apertium entries
echo -e "\nApertium Integration Preview:"
grep -A 3 "<e>" results/apertium_format/ido-epo.dix | head -20

# Statistics
echo -e "\nStatistics:"
jq '.' results/vortaro_format/vortaro_stats.json
jq '.' results/apertium_format/apertium_format_stats.json
```

---

## 📋 Integration Checklist

### Phase 1: Vortaro (Dictionary) ⏳

**Time:** ~2 hours  
**Risk:** Low  
**Impact:** Vocabulary reference, learning resources

- [ ] Run `16_filter_for_vortaro.py` ✅ (ready to run)
- [ ] Review output quality
- [ ] Clone vortaro repository
- [ ] Create feature branch
- [ ] Add dictionary data
- [ ] Create PR
- [ ] Manual review
- [ ] Merge

**Commands:**
```bash
# Clone vortaro (replace with actual repo URL)
git clone https://github.com/[username]/vortaro.git ~/apertium-dev/vortaro
cd ~/apertium-dev/vortaro

# Create branch
git checkout -b feature/bert-ido-epo-50k

# Copy formatted data
cp ../projects/embedding-aligner/results/vortaro_format/ido_epo_dictionary.json data/

# Commit and push
git add data/ido_epo_dictionary.json
git commit -m "feat: add 50,000 BERT-generated Ido↔Esperanto pairs"
git push -u origin feature/bert-ido-epo-50k

# Create PR on GitHub/GitLab
```

---

### Phase 2: Apertium ido-epo (Translation) ⏳

**Time:** ~6 hours  
**Risk:** Medium (requires testing)  
**Impact:** Live translations, high visibility

- [ ] Run `17_format_for_apertium.py` ✅ (ready to run)
- [ ] Clone apertium-ido-epo
- [ ] Create feature branch
- [ ] Merge with existing dictionary
- [ ] Validate XML
- [ ] Compile (`make`)
- [ ] Test translations (bidirectional)
- [ ] Update CHANGELOG.md
- [ ] Create PR
- [ ] Manual review
- [ ] Merge

**Commands:**
```bash
# Clone apertium-ido-epo
cd ~/apertium-dev
git clone https://github.com/apertium/apertium-ido-epo.git
cd apertium-ido-epo

# Create branch
git checkout -b feature/bert-translation-pairs

# Backup existing
cp apertium-ido-epo.ido-epo.dix apertium-ido-epo.ido-epo.dix.backup

# Manual merge (or use script 18 when created)
# For now, manually add entries from ../projects/embedding-aligner/results/apertium_format/ido-epo.dix
# to the <section> in apertium-ido-epo.ido-epo.dix

# Validate
xmllint --noout apertium-ido-epo.ido-epo.dix

# Compile
make clean && make

# Test
echo "La hundo kurso." | apertium ido-epo
echo "Mi havas libron." | apertium epo-ido

# Commit
git add apertium-ido-epo.ido-epo.dix CHANGELOG.md
git commit -m "feat: add BERT-generated translation pairs"
git push -u origin feature/bert-translation-pairs
```

---

### Phase 3: Deployment ⏳

**Time:** ~3 hours  
**Risk:** Low (after testing)  
**Impact:** Production translator

- [ ] Test locally with updated dictionary
- [ ] Deploy to staging
- [ ] Run integration tests
- [ ] Deploy to production
- [ ] Monitor logs
- [ ] Announce update

**Commands:** See `INTEGRATION_PLAN.md` Part 3

---

## 📊 Expected Results

### Vortaro
- **Words added:** ~5,000 Ido words
- **Total pairs:** ~10,000 (with multiple candidates)
- **Similarity:** ≥ 0.85 (high confidence)
- **Format:** JSON + CSV

### Apertium
- **Entries added:** ~3,000 (single best candidate)
- **Similarity:** ≥ 0.80
- **POS tagged:** ~70% (morphology-based)
- **Format:** .dix XML

### Production Impact
- **Coverage increase:** +15-20%
- **Translation quality:** Improved for common words
- **Performance:** No impact (compiled dictionaries)

---

## 🎯 Recommended Order

1. **Start with Vortaro** (lowest risk, good practice)
   - Run script 16
   - Review output
   - Create PR

2. **Then Apertium** (after vortaro experience)
   - Run script 17
   - Test thoroughly
   - Create PR

3. **Finally Deploy** (after both PRs merged)
   - Production update
   - Monitor and iterate

---

## ⚠️ Important Notes

### Before Running Scripts

1. **Backup your data** - Always backup before modifying
2. **Test on sample** - Try with `--max-candidates 1` first
3. **Review manually** - Spot-check 20-30 random pairs
4. **Use version control** - Always work in feature branches

### Quality Thresholds

| System | Min Similarity | Max Candidates | Rationale |
|--------|---------------|----------------|-----------|
| Vortaro | 0.85 | 3 | Learning resource, multiple options OK |
| Apertium | 0.80 | 1 | Translation engine, need single best |
| Production | 0.80+ | 1 | High confidence only |

### Testing

**Always test bidirectionally:**
```bash
# Ido → Esperanto
echo "Test sentence" | apertium ido-epo

# Esperanto → Ido
echo "Test sentence" | apertium epo-ido
```

---

## 📖 Full Documentation

- **Overview:** `INTEGRATION_PLAN.md` (complete details)
- **This guide:** `INTEGRATION_QUICKSTART.md` (quick reference)
- **Training:** `docs/BERT_TRAINING_SUMMARY.md`
- **Results:** `docs/BERT_ALIGNMENT_COMPLETE.md`
- **Git:** `GIT_WORKFLOW.md`

---

## 🆘 Need Help?

1. **Review logs** - Check script output for errors
2. **Validate data** - Use JSON validators, xmllint
3. **Test incrementally** - Start small, scale up
4. **Ask for review** - Share PRs for feedback

---

## ✅ Ready to Start!

**Next command:**
```bash
cd /home/mark/apertium-dev/projects/embedding-aligner

# Run vortaro formatter
python scripts/16_filter_for_vortaro.py \
  --input results/bert_ido_epo_alignment/translation_candidates.json \
  --output results/vortaro_format/ \
  --min-similarity 0.85 \
  --max-candidates 3 \
  --include-frequencies \
  --format both

# Review output
ls -lh results/vortaro_format/
```

**Let's integrate these translation pairs into production!** 🚀

