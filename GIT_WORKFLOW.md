# Git Workflow for Embedding Aligner Project

## 📋 What to Add to Git

This guide explains what files should be committed to version control and what should be excluded or stored elsewhere.

---

## ✅ Files to INCLUDE in Git

### 1. **Source Code** (Essential)
```bash
git add scripts/*.py
git add *.py
```

**Files:**
- `scripts/13_finetune_bert.py`
- `scripts/14_explore_bert_embeddings.py`
- `scripts/15_bert_crosslingual_alignment.py`
- Any other Python scripts

**Why:** Core functionality, must be versioned.

---

### 2. **Documentation** (Essential)
```bash
git add README.md
git add docs/*.md
git add GIT_WORKFLOW.md
```

**Files:**
- `README.md` - Main project documentation
- `docs/BERT_TRAINING_SUMMARY.md` - Training process details
- `docs/BERT_ALIGNMENT_COMPLETE.md` - Results and analysis
- `GIT_WORKFLOW.md` - This file

**Why:** Essential for understanding the project.

---

### 3. **Configuration Files** (Essential)
```bash
git add requirements.txt
git add .gitignore
git add setup.py  # if exists
```

**Files:**
- `requirements.txt` - Python dependencies
- `.gitignore` - Files to exclude from git
- Configuration files for deployment

**Why:** Needed to reproduce environment.

---

### 4. **Final Results** (Important)
```bash
git add results/bert_ido_epo_alignment/translation_candidates.json
git add results/bert_ido_epo_alignment/seed_dictionary.txt
git add results/bert_ido_epo_alignment/alignment_stats.json
```

**Files:**
- `translation_candidates.json` (3.8 MB) - 50,000 translation pairs
- `seed_dictionary.txt` (7 KB) - 1,022 cognate pairs
- `alignment_stats.json` (251 B) - Pipeline statistics

**Why:** These are the final output and relatively small (<5 MB).

---

### 5. **Small Vocabulary Files** (Optional but Recommended)
```bash
git add models/esperanto_clean__vocab.txt
git add models/esperanto_clean__stats.json
```

**Files:**
- Vocabulary lists (plain text)
- Statistics files (JSON)

**Why:** Small text files useful for reproduction.

---

## ⚠️ Files to MAYBE Include (Use Git LFS)

For files 10-100 MB, consider using **Git LFS** (Large File Storage):

```bash
# Install Git LFS
git lfs install

# Track large files
git lfs track "*.npz"
git lfs track "embeddings/*.npz"

# Add .gitattributes
git add .gitattributes

# Then add files
git add embeddings/ido_bert_vocab5k.npz  # 16 MB
```

**Files:**
- `embeddings/ido_bert_vocab5k.npz` (16 MB) - Pre-computed Ido embeddings

**Why:** Useful for quick starts, but can be regenerated.

---

## ❌ Files to EXCLUDE from Git

### 1. **Large Model Files** (>100 MB)

**DO NOT commit:**
```
models/bert-ido-finetuned-full/  (12+ GB total)
├── model.safetensors            (1.06 GB)
├── checkpoint-*/                 (multiple GB each)
└── optimizer.pt                  (2+ GB)
```

**Reason:** Too large for git. Use external storage:
- Hugging Face Model Hub
- AWS S3 / Google Cloud Storage
- Institutional file servers
- Provide download links in README

**Alternative:**
```bash
# Create a download script
cat > download_models.sh << 'EOF'
#!/bin/bash
echo "Downloading BERT model..."
# wget or curl from cloud storage
wget https://example.com/bert-ido-finetuned-full.tar.gz
tar -xzf bert-ido-finetuned-full.tar.gz
EOF
```

---

### 2. **Large Data Files**

**DO NOT commit:**
```
data/processed/ido_wikipedia_plus_wikisource.txt  (~50 MB)
data/raw/*                                          (various sizes)
```

**Reason:** Large and can be regenerated.

**Alternative:** Provide download instructions in README:
```markdown
## Download Corpus

```bash
# Download Ido Wikipedia
wget https://dumps.wikimedia.org/iowiki/latest/iowiki-latest-pages-articles.xml.bz2

# Process using WikiExtractor
python scripts/preprocess_wikipedia.py
```
```

---

### 3. **Binary Embeddings** (Large)

**DO NOT commit:**
```
results/bert_ido_epo_alignment/ido_aligned.npy      (15 MB)
results/bert_ido_epo_alignment/epo_aligned.npy      (15 MB)
results/bert_ido_epo_alignment/procrustes_W.npy     (2.3 MB)
```

**Reason:** Binary files that can be regenerated quickly.

---

### 4. **Logs and Temporary Files**

**DO NOT commit:**
```
logs/*.log
*.tmp
*.pyc
__pycache__/
.ipynb_checkpoints/
```

**Reason:** Temporary, generated, or user-specific.

---

### 5. **Virtual Environments**

**DO NOT commit:**
```
venv/
env/
.venv/
```

**Reason:** Environment-specific, regenerated from `requirements.txt`.

---

### 6. **Credentials and Keys**

**NEVER commit:**
```
*.pem
*.key
.env
secrets.json
aws_credentials.txt
```

**Reason:** Security risk.

---

## 📦 Recommended Git LFS Configuration

If you have Git LFS available:

```bash
# Initialize Git LFS
git lfs install

# Track specific large file types
git lfs track "*.npz"
git lfs track "*.npy"
git lfs track "*.model"

# Track specific directories
git lfs track "embeddings/**"
git lfs track "models/bert-ido-finetuned-full/**"

# Commit .gitattributes
git add .gitattributes
git commit -m "chore: configure Git LFS for large files"
```

---

## 📝 Recommended Commit Structure

### Initial Commit
```bash
# Add essential files
git add scripts/*.py
git add README.md
git add docs/*.md
git add requirements.txt
git add .gitignore
git add GIT_WORKFLOW.md

git commit -m "feat: initial Ido-Esperanto BERT alignment project

- Fine-tuning script for BERT on Ido corpus
- Embedding extraction and exploration tools
- Complete cross-lingual alignment pipeline
- Comprehensive documentation

Results: 50,000 translation pairs with 100% validation accuracy"
```

### Add Results
```bash
# Add output files
git add results/bert_ido_epo_alignment/*.json
git add results/bert_ido_epo_alignment/*.txt

git commit -m "feat: add BERT alignment results

- 50,000 Ido↔Esperanto translation pairs
- 1,022 automatic cognates seed dictionary
- 100% precision on validation set"
```

### Add Pre-computed Embeddings (if using Git LFS)
```bash
git lfs track "embeddings/*.npz"
git add .gitattributes
git add embeddings/ido_bert_vocab5k.npz

git commit -m "feat: add pre-computed Ido embeddings

- 5,000 most frequent Ido words
- Extracted from fine-tuned XLM-RoBERTa
- Enables quick pipeline execution without BERT model"
```

---

## 🌐 External Storage Options

For files >100 MB, use external storage:

### Option 1: Hugging Face Model Hub
```bash
# Upload model to Hugging Face
huggingface-cli login
huggingface-cli repo create bert-ido-finetuned
huggingface-cli upload bert-ido-finetuned models/bert-ido-finetuned-full/
```

Then in README:
```markdown
## Download Model

```bash
pip install huggingface_hub
python -c "from huggingface_hub import snapshot_download; snapshot_download('username/bert-ido-finetuned', local_dir='models/bert-ido-finetuned-full')"
```
```

### Option 2: Zenodo (Academic/Research)
- Upload to Zenodo for DOI and permanent storage
- Free, citable, long-term preservation
- Link in README

### Option 3: Cloud Storage (S3, GCS, Azure)
```bash
# Upload to S3
aws s3 cp models/bert-ido-finetuned-full/ s3://bucket/bert-ido/ --recursive

# Download instructions in README
aws s3 sync s3://bucket/bert-ido/ models/bert-ido-finetuned-full/
```

---

## 📊 File Size Summary

| Category | Size | Include? | Method |
|----------|------|----------|--------|
| Scripts | < 1 MB | ✅ Yes | Direct commit |
| Documentation | < 1 MB | ✅ Yes | Direct commit |
| Config files | < 100 KB | ✅ Yes | Direct commit |
| Results (JSON) | 3.8 MB | ✅ Yes | Direct commit |
| Seed dictionary | 7 KB | ✅ Yes | Direct commit |
| Embeddings (.npz) | 16 MB | ⚠️ Maybe | Git LFS or exclude |
| Binary arrays (.npy) | 15 MB each | ❌ No | Regenerate |
| BERT model | 12+ GB | ❌ No | External storage |
| Corpus data | 50+ MB | ❌ No | Download script |
| Logs | Variable | ❌ No | Exclude (.gitignore) |

---

## 🔄 Complete Workflow Example

```bash
# 1. Stage essential files
git add scripts/*.py
git add README.md docs/*.md GIT_WORKFLOW.md
git add requirements.txt .gitignore
git add results/bert_ido_epo_alignment/*.json
git add results/bert_ido_epo_alignment/*.txt

# 2. Check what will be committed
git status
du -sh $(git ls-files --cached)

# 3. Commit with descriptive message
git commit -m "feat: complete BERT-based Ido-Esperanto alignment

Core contributions:
- BERT fine-tuning pipeline for Ido corpus
- Cross-lingual embedding alignment using Procrustes
- Automatic cognate discovery (1,022 pairs)
- Translation candidate generation (50,000 pairs)
- 100% validation accuracy

Files included:
- Complete source code and scripts
- Comprehensive documentation
- Final translation results (JSON)
- Seed dictionary

Large files (models, embeddings) available separately:
See README.md for download instructions"

# 4. Push to remote
git push origin main
```

---

## ✅ Final Checklist

Before committing:

- [ ] All scripts are documented and working
- [ ] README.md is complete and accurate
- [ ] requirements.txt includes all dependencies
- [ ] .gitignore excludes large/sensitive files
- [ ] Results files are included (< 5 MB)
- [ ] Large files have external storage links
- [ ] No credentials or keys in repository
- [ ] Commit messages are descriptive
- [ ] Total repository size < 20 MB (without Git LFS)

---

**Recommended Total Git Repository Size:** **< 20 MB** (excluding Git LFS)

This keeps cloning fast and hosting free on platforms like GitHub/GitLab.

