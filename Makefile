PY=python3
ROOT=../..
EXTRACTOR=$(ROOT)/extractor

# Paths
CORPUS=data/ido_corpus.txt
MODEL_DIR=models/bert-ido-finetuned-full
EMBEDDINGS=embeddings/ido_bert_vocab5k.npz
EPO_VOCAB=models/esperanto_clean__vocab.txt
EPO_MODEL=models/esperanto_clean__300d.npy
ALIGNMENT_OUT=results/bert_ido_epo_alignment
CANDIDATES=$(ALIGNMENT_OUT)/translation_candidates.json
BERT_SOURCE=$(EXTRACTOR)/data/sources/source_bert_embeddings.json

.PHONY: all source_bert_embeddings align extract finetune-bert help

all: source_bert_embeddings

# Full pipeline: align → convert → write to extractor source
source_bert_embeddings: $(BERT_SOURCE)

$(BERT_SOURCE): $(CANDIDATES)
	$(PY) scripts/20_convert_to_unified_format.py \
	  --input $(CANDIDATES) \
	  --output $(BERT_SOURCE)
	@echo "✓ Updated $(BERT_SOURCE)"

$(CANDIDATES): $(EMBEDDINGS) $(EPO_VOCAB) $(EPO_MODEL)
	$(PY) scripts/15_bert_crosslingual_alignment.py \
	  --bert-model $(MODEL_DIR) \
	  --ido-embeddings $(EMBEDDINGS) \
	  --epo-vocab $(EPO_VOCAB) \
	  --epo-model $(EPO_MODEL) \
	  --output-dir $(ALIGNMENT_OUT)

$(EMBEDDINGS): $(MODEL_DIR)
	$(PY) scripts/14_extract_bert_embeddings.py \
	  --model $(MODEL_DIR) \
	  --vocab data/ido_vocab.txt \
	  --output $(EMBEDDINGS)

# Expensive GPU step — only run when retraining is needed (skip with existing model)
finetune-bert:
	$(PY) scripts/13_finetune_bert.py \
	  --corpus $(CORPUS) \
	  --output $(MODEL_DIR)

help:
	@echo "Targets:"
	@echo "  source_bert_embeddings  Build and export BERT source to extractor (default)"
	@echo "  align                   Run cross-lingual alignment (step 15)"
	@echo "  extract                 Extract BERT embeddings from fine-tuned model (step 14)"
	@echo "  finetune-bert           Fine-tune BERT on Ido corpus (step 13, GPU-intensive)"
	@echo ""
	@echo "Output: $(BERT_SOURCE)"
