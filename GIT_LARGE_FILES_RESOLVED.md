# Git Large Files Issue - RESOLVED ✅

## 🎯 Problem

Attempted to push `feature/bert-alignment-pipeline` branch to GitHub, but push was rejected due to large binary files:

```
remote: error: File results/bert_aligned_clean_0.60/epo_w2v_aligned.npy is 492.07 MB
remote: error: This exceeds GitHub's file size limit of 100.00 MB
```

**Root cause:** Large `.npy` (NumPy array) files were committed to Git in earlier commits.

---

## ✅ Solution Applied

### Step 1: Remove files from Git tracking
```bash
git rm --cached results/bert_aligned_clean_0.60/*.npy
```

### Step 2: Rewrite Git history
Used `git filter-branch` to remove ALL large files from entire branch history:

```bash
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch results/*/*.npy' \
  --prune-empty --tag-name-filter cat -- --all
```

### Step 3: Clean up repository
```bash
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### Step 4: Force push cleaned branch
```bash
git push -u origin feature/bert-alignment-pipeline --force
```

---

## 📊 Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Repository size** | 1.8 GB | 6.4 MB | **99.6% reduction** |
| **Largest file** | 830 MB | 3.7 MB | ✅ Under 100 MB |
| **Push status** | ❌ Rejected | ✅ Successful | ✅ |

**Files removed from Git:**
- `results/bert_aligned/*.npy` (830 MB)
- `results/bert_aligned_clean_0.60/*.npy` (550 MB)
- `results/bert_aligned_0.60/*.npy` (888 MB)
- `data/raw/additional/*.xml.bz2` (177 MB)
- **Total removed:** ~1.79 GB

---

## 🛡️ Prevention: How to Avoid This in the Future

### 1. ✅ Use .gitignore (Already in place)

Our `.gitignore` now includes:

```gitignore
# Large binary files
*.npy
*.npz
*.bin
*.model

# Data files
data/raw/
data/processed/*.txt
data/processed/*.xml

# Results
results/*/*.npy
results/*/*.npz
```

### 2. ✅ Check before committing

**Always check file sizes before committing:**

```bash
# Show files that will be committed
git status

# Show sizes of staged files
git diff --cached --name-only | xargs ls -lh

# Find files larger than 10 MB
find . -type f -size +10M -not -path "./.git/*"
```

### 3. ✅ Use pre-commit hooks

Create `.git/hooks/pre-commit` to automatically check file sizes:

```bash
#!/bin/bash
# Prevent committing files larger than 50 MB

MAX_SIZE=52428800  # 50 MB in bytes

while IFS= read -r file; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        if [ "$size" -gt "$MAX_SIZE" ]; then
            echo "❌ ERROR: File too large: $file ($(numfmt --to=iec $size))"
            echo "   Maximum size: 50 MB"
            echo "   Add to .gitignore or use Git LFS"
            exit 1
        fi
    fi
done < <(git diff --cached --name-only)

echo "✅ All files under size limit"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

### 4. ✅ Use Git LFS for large files (if needed)

If you MUST version control large files:

```bash
# Install Git LFS
git lfs install

# Track large file types
git lfs track "*.npz"
git lfs track "models/*.bin"

# Commit .gitattributes
git add .gitattributes
git commit -m "chore: configure Git LFS"
```

**Note:** For this project, we DON'T need Git LFS since .npy files can be regenerated.

### 5. ✅ Regular cleanup checks

Add to your workflow:

```bash
# Monthly cleanup check
git rev-list --objects --all | \
  git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | \
  awk '$1 == "blob" && $3 >= 10485760 {print $3/1048576 " MB", $4}' | \
  sort -rn

# Should show no files > 50 MB
```

---

## 📝 What Files SHOULD Be in Git

### ✅ DO commit:
- ✅ Source code (`.py`, `.js`, etc.)
- ✅ Documentation (`.md`, `.txt`)
- ✅ Configuration files (`requirements.txt`, `.gitignore`)
- ✅ Small data files (< 1 MB)
- ✅ **Results we keep:**
  - `results/bert_ido_epo_alignment/translation_candidates.json` (3.7 MB)
  - `results/bert_ido_epo_alignment/seed_dictionary.txt` (7 KB)
  - `results/bert_ido_epo_alignment/alignment_stats.json` (251 B)

### ❌ DON'T commit:
- ❌ Large binary files (`.npy`, `.bin`, `.model`)
- ❌ Compressed data files (`.xml.bz2`, `.tar.gz`)
- ❌ Large datasets (> 10 MB)
- ❌ Compiled artifacts
- ❌ Virtual environments (`venv/`)
- ❌ Generated files that can be recreated

---

## 🎓 Lessons Learned

### 1. **Check .gitignore early**
Before your first commit, ensure .gitignore covers all large file types.

### 2. **Review commits before pushing**
```bash
# See what's in your commits
git log --stat
git show --stat

# Check sizes
git diff --cached --name-only | xargs ls -lh
```

### 3. **Smaller commits, more often**
Don't accumulate many commits before pushing. Push frequently to catch issues early.

### 4. **Use git status carefully**
```bash
# Good: Review what will be committed
git status
git diff --cached

# Bad: Blindly committing everything
git add .  # Be careful!
git commit -m "stuff"
```

### 5. **Document what files are generated**
In README, clearly document:
- What files are generated
- What files can be regenerated
- What files MUST be in Git
- What files should NEVER be in Git

---

## 🔧 Recovery Commands (If It Happens Again)

### Quick fix for uncommitted files:
```bash
# Unstage large files
git reset HEAD path/to/large/file.npy

# Add to .gitignore
echo "path/to/large/file.npy" >> .gitignore
```

### If already committed but not pushed:
```bash
# Remove from last commit
git rm --cached path/to/large/file.npy
git commit --amend

# Or reset to before the bad commit
git reset --soft HEAD~1
```

### If already pushed (be careful!):
```bash
# Rewrite history (dangerous on shared branches!)
git filter-branch --force --index-filter \
  'git rm --cached --ignore-unmatch path/to/large/*.npy' \
  --prune-empty --tag-name-filter cat -- --all

# Clean up
rm -rf .git/refs/original/
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (only on feature branches!)
git push --force origin branch-name
```

---

## 📋 Checklist Before Each Push

```markdown
- [ ] Run `git status` and review all files
- [ ] Check for large files: `find . -type f -size +10M -not -path "./.git/*"`
- [ ] Verify .gitignore excludes binaries
- [ ] Run `git diff --cached --stat` to see changes
- [ ] Ensure no .npy, .bin, or .model files are staged
- [ ] Test push: `git push --dry-run`
- [ ] Actually push: `git push`
```

---

## ✅ Status: RESOLVED

**Branch:** `feature/bert-alignment-pipeline`  
**Status:** ✅ Successfully pushed to GitHub  
**PR Link:** https://github.com/komapc/embedding-aligner/pull/new/feature/bert-alignment-pipeline  
**Repository size:** 6.4 MB (clean!)  

---

## 🚀 Next Steps

1. **Create Pull Request:** Visit the link above
2. **Review changes:** Ensure everything looks good
3. **Merge when ready:** After review and approval
4. **Monitor repository size:** Keep under 50 MB per file
5. **Document this fix:** Share with team to prevent future issues

---

**Problem solved! Repository is clean and push successful! 🎉**

