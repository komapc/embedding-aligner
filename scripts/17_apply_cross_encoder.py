#!/usr/bin/env python3
"""Apply the trained IO↔EO cross-encoder to BERT bi-encoder candidates.

Closes the gap between `16_train_cross_encoder.py` (which trains the model)
and `20_convert_to_unified_format.py` (which only similarity-thresholds): this
step re-scores every (io_lemma, eo_candidate) pair from the bi-encoder
candidate file with the cross-encoder and keeps the ones it judges true
translations — including non-cognate pairs the build-time cognate guard would
otherwise drop.

Output is a filtered candidate file in the SAME schema as the bi-encoder's
`translation_candidates.json` (`{io: [{epo, similarity, ce_score}, ...]}`),
so it is a drop-in for `20_convert_to_unified_format.py --min-similarity 0.0`.

Runs on GPU when available (one forward pass per pair; ~hundreds of thousands
of pairs), falls back to CPU.

Usage:
    python3 scripts/17_apply_cross_encoder.py \
        --model models/cross-encoder-io-eo \
        --candidates results/bert_ido_epo_alignment/translation_candidates.json \
        --output results/bert_ido_epo_alignment/translation_candidates_ce.json \
        --threshold 0.5 --top-k 3
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_candidates(path: Path) -> dict[str, list[dict]]:
    data = json.load(open(path, encoding='utf-8'))
    # tolerate {io:[...]} dict or [{io, candidates:[...]}] list
    if isinstance(data, dict):
        return data
    out = {}
    for rec in data:
        out[rec['io']] = rec.get('candidates') or rec.get('epo') or []
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent.parent
    ap.add_argument('--model', type=Path, default=here / 'models' / 'cross-encoder-io-eo')
    ap.add_argument('--candidates', type=Path,
                    default=here / 'results' / 'bert_ido_epo_alignment' / 'translation_candidates.json')
    ap.add_argument('--output', type=Path,
                    default=here / 'results' / 'bert_ido_epo_alignment' / 'translation_candidates_ce.json')
    ap.add_argument('--threshold', type=float, default=0.5,
                    help='Keep pairs with cross-encoder P(translation) >= this.')
    ap.add_argument('--top-k', type=int, default=3,
                    help='Keep at most this many candidates per lemma (by ce_score).')
    ap.add_argument('--batch-size', type=int, default=128)
    ap.add_argument('--max-length', type=int, default=64)
    args = ap.parse_args()

    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification

    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    logger.info("Device: %s", device)
    if device == 'cpu':
        logger.warning("CPU inference over all pairs is slow — GPU (Colab T4) recommended.")

    tokenizer = AutoTokenizer.from_pretrained(str(args.model))
    model = AutoModelForSequenceClassification.from_pretrained(str(args.model)).to(device)
    model.eval()

    cands = load_candidates(args.candidates)
    # Flatten to (io, eo, similarity) for batched scoring.
    flat: list[tuple[str, str, float]] = []
    for io, lst in cands.items():
        for c in lst:
            flat.append((io, c['epo'], c.get('similarity', 0.0)))
    logger.info("Scoring %d pairs across %d lemmas", len(flat), len(cands))

    scores: list[float] = []
    with torch.no_grad():
        for i in range(0, len(flat), args.batch_size):
            batch = flat[i:i + args.batch_size]
            enc = tokenizer([io for io, _, _ in batch],
                            [eo for _, eo, _ in batch],
                            truncation=True, max_length=args.max_length,
                            padding=True, return_token_type_ids=False,
                            return_tensors='pt').to(device)
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=1)[:, 1]
            scores.extend(probs.cpu().tolist())
            if (i // args.batch_size) % 100 == 0:
                logger.info("  %d/%d pairs scored", i, len(flat))

    # Regroup, threshold, top-k.
    out: dict[str, list[dict]] = {}
    kept = 0
    for (io, eo, sim), ce in zip(flat, scores):
        if ce < args.threshold:
            continue
        out.setdefault(io, []).append({'epo': eo, 'similarity': sim, 'ce_score': round(ce, 4)})
    for io in list(out):
        out[io].sort(key=lambda c: c['ce_score'], reverse=True)
        out[io] = out[io][:args.top_k]
        kept += len(out[io])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(args.output, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    logger.info("Kept %d pairs across %d lemmas (threshold=%.2f, top_k=%d)",
                kept, len(out), args.threshold, args.top_k)
    logger.info("Wrote %s", args.output)


if __name__ == '__main__':
    main()
