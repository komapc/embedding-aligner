#!/usr/bin/env python3
"""Symmetric root↔stem BLI + iterative (VecMap-style) refinement.

The morpheme run made the Ido ROOT space semantic but aligned it to the EO WORD
space (hund vs hundo) — a granularity mismatch that one-shot Procrustes couldn't
bridge. Fix: put EO at the same granularity. apertium-ido strips only the
GRAMMATICAL ending (urbo->urb, urbeto->urbet), so we derive EO "stems" by
stripping the same endings from the existing 430k EO word vectors and averaging
each lexeme's inflections — no eowiki extraction, reusing the high-quality EO
embeddings. Then align root↔stem and refine with self-learning.

Run: venv/bin/python experiments/eval_bli_symmetric.py
"""
from __future__ import annotations

import json
import logging
import random
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from gensim.models import Word2Vec
from scipy.linalg import orthogonal_procrustes

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_bli_morpheme import lemmatize_lines  # reuse the fixed lemmatizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent.parent
EO_NPY = HERE / 'models' / 'esperanto_clean__300d.npy'
EO_VOCAB = HERE / 'models' / 'esperanto_clean__vocab.txt'
IO_WIKT = HERE.parents[1] / 'extractor' / 'work' / 'io_wiktionary_processed.json'
IO_W2V = HERE / 'experiments' / 'ido_roots_w2v.model'
SEED = 42
TARGET_CAP = 120_000          # build EO stems from the top-N frequent EO words

# EO grammatical endings, longest first (mirrors apertium grammatical strip).
_EO_SUF = ('ojn', 'ajn', 'on', 'an', 'en', 'oj', 'aj', 'as', 'is', 'os', 'us',
           'o', 'a', 'e', 'i', 'u')


def stem_eo(w: str) -> str:
    for suf in _EO_SUF:
        if w.endswith(suf) and len(w) - len(suf) >= 2:
            return w[:-len(suf)]
    return w


def l2(X):
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


def main():
    # --- EO stem embeddings (average each lexeme's inflections) ---
    eo_emb = np.load(EO_NPY).astype(np.float32)
    eo_words = [l.strip() for l in open(EO_VOCAB)][:eo_emb.shape[0]]
    groups = defaultdict(list)
    for i, w in enumerate(eo_words[:TARGET_CAP]):
        if w.isalpha():
            groups[stem_eo(w)].append(i)
    stems = [s for s in groups if len(s) >= 2]
    stem_emb = np.vstack([eo_emb[groups[s]].mean(0) for s in stems]).astype(np.float32)
    stem_idx = {s: i for i, s in enumerate(stems)}
    log.info("EO stems: %d (from top %d words)", len(stems), TARGET_CAP)

    # --- Ido root vectors (cached morpheme model) ---
    wv = Word2Vec.load(str(IO_W2V)).wv
    log.info("Ido root vocab: %d", len(wv))

    # --- gold (io_root, eo_stem) ---
    data = json.load(open(IO_WIKT))
    ent = data['entries'] if isinstance(data, dict) else data
    raw = {}
    for e in ent:
        io = (e.get('lemma') or '').lower().strip()
        if not io or not io.isascii() or not io.isalpha() or len(io) < 3:
            continue
        eos = {tr['term'].lower() for s in (e.get('senses') or [])
               for tr in (s.get('translations') or [])
               if tr.get('lang') == 'eo' and tr.get('term')}
        eos = {stem_eo(x) for x in eos if x.isalpha()}
        eos = {x for x in eos if x in stem_idx}
        if len(eos) == 1:
            raw[io] = next(iter(eos))
    ios = list(raw)
    roots_per = lemmatize_lines(ios)
    gold = []
    for io, r in zip(ios, roots_per):
        if r and r[0] in wv and r[0] != raw[io]:   # drop trivial identical-stem
            gold.append((io, r[0], raw[io]))
    # dedup by (root, stem)
    seen = set(); g2 = []
    for io, r, s in gold:
        if (r, s) not in seen:
            seen.add((r, s)); g2.append((io, r, s))
    gold = g2
    log.info("Gold (io_root != eo_stem, both in vocab): %d", len(gold))

    random.Random(SEED).shuffle(gold)
    n_test = min(500, len(gold) // 5)
    test, train = gold[:n_test], gold[n_test:]

    Et = l2(stem_emb)
    src_roots = [r for _, r, _ in train]
    Xtr = l2(np.vstack([wv[r] for r in src_roots]))
    Ytr = l2(np.vstack([stem_emb[stem_idx[s]] for _, _, s in train]))

    Xte = l2(np.vstack([wv[r] for _, r, _ in test]))
    gold_stem = [s for _, _, s in test]
    io_word = [io for io, _, _ in test]

    def evaluate(W, tag):
        S = (Xte @ W) @ Et.T
        order = np.argsort(-S, axis=1)[:, :5]
        pred1 = [stems[order[i, 0]] for i in range(len(test))]
        hit1 = np.array([pred1[i] == gold_stem[i] for i in range(len(test))])
        hit5 = np.array([gold_stem[i] in [stems[j] for j in order[i]] for i in range(len(test))])
        cog = np.array([pred1[i][:4] == test[i][1][:4] for i in range(len(test))])
        nc = ~cog
        print(f"\n[{tag}] P@1 {hit1.mean()*100:.1f}%  P@5 {hit5.mean()*100:.1f}%  (n={len(test)})")
        print(f"  cognate pred:     {cog.mean()*100:5.1f}%, precision "
              f"{hit1[cog].mean()*100 if cog.any() else float('nan'):.0f}%")
        print(f"  NON-cognate pred: {nc.mean()*100:5.1f}%, precision "
              f"{hit1[nc].mean()*100 if nc.any() else float('nan'):.0f}%  <<<")

    # one-shot supervised Procrustes
    W, _ = orthogonal_procrustes(Xtr, Ytr)
    evaluate(W, "root<->stem, Procrustes")

    # self-learning refinement (VecMap-style): induce mutual-NN pairs over a
    # frequent sub-vocab, re-align, repeat.
    log.info("Self-learning refinement...")
    sub_roots = [w for w in wv.index_to_key[:20000] if w in wv]
    Xs_all = l2(np.vstack([wv[w] for w in sub_roots]))
    Et_sub = Et[:40000]                                  # frequent stems
    stems_sub = stems[:40000]
    for it in range(5):
        M = (Xs_all @ W) @ Et_sub.T
        s2t = M.argmax(1)
        t2s = M.argmax(0)
        idx = [i for i in range(len(sub_roots)) if t2s[s2t[i]] == i]
        if len(idx) < 50:
            break
        X = l2(np.vstack([wv[sub_roots[i]] for i in idx]))
        Y = l2(Et_sub[[s2t[i] for i in idx]])
        W, _ = orthogonal_procrustes(X, Y)
    log.info("  refined on %d mutual-NN pairs", len(idx))
    evaluate(W, "root<->stem, +self-learning")

    print("\n(BERT 6%, fastText 1%, morpheme/root↔word 2% non-cognate — bar to beat)")


if __name__ == '__main__':
    main()
