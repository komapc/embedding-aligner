#!/usr/bin/env python3
"""'Done-correctly' BLI test: fastText (subword, Ido) + word2vec (EO) via Procrustes.

The canonical low-resource bilingual-lexicon-induction setup, replacing the
isolated-BERT-word-vectors that gave 6% non-cognate precision:
  - Ido side: fastText trained on the Ido corpus (subwords model Ido morphology).
  - EO side : the existing 430k-word `esperanto_clean__300d.npy` (no 10k ceiling).
  - Align with a GOLD Wiktionary seed; measure precision split by cognate vs
    NON-cognate — the latter is the only number that matters (cognates are
    already handled by the build-time guard).

Run: venv/bin/python experiments/eval_bli_fasttext.py
"""
from __future__ import annotations

import json
import logging
import random
from pathlib import Path

import numpy as np
from scipy.linalg import orthogonal_procrustes

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent.parent
CORPUS = HERE / 'data' / 'processed' / 'ido_finetune_corpus.txt'
EO_NPY = HERE / 'models' / 'esperanto_clean__300d.npy'
EO_VOCAB = HERE / 'models' / 'esperanto_clean__vocab.txt'
IO_WIKT = HERE.parents[1] / 'extractor' / 'work' / 'io_wiktionary_processed.json'
FT_CACHE = HERE / 'experiments' / 'ido_fasttext.model'
SEED = 42
DIM = 300


def l2norm(X):
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


def train_or_load_fasttext():
    from gensim.models import FastText
    if FT_CACHE.exists():
        log.info("Loading cached fastText model")
        return FastText.load(str(FT_CACHE))
    log.info("Training fastText on Ido corpus (subword, dim=%d)...", DIM)
    sents = [ln.split() for ln in open(CORPUS, encoding='utf-8')]
    log.info("  %d sentences", len(sents))
    m = FastText(vector_size=DIM, window=5, min_count=3, sg=1, epochs=5,
                 workers=4, seed=SEED)
    m.build_vocab(sents)
    m.train(sents, total_examples=len(sents), epochs=m.epochs)
    m.save(str(FT_CACHE))
    return m


def build_gold(eo_idx):
    data = json.load(open(IO_WIKT))
    ent = data['entries'] if isinstance(data, dict) else data
    gold = {}
    for e in ent:
        io = (e.get('lemma') or '').lower().strip()
        if not io or not io.isascii() or not io.isalpha() or len(io) < 3:
            continue
        eos = {tr['term'].lower() for s in (e.get('senses') or [])
               for tr in (s.get('translations') or [])
               if tr.get('lang') == 'eo' and tr.get('term')}
        eos = {x for x in eos if x in eo_idx}
        if len(eos) == 1:
            gold[io] = next(iter(eos))
    return list(gold.items())


def main():
    eo_emb = np.load(EO_NPY).astype(np.float32)
    eo_words = [l.strip() for l in open(EO_VOCAB, encoding='utf-8')][:eo_emb.shape[0]]
    eo_idx = {w: i for i, w in enumerate(eo_words)}
    log.info("EO embedding: %s, vocab %d", eo_emb.shape, len(eo_words))

    ft = train_or_load_fasttext()
    gold = build_gold(eo_idx)
    log.info("Unambiguous gold pairs (eo in EO vocab): %d", len(gold))
    random.Random(SEED).shuffle(gold)
    n_test = min(500, len(gold) // 5)
    test, train = gold[:n_test], gold[n_test:]
    log.info("Split: train=%d test=%d", len(train), len(test))

    io_vec = {io: ft.wv[io] for io, _ in gold}        # fastText: OOV-safe via subwords

    def W_from(pairs):
        X = l2norm(np.vstack([io_vec[io] for io, _ in pairs]))
        Y = l2norm(np.vstack([eo_emb[eo_idx[eo]] for _, eo in pairs]))
        W, _ = orthogonal_procrustes(X, Y)
        return W

    W = W_from(train)
    E = l2norm(eo_emb)
    io_test = [io for io, _ in test]
    gold_map = dict(test)

    X = l2norm(np.vstack([io_vec[io] for io in io_test]) @ W)
    # CSLS-style retrieval
    S = X @ E.T
    rT = np.sort(S, axis=1)[:, -10:].mean(axis=1)
    # rS over a large source pool (all train io)
    Xs = l2norm(np.vstack([io_vec[io] for io, _ in train]) @ W)
    rS = np.sort(Xs @ E.T, axis=0)[-10:, :].mean(axis=0)
    Scsls = 2 * S - rT[:, None] - rS[None, :]

    def report(Smat, tag):
        order = np.argsort(-Smat, axis=1)[:, :5]
        conf = Smat[np.arange(len(io_test)), order[:, 0]]
        pred1 = [eo_words[order[i, 0]] for i in range(len(io_test))]
        hit1 = np.array([pred1[i] == gold_map[io_test[i]] for i in range(len(io_test))])
        hit5 = np.array([gold_map[io_test[i]] in [eo_words[j] for j in order[i]]
                         for i in range(len(io_test))])
        cog = np.array([pred1[i][:4] == io_test[i][:4] for i in range(len(io_test))])
        print(f"\n[{tag}] P@1 {hit1.mean()*100:.1f}%  P@5 {hit5.mean()*100:.1f}%"
              f"  (n={len(io_test)})")
        print(f"  cognate predictions:     {cog.mean()*100:5.1f}% of test, "
              f"precision {hit1[cog].mean()*100 if cog.any() else float('nan'):.0f}%")
        print(f"  NON-cognate predictions: {(~cog).mean()*100:5.1f}% of test, "
              f"precision {hit1[~cog].mean()*100 if (~cog).any() else float('nan'):.0f}%  <<< the number that matters")
        # confidence-thresholded NON-cognate precision
        print("  NON-cognate precision/coverage by confidence percentile:")
        for q in (0.5, 0.7, 0.9):
            thr = np.quantile(conf, q)
            keep = (conf >= thr) & ~cog
            cov = keep.sum()
            prec = hit1[keep].mean()*100 if keep.any() else float('nan')
            print(f"    top {int((1-q)*100)}% conf: {cov:3d} non-cog kept, precision {prec:.0f}%")

    report(S, "fastText + raw-NN")
    report(Scsls, "fastText + CSLS")
    print("\n(BERT bi-encoder non-cognate precision was ~6% — the bar to beat)")


if __name__ == '__main__':
    main()
