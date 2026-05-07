#!/usr/bin/env python3
"""Train an IO↔EO cross-encoder for re-ranking BERT bi-encoder candidates.

Architecture: XLM-RoBERTa-base + sequence-classification head (binary).
Input format: `<s> {io_lemma} </s></s> {eo_term} </s>` — the standard
sentence-pair encoding for RoBERTa-family models. Labels: 1 = translation,
0 = not.

Pipeline:
  1. Load Wiktionary + Wikipedia-langlink positives via `lib/seed_pairs`.
  2. Build the full `known_golds` set (covering polysemy) from the same
     sources so negative selection is leak-free.
  3. Stratified-deterministic split → 200 held-out positives committed to
     `data/cross_encoder_heldout.jsonl` for stable evaluation across runs.
  4. Assemble hard + surface negatives for the train remainder.
  5. Tokenize and feed `transformers.Trainer` for 3 epochs.
  6. Eval on held-out: F1, AUC, accuracy.

Outputs:
  models/cross-encoder-io-eo/   — checkpointed HF model + tokenizer
  data/cross_encoder_heldout.jsonl — committed eval set
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib.seed_pairs import (  # noqa: E402
    Pair,
    assemble_hard_negatives,
    assemble_surface_negatives,
    dump_heldout_jsonl,
    load_all_known_golds,
    load_all_positives,
    load_candidate_io_set,
    stratified_train_heldout_split,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def build_dataset(pairs: list[Pair], tokenizer, max_length: int = 64):
    """Tokenize (io, eo) pairs as RoBERTa sentence-pairs. Returns a HF
    Dataset. `max_length=64` is plenty: lemmas + EO terms are 1–4 tokens
    each."""
    from datasets import Dataset
    ios = [p.io for p in pairs]
    eos = [p.eo for p in pairs]
    enc = tokenizer(ios, eos, truncation=True, max_length=max_length,
                    padding=False, return_token_type_ids=False)
    enc['labels'] = [p.label for p in pairs]
    return Dataset.from_dict(enc)


def compute_metrics(eval_pred):
    """F1, AUC, accuracy for the held-out set."""
    import numpy as np
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
    logits, labels = eval_pred
    probs = np.exp(logits[:, 1]) / np.exp(logits).sum(axis=1)
    preds = (probs >= 0.5).astype(int)
    return {
        'accuracy': accuracy_score(labels, preds),
        'f1': f1_score(labels, preds),
        'auc': roc_auc_score(labels, probs),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent.parent
    extr = here.parents[1] / 'extractor'
    ap.add_argument('--bilingual-raw', type=Path,
                    default=extr / 'work' / 'bilingual_raw.json')
    ap.add_argument('--langlinks', type=Path,
                    default=extr / 'work' / 'io_eo_langlinks.json')
    ap.add_argument('--candidates', type=Path,
                    default=here / 'results' / 'bert_ido_epo_alignment' / 'translation_candidates.json')
    ap.add_argument('--eo-vocab', type=Path,
                    default=here / 'data' / 'esperanto_vocabulary.txt')
    ap.add_argument('--heldout-out', type=Path,
                    default=here / 'data' / 'cross_encoder_heldout.jsonl')
    ap.add_argument('--model-out', type=Path,
                    default=here / 'models' / 'cross-encoder-io-eo')
    ap.add_argument('--base-model', default='xlm-roberta-base')
    ap.add_argument('--heldout-size', type=int, default=200)
    ap.add_argument('--hard-neg-per-pos', type=int, default=4)
    ap.add_argument('--surface-neg-per-pos', type=int, default=1)
    ap.add_argument('--epochs', type=int, default=3)
    ap.add_argument('--batch-size', type=int, default=32)
    ap.add_argument('--learning-rate', type=float, default=2e-5)
    ap.add_argument('--max-length', type=int, default=64)
    ap.add_argument('--seed', type=int, default=42)
    ap.add_argument('--dump-only', action='store_true',
                    help='Assemble pairs + write held-out file, then exit. Use to '
                         'regenerate `data/cross_encoder_heldout.jsonl` on CPU '
                         'without running GPU training.')
    args = ap.parse_args()

    # Stage 1: assemble train + heldout sets
    positives = load_all_positives(args.bilingual_raw, args.langlinks)
    known_golds = load_all_known_golds(args.bilingual_raw, args.langlinks)
    eligible = load_candidate_io_set(args.candidates)
    train_pos, heldout_pos = stratified_train_heldout_split(
        positives, heldout_size=args.heldout_size, seed=args.seed,
        eligible_io_set=eligible,
    )

    # Persist heldout artifact early — it doesn't depend on negative assembly
    # and is the only thing produced when running with `--dump-only`.
    dump_heldout_jsonl(heldout_pos, args.candidates, args.heldout_out,
                       neg_per_pos=args.hard_neg_per_pos)

    if args.dump_only:
        logger.info("--dump-only set: skipping negative assembly + training. "
                    "Heldout written to %s", args.heldout_out)
        return

    logger.info("Assembling negatives...")
    t0 = time.time()
    hard_neg = assemble_hard_negatives(
        train_pos, args.candidates, known_golds, neg_per_pos=args.hard_neg_per_pos,
    )
    surf_neg = assemble_surface_negatives(
        train_pos, args.eo_vocab, known_golds, neg_per_pos=args.surface_neg_per_pos,
        seed=args.seed,
    )
    logger.info("Negatives assembled in %.1fs", time.time() - t0)

    train_pairs = train_pos + hard_neg + surf_neg
    # Held-out set: heldout positives + their hard negatives (paired 1:4)
    heldout_hard = assemble_hard_negatives(
        heldout_pos, args.candidates, known_golds, neg_per_pos=args.hard_neg_per_pos,
    )
    eval_pairs = heldout_pos + heldout_hard

    logger.info("Train: %d (pos=%d hard=%d surf=%d) | Eval: %d (pos=%d neg=%d)",
                len(train_pairs), len(train_pos), len(hard_neg), len(surf_neg),
                len(eval_pairs), len(heldout_pos), len(heldout_hard))

    # Stage 2: train
    import torch
    from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                              DataCollatorWithPadding, Trainer, TrainingArguments)

    logger.info("Loading base model: %s", args.base_model)
    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.base_model, num_labels=2,
    )

    train_ds = build_dataset(train_pairs, tokenizer, args.max_length)
    eval_ds = build_dataset(eval_pairs, tokenizer, args.max_length)
    train_ds = train_ds.shuffle(seed=args.seed)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info("Training device: %s", device)
    if device == "cpu":
        logger.warning("CPU training will be very slow — use GPU (Colab T4 / g4dn.xlarge)")

    args.model_out.mkdir(parents=True, exist_ok=True)
    training_args = TrainingArguments(
        output_dir=str(args.model_out),
        overwrite_output_dir=True,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=100,
        eval_strategy='epoch',
        save_strategy='epoch',
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model='f1',
        fp16=(device == 'cuda'),
        report_to='none',
        seed=args.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    t0 = time.time()
    trainer.train()
    logger.info("Training complete in %.1f min", (time.time() - t0) / 60)

    final = trainer.evaluate()
    logger.info("Final held-out metrics: %s", final)

    trainer.save_model(str(args.model_out))
    tokenizer.save_pretrained(str(args.model_out))
    logger.info("Saved model to %s", args.model_out)


if __name__ == '__main__':
    main()
