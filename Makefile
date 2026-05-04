PY=python3
ROOT=../..
EXTRACTOR=$(ROOT)/extractor

# Paths
CORPUS=data/ido_corpus.txt
MODEL_DIR=models/bert-ido-finetuned-full
RAW_VOCAB=data/ido_vocabulary.txt
FILTERED_VOCAB=data/ido_vocabulary_filtered.txt
EMBEDDINGS=embeddings/ido_bert_filtered.npz
EPO_VOCAB=models/esperanto_clean__vocab.txt
EPO_MODEL=models/esperanto_clean__300d.npy
IO_PROCESSED=$(EXTRACTOR)/work/io_wiktionary_processed.json
IDO_AUTOMORF=$(ROOT)/apertium-ido/ido.automorf.bin
ALIGNMENT_OUT=results/bert_ido_epo_alignment
CANDIDATES=$(ALIGNMENT_OUT)/translation_candidates.json
BERT_SOURCE=$(EXTRACTOR)/data/sources/source_bert_embeddings.json

.PHONY: all source_bert_embeddings align extract preprocess-vocab finetune-bert help

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

$(EMBEDDINGS): $(MODEL_DIR) $(FILTERED_VOCAB)
	$(PY) scripts/14_extract_bert_embeddings.py \
	  --model $(MODEL_DIR) \
	  --vocab $(FILTERED_VOCAB) \
	  --output $(EMBEDDINGS)

# Preprocess raw Ido vocab: drop junk shapes, lemmatize via Apertium morphology
# (collapse kreas/kreis/kreado -> krear), and drop words already covered by
# io.wiktionary. BERT focuses on the long tail.
$(FILTERED_VOCAB): $(RAW_VOCAB) $(IO_PROCESSED) $(IDO_AUTOMORF)
	$(PY) scripts/preprocess_vocab.py \
	  --input $(RAW_VOCAB) \
	  --output $(FILTERED_VOCAB) \
	  --io-processed $(IO_PROCESSED) \
	  --ido-automorf $(IDO_AUTOMORF)

preprocess-vocab: $(FILTERED_VOCAB)

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
