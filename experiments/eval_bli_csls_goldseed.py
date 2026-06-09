#!/usr/bin/env python3
"""Offline BLI ablation: gold-seed Procrustes (#3) + CSLS retrieval (#6).

Measures precision@1/@5 of Ido→Esperanto bilingual lexicon induction on a
held-out gold split, across the 2x2 of {cognate seed, gold seed} x {raw-NN,
CSLS}. Runs locally on CPU with the existing fine-tuned model + cached EO
embeddings — no GPU, no re-finetune.

Why: run-1 cross-encoder output was 29% gold precision with confident antonyms.
The candidates it re-ranked came from a cognate-biased Procrustes seed + raw
cosine NN (hubness). This isolates whether a gold seed and CSLS fix the
candidate quality *before* spending GPU on a cross-encoder retrain.
"""
from __future__ import annotations

import json
import logging
import random
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.linalg import orthogonal_procrustes
from transformers import XLMRobertaModel, XLMRobertaTokenizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent.parent
MODEL = HERE / 'models' / 'bert-ido-finetuned-full'
EO_NPZ = HERE / 'results' / 'bert_ido_epo_alignment' / 'esperanto_bert_embeddings.npz'
IO_WIKT = HERE.parents[1] / 'extractor' / 'work' / 'io_wiktionary_processed.json'
SEED = 42
CSLS_K = 10


def l2norm(X):
    return X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)


def all_but_the_top(X, D):
    """Anisotropy fix (Mu & Viswanath): mean-center, then remove the top-D
    principal directions that dominate every BERT vector. Returns centered,
    de-topped vectors (caller re-normalizes)."""
    mu = X.mean(axis=0, keepdims=True)
    Xc = X - mu
    if D > 0:
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
        top = Vt[:D]                       # [D, d]
        Xc = Xc - (Xc @ top.T) @ top
    return Xc


def get_word_embedding(word, model, tok):
    t = tok(word, return_tensors='pt', add_special_tokens=True)
    with torch.no_grad():
        out = model(**t).last_hidden_state[0, 1:-1, :]
        if out.shape[0] == 0:  # single-subword edge case
            out = model(**t).last_hidden_state[0, :, :]
        return out.mean(dim=0).cpu().numpy()


def embed_words(words, model, tok):
    return np.vstack([get_word_embedding(w, model, tok) for w in words]).astype(np.float32)


def build_gold(eo_idx):
    """Unambiguous io->eo gold pairs whose eo term is in the cached EO vocab."""
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


def cognate_seed(seed_ios, eo_words, max_pairs=500):
    """Reproduce the pipeline's surface-similarity seed (exact + near matches)."""
    from difflib import SequenceMatcher
    eo_set = set(eo_words)
    pairs = []
    for io in seed_ios:
        if io in eo_set:
            pairs.append((io, io))
    used = {e for _, e in pairs}
    by_len = {}
    for w in eo_words:
        by_len.setdefault(len(w), []).append(w)
    for io in seed_ios:
        if len(pairs) >= max_pairs:
            break
        best = None
        for L in range(len(io) - 2, len(io) + 3):
            for eo in by_len.get(L, ()):
                if eo in used:
                    continue
                if SequenceMatcher(None, io, eo).ratio() >= 0.7:
                    best = eo
                    break
            if best:
                break
        if best:
            pairs.append((io, best))
            used.add(best)
    return pairs


def procrustes_W(pairs, io_vec, eo_emb, eo_idx):
    X = np.vstack([io_vec[io] for io, _ in pairs])
    Y = np.vstack([eo_emb[eo_idx[eo]] for _, eo in pairs])
    W, _ = orthogonal_procrustes(l2norm(X), l2norm(Y))
    return W


def precision(io_test, gold_map, io_vec, W, eo_emb, eo_words, use_csls,
              src_pool=None, return_top1sim=False):
    X = l2norm(np.vstack([io_vec[io] for io in io_test]) @ W)
    E = l2norm(eo_emb)
    S = X @ E.T                                   # [T, N] cosine
    cos_top1 = S.max(axis=1).copy()               # raw cosine of the top-1 match
    if use_csls:
        rT = np.sort(S, axis=1)[:, -CSLS_K:].mean(axis=1)        # query side
        # target-side density estimated over a large source pool, not just the test
        P = l2norm((src_pool if src_pool is not None else X) )
        Ssrc = P @ E.T
        rS = np.sort(Ssrc, axis=0)[-CSLS_K:, :].mean(axis=0)
        S = 2 * S - rT[:, None] - rS[None, :]
    order = np.argsort(-S, axis=1)[:, :5]
    p1 = p5 = 0
    hit1 = np.zeros(len(io_test), dtype=bool)
    pred1 = []
    for i, io in enumerate(io_test):
        g = gold_map[io]
        top5 = [eo_words[j] for j in order[i]]
        pred1.append(top5[0])
        if top5[0] == g:
            p1 += 1
            hit1[i] = True
        if g in top5:
            p5 += 1
    n = len(io_test)
    if return_top1sim:
        return p1 / n, p5 / n, cos_top1, hit1, pred1
    return p1 / n, p5 / n


def main():
    eo = np.load(EO_NPZ, allow_pickle=True)
    eo_emb = eo['embeddings'].astype(np.float32)
    eo_words = [str(w) for w in eo['words']]
    eo_idx = {w: i for i, w in enumerate(eo_words)}
    log.info("Cached EO vocab: %d words, dim %d", len(eo_words), eo_emb.shape[1])

    gold = build_gold(eo_idx)
    log.info("Unambiguous gold pairs (eo in cached vocab): %d", len(gold))
    random.Random(SEED).shuffle(gold)
    n_test = min(500, len(gold) // 5)
    test = gold[:n_test]
    train = gold[n_test:]
    log.info("Split: train=%d test=%d", len(train), len(test))

    all_ios = sorted({io for io, _ in gold})
    cache = HERE / 'experiments' / 'gold_io_emb.npz'
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        io_vec = {str(w): v for w, v in zip(z['words'], z['emb'])}
        if set(all_ios) <= set(io_vec):
            log.info("Loaded %d cached io embeddings", len(io_vec))
        else:
            io_vec = None
    else:
        io_vec = None
    if io_vec is None:
        log.info("Loading model (CPU) + embedding %d gold io words...", len(all_ios))
        tok = XLMRobertaTokenizer.from_pretrained(str(MODEL))
        model = XLMRobertaModel.from_pretrained(str(MODEL)).eval()
        mat = embed_words(all_ios, model, tok)
        np.savez(cache, words=np.array(all_ios), emb=mat)
        io_vec = dict(zip(all_ios, mat))

    gold_map = dict(gold)
    io_test = [io for io, _ in test]

    # frequency rank of each io word (data/ido_vocabulary.txt is freq-ordered)
    freq_rank = {}
    vf = HERE / 'data' / 'ido_vocabulary.txt'
    if vf.exists():
        for i, line in enumerate(open(vf)):
            w = line.strip()
            if w and w not in freq_rank:
                freq_rank[w] = i

    def run(io_mat_dict, eo_mat, tag):
        src_pool = np.vstack([io_mat_dict[io] for io, _ in train])
        W_gold = procrustes_W(train, io_mat_dict, eo_mat, eo_idx)
        cos1 = hit1 = pred1 = None
        print(f"\n=== {tag}: Ido→EO BLI precision (held-out {len(test)} pairs) ===")
        print(f"{'config':<28}{'P@1':>8}{'P@5':>8}")
        for name, W, csls in [("gold seed + raw-NN", W_gold, False)]:
            p1, p5, c, h, pr = precision(io_test, gold_map, io_mat_dict, W,
                                         eo_mat, eo_words, csls,
                                         src_pool=(src_pool @ W),
                                         return_top1sim=True)
            print(f"{name:<28}{p1*100:>7.1f}%{p5*100:>7.1f}%")
            cos1, hit1, pred1 = c, h, np.array(pr)
        return cos1, hit1, pred1

    def analyze(cos1, hit1, pred1, tag):
        cog = np.array([pred1[i][:4] == io_test[i][:4] for i in range(len(io_test))])
        print(f"\n[{tag}] precision/coverage by cosine threshold, split cognate vs NON-cognate:")
        print(f"{'thr':>6}{'all cov':>9}{'all P':>7}{'   cog cov':>11}{'cog P':>7}"
              f"{'  NONcog cov':>13}{'NONcog P':>9}")
        for thr in (0.0, 0.6, 0.7, 0.8):
            for label, mask in [('', None)]:
                pass
            k = cos1 >= thr
            def cp(sel):
                s = k & sel
                return s.mean()*100, (hit1[s].mean()*100 if s.any() else float('nan'))
            ac, ap = cp(np.ones_like(k))
            cc, cpp = cp(cog)
            nc, npp = cp(~cog)
            print(f"{thr:>6.2f}{ac:>8.1f}%{ap:>6.0f}%{cc:>10.1f}%{cpp:>6.0f}%{nc:>12.1f}%{npp:>8.0f}%")
        # frequency terciles (rarer = higher rank) at a fixed threshold
        if freq_rank:
            ranks = np.array([freq_rank.get(io, 10**9) for io in io_test])
            valid = ranks < 10**9
            qs = np.quantile(ranks[valid], [1/3, 2/3])
            tercile = np.digitize(ranks, qs)   # 0=common,1=mid,2=rare
            print(f"[{tag}] gold-seed top-1 precision @ cos>=0.70 by frequency tercile:")
            k = cos1 >= 0.70
            for t, nm in [(0, 'common'), (1, 'mid'), (2, 'rare')]:
                sel = (tercile == t) & valid
                s = k & sel
                cov = s.sum()/max(sel.sum(),1)*100
                pr = hit1[s].mean()*100 if s.any() else float('nan')
                print(f"    {nm:<7}: kept {s.sum():>3}/{sel.sum():>3} ({cov:4.0f}%)  precision {pr:5.0f}%")

    # raw vs whitened
    cR = run(io_vec, eo_emb, "RAW")
    D = 10
    io_mat = np.vstack([io_vec[w] for w in all_ios])
    io_vec_w = dict(zip(all_ios, all_but_the_top(io_mat, D)))
    cW = run(io_vec_w, all_but_the_top(eo_emb, D), f"WHITENED(D={D})")

    # matched-coverage RAW vs WHITENED (advisor: is whitening new ranking or just rescale?)
    print("\n=== matched-coverage precision (top-X% by top-1 confidence) ===")
    print(f"{'coverage':>10}{'RAW P':>8}{'WHITENED P':>12}")
    for frac in (0.2, 0.5, 1.0):
        out = []
        for cos1, hit1, _ in (cR, cW):
            kth = np.quantile(cos1, 1 - frac)
            sel = cos1 >= kth
            out.append(hit1[sel].mean()*100)
        print(f"{int(frac*100):>9}%{out[0]:>7.0f}%{out[1]:>11.0f}%")

    analyze(*cR, "RAW")
    analyze(*cW, f"WHITENED(D={D})")
    print("\n(run-1 cross-encoder field precision was ~29% top-1 for reference)")


if __name__ == '__main__':
    main()
