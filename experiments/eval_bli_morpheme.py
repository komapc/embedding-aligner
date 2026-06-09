#!/usr/bin/env python3
"""Morpheme/root-level BLI test ('word parts vs words').

Hypothesis: the Ido corpus is too small for whole-word/char-gram vectors
(fastText collapsed to spelling). Ido is regular & agglutinative, so collapsing
every surface form to its ROOT via the apertium analyzer (urbo/urbeto/urbano ->
urb) multiplies each root's occurrences and should give better statistics.

We train word2vec (NO subword — isolates root-level distributional semantics
from the orthographic collapse) on the lemmatized corpus, align the root space
to the EO word2vec space with a gold seed, and measure NON-cognate precision.

Run: venv/bin/python experiments/eval_bli_morpheme.py
"""
from __future__ import annotations

import json
import logging
import random
import re
import subprocess
from pathlib import Path

import numpy as np
from scipy.linalg import orthogonal_procrustes

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent.parent
CORPUS = HERE / 'data' / 'processed' / 'ido_finetune_corpus.txt'
ROOTS_CACHE = HERE / 'experiments' / 'ido_corpus_roots.txt'
AUTOMORF = HERE.parents[1] / 'apertium-ido' / 'ido.automorf.bin'
EO_NPY = HERE / 'models' / 'esperanto_clean__300d.npy'
EO_VOCAB = HERE / 'models' / 'esperanto_clean__vocab.txt'
IO_WIKT = HERE.parents[1] / 'extractor' / 'work' / 'io_wiktionary_processed.json'
W2V_CACHE = HERE / 'experiments' / 'ido_roots_w2v.model'
SEED = 42
DIM = 300

_TOK = re.compile(r'\^([^/^$]+)/([^$]*)\$')
_SENT = 'qxqxqx'                                       # sentence separator token
_SPECIAL = re.compile(r'([\^$/\\<>\[\]{}@])')          # lt-proc stream-format chars


def lemmatize_lines(lines: list[str]) -> list[list[str]]:
    """Lemmatize lines in one lt-proc call. lt-proc does NOT preserve input
    newlines (and unescaped format chars `^$/\\<>[]{}@` truncate the stream), so
    escape them and separate sentences with a sentinel token, then split on it."""
    text = (' ' + _SENT + ' ').join(_SPECIAL.sub(r'\\\1', l) for l in lines)
    out = subprocess.run(['lt-proc', str(AUTOMORF)], input=text,
                         capture_output=True, text=True).stdout
    flat = []
    for m in _TOK.finditer(out):
        surf, ana = m.group(1), m.group(2)
        first = ana.split('/')[0]
        flat.append(surf.lower() if first.startswith('*') else first.split('<')[0].lower())
    sents: list[list[str]] = [[]]
    for r in flat:
        if r == _SENT:
            sents.append([])
        else:
            sents[-1].append(r)
    return sents


def build_roots_corpus():
    if ROOTS_CACHE.exists():
        return
    log.info("Lemmatizing corpus -> roots via lt-proc (chunked)...")
    with open(CORPUS) as fin, open(ROOTS_CACHE, 'w') as fout:
        buf = []
        done = 0
        for line in fin:
            buf.append(line.rstrip('\n'))
            if len(buf) >= 5000:
                fout.write('\n'.join(' '.join(r) for r in lemmatize_lines(buf)) + '\n')
                done += len(buf); buf = []
                log.info("  %d lines", done)
        if buf:
            fout.write('\n'.join(' '.join(r) for r in lemmatize_lines(buf)) + '\n')


def train_or_load():
    from gensim.models import Word2Vec
    if W2V_CACHE.exists():
        return Word2Vec.load(str(W2V_CACHE))
    log.info("Training word2vec on ROOT corpus (sg, dim=%d)...", DIM)
    sents = [ln.split() for ln in open(ROOTS_CACHE)]
    m = Word2Vec(sents, vector_size=DIM, window=5, min_count=5, sg=1,
                 epochs=5, workers=4, seed=SEED)
    m.save(str(W2V_CACHE))
    return m


def main():
    build_roots_corpus()
    w2v = train_or_load()
    wv = w2v.wv
    log.info("Root vocab: %d", len(wv))
    # sanity: are root neighbors semantic now?
    for w in ('hund', 'urb', 'dom', 'reg'):
        if w in wv:
            print(f"  NN({w}) = {[x for x,_ in wv.most_similar(w, topn=8)]}")

    eo_emb = np.load(EO_NPY).astype(np.float32)
    eo_words = [l.strip() for l in open(EO_VOCAB)][:eo_emb.shape[0]]
    eo_idx = {w: i for i, w in enumerate(eo_words)}

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
        eos = {x for x in eos if x in eo_idx}
        if len(eos) == 1:
            raw[io] = next(iter(eos))
    # map io word -> root (one word per line, batched)
    ios = list(raw)
    roots_per = lemmatize_lines(ios)
    gold = []
    for io, r in zip(ios, roots_per):
        if r and r[0] in wv:
            gold.append((io, r[0], raw[io]))
    log.info("Gold (io, root-in-vocab, eo): %d", len(gold))

    l2 = lambda X: X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    random.Random(SEED).shuffle(gold)
    n_test = min(500, len(gold) // 5)
    test, train = gold[:n_test], gold[n_test:]

    def W_from(pairs):
        X = l2(np.vstack([wv[r] for _, r, _ in pairs]))
        Y = l2(np.vstack([eo_emb[eo_idx[eo]] for *_, eo in pairs]))
        W, _ = orthogonal_procrustes(X, Y)
        return W

    W = W_from(train)
    E = l2(eo_emb)
    X = l2(np.vstack([wv[r] for _, r, _ in test]) @ W)
    S = X @ E.T
    order = np.argsort(-S, axis=1)[:, :5]
    pred1 = [eo_words[order[i, 0]] for i in range(len(test))]
    hit1 = np.array([pred1[i] == test[i][2] for i in range(len(test))])
    hit5 = np.array([test[i][2] in [eo_words[j] for j in order[i]] for i in range(len(test))])
    cog = np.array([pred1[i][:4] == test[i][0][:4] for i in range(len(test))])
    print(f"\n[morpheme/root word2vec] P@1 {hit1.mean()*100:.1f}%  P@5 {hit5.mean()*100:.1f}%  (n={len(test)})")
    print(f"  cognate predictions:     {cog.mean()*100:5.1f}%, precision {hit1[cog].mean()*100 if cog.any() else float('nan'):.0f}%")
    print(f"  NON-cognate predictions: {(~cog).mean()*100:5.1f}%, precision {hit1[~cog].mean()*100 if (~cog).any() else float('nan'):.0f}%  <<< the number that matters")
    print("\n(BERT 6%, fastText 1% non-cognate — the bar to beat)")


if __name__ == '__main__':
    main()
