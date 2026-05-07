"""Assemble (io, eo, label) training pairs for the IO↔EO cross-encoder.

Produces three flavors of pair:

  * **Wiktionary positives** — gold translations from `bilingual_raw.json`.
    Single-sense, single-EO-term entries from io_wiktionary, eo_wiktionary,
    en_wiktionary_via, fr_wiktionary_via.

  * **Wikipedia langlink positives** — interlanguage-link page-title pairs
    from `io_eo_langlinks.json`, FILTERED to drop:
        (a) trivial identity pairs (io == eo)        — kills `ABBA ↔ ABBA`
        (b) any pair with an uppercase-leading term  — kills named entities
    What remains is loanword / long-tail vocabulary that complements
    Wiktionary's coverage.

  * **Hard negatives** — for each positive, take BERT's top-K candidates for
    the IO lemma and use the non-gold candidates. Pulls from the existing
    `translation_candidates.json` so we don't pay for a separate retrieval.

  * **Surface-similar negatives** — for each positive, pick an EO vocab term
    of similar length within edit-distance ≤ 2 of the IO lemma, excluding the
    gold. Catches cognate false-friends like `krea` / `kreado` that the model
    must learn to discriminate.

Held-out split is deterministic and stratified across all five source tiers
so the eval set covers every kind of positive uniformly.
"""
from __future__ import annotations

import difflib
import json
import logging
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

logger = logging.getLogger(__name__)


# A lemma-shaped lowercase term: ASCII / Esperanto-letter alphabetic, no
# spaces or punctuation, length ≥ 3. Used to gate Wikipedia-langlink page
# titles down to single-word vocabulary entries.
_LOWERCASE_LEMMA_RE = re.compile(r'^[a-zĉĝĥĵŝŭ]{3,}$')


class Pair(NamedTuple):
    """A single training example."""
    io: str
    eo: str
    label: int   # 1 = positive, 0 = negative
    tag: str     # source name for positives ("io_wiktionary", "wikipedia_langlinks", ...)
                 # or negative class for negatives ("hard", "surface")


_WIKTIONARY_SOURCES = frozenset({
    'io_wiktionary', 'eo_wiktionary', 'en_wiktionary_via', 'fr_wiktionary_via',
})


def _norm(s: str | None) -> str:
    return (s or '').strip()


def load_wiktionary_positives(bilingual_raw_path: Path) -> list[Pair]:
    """Return single-sense, single-EO-term positives from `bilingual_raw.json`.

    Multi-sense / multi-translation entries are skipped to avoid mislabelling
    a polysemy. We tag each pair with the **first** Wiktionary source listed
    on the translation; preference order matches stratification later.
    """
    with open(bilingual_raw_path) as f:
        raw = json.load(f)

    out: list[Pair] = []
    for entry in raw:
        if entry.get('language') != 'io':
            continue
        senses = entry.get('senses') or []
        if len(senses) != 1:
            continue
        io_lemma = _norm(entry.get('lemma'))
        if not io_lemma:
            continue
        translations = [
            t for t in senses[0].get('translations') or []
            if t.get('lang') == 'eo' and _norm(t.get('term'))
        ]
        if len(translations) != 1:
            continue
        t = translations[0]
        sources = t.get('sources') or []
        wikt_src = next((s for s in sources if s in _WIKTIONARY_SOURCES), None)
        if wikt_src is None:
            continue
        out.append(Pair(io=io_lemma, eo=_norm(t['term']), label=1, tag=wikt_src))
    logger.info("Wiktionary positives: %d (single-sense, single-EO)", len(out))
    return out


def load_langlink_positives(langlinks_path: Path) -> list[Pair]:
    """Return Wikipedia-langlink positives, filtered to drop named entities.

    Wikipedia article titles arrive capitalized (`ABBA`, `Abadeyo`,
    `AFK Ajax`). We lowercase both sides and keep only entries where:
      - both terms are single-word lemma-shaped (matches `_LOWERCASE_LEMMA_RE`,
        i.e. all-letters, no spaces / digits / hyphens, length ≥ 3) — drops
        multi-word titles like `AFK Ajax` and acronyms like `ABBA` (which
        lowercase to `abba`, length 4 letters; passes the regex but the
        identity filter below catches it)
      - lowercased forms differ — drops identity matches (`abba ↔ abba`,
        `berlin ↔ berlin`)
    The remainder is single-word loanwords / long-tail vocab where the IO
    and EO orthographies genuinely differ (`abadeyo ↔ abatejo`).
    """
    if not langlinks_path.exists():
        logger.warning("Langlinks file missing: %s — skipping langlink positives", langlinks_path)
        return []
    with open(langlinks_path) as f:
        data = json.load(f)
    out: list[Pair] = []
    for entry in data:
        io_lemma = _norm(entry.get('lemma')).lower()
        if not _LOWERCASE_LEMMA_RE.match(io_lemma):
            continue
        for s in entry.get('senses') or []:
            for t in s.get('translations') or []:
                if t.get('lang') != 'eo':
                    continue
                eo = _norm(t.get('term')).lower()
                if not _LOWERCASE_LEMMA_RE.match(eo):
                    continue
                if eo == io_lemma:
                    continue
                out.append(Pair(io=io_lemma, eo=eo, label=1, tag='wikipedia_langlinks'))
    logger.info("Langlink positives (filtered): %d", len(out))
    return out


def load_all_positives(bilingual_raw_path: Path, langlinks_path: Path) -> list[Pair]:
    """Concatenate Wiktionary + Wikipedia-langlink positives, deduplicated by
    (io, eo). When the same pair appears in both sources, keep the Wiktionary
    one (higher tier)."""
    wikt = load_wiktionary_positives(bilingual_raw_path)
    seen = {(p.io, p.eo) for p in wikt}
    ll = [p for p in load_langlink_positives(langlinks_path)
          if (p.io, p.eo) not in seen]
    logger.info("Total unique positives: %d (wikt %d + langlink %d)",
                len(wikt) + len(ll), len(wikt), len(ll))
    return wikt + ll


def load_all_known_golds(bilingual_raw_path: Path, langlinks_path: Path) -> dict[str, set[str]]:
    """Return io -> {eo₁, eo₂, ...} mapping covering EVERY known gold
    translation, including multi-sense / multi-translation entries we don't
    emit as positives. Used to bullet-proof negative selection: even
    polysemous translations that won't be trained on must be excluded as
    candidate negatives, otherwise the cross-encoder learns to penalize
    correct alternative translations."""
    golds: dict[str, set[str]] = defaultdict(set)
    with open(bilingual_raw_path) as f:
        raw = json.load(f)
    for entry in raw:
        if entry.get('language') != 'io':
            continue
        io_lemma = _norm(entry.get('lemma'))
        if not io_lemma:
            continue
        for s in entry.get('senses') or []:
            for t in s.get('translations') or []:
                if t.get('lang') != 'eo':
                    continue
                eo = _norm(t.get('term'))
                if eo:
                    golds[io_lemma].add(eo)
    if langlinks_path.exists():
        with open(langlinks_path) as f:
            ll = json.load(f)
        for entry in ll:
            io_lemma = _norm(entry.get('lemma')).lower()
            if not _LOWERCASE_LEMMA_RE.match(io_lemma):
                continue
            for s in entry.get('senses') or []:
                for t in s.get('translations') or []:
                    if t.get('lang') != 'eo':
                        continue
                    eo = _norm(t.get('term')).lower()
                    if _LOWERCASE_LEMMA_RE.match(eo):
                        golds[io_lemma].add(eo)
    logger.info("Known-gold coverage: %d IO lemmas with at least one gold EO",
                len(golds))
    return golds


def assemble_hard_negatives(
    positives: list[Pair], candidates_path: Path,
    known_golds: dict[str, set[str]], neg_per_pos: int = 4,
) -> list[Pair]:
    """For each positive, pull up to `neg_per_pos` non-gold candidates from
    BERT's top-K for that IO lemma.

    `known_golds` is the full io→{eo} mapping from `load_all_known_golds()`
    — used to skip ANY known correct translation, including polysemous
    senses we never emit as positives (e.g. `rakonto` → {`fabelo`, `fablo`,
    `rakonto`} — picking any of them as a hard negative would teach the
    cross-encoder a wrong lesson).

    Skips positives whose IO lemma isn't in the candidates file (typically
    Wiktionary-covered words BERT didn't process — no hard negatives
    available there)."""
    with open(candidates_path) as f:
        cands = json.load(f)
    out: list[Pair] = []
    missing = 0
    for p in positives:
        bucket = cands.get(p.io)
        if not bucket:
            missing += 1
            continue
        gold = known_golds.get(p.io, set())
        picked = 0
        for c in bucket:
            if picked >= neg_per_pos:
                break
            eo = _norm(c.get('epo'))
            if not eo or eo in gold:
                continue
            out.append(Pair(io=p.io, eo=eo, label=0, tag='hard'))
            picked += 1
    logger.info("Hard negatives: %d (positives without BERT candidates: %d)", len(out), missing)
    return out


# Esperanto lemma endings (noun -o, adj -a, adv -e, verb-inf -i). Filtering
# the EO vocab to these endings cuts inflectional forms (`-on` accusative,
# `-ojn` plural-acc, `-as/-is/-os/-us` verb-tense) which would otherwise
# pollute the surface-similar negatives with `rakonto → rakonton, rakontoj`
# and similar non-adversarial junk.
_EO_LEMMA_ENDINGS = ('o', 'a', 'e', 'i')


def _looks_like_inflection_of(word: str, gold: str) -> bool:
    """True if `word` appears to be a morphological inflection of `gold`.
    Catches `gold + 'n'` (acc), `gold + 'j'` (plural), `gold[:-1] + 'oj'`,
    `gold[:-1] + 'as'`, etc. Conservative — only the obvious shapes."""
    if not gold or word == gold:
        return False
    if word.startswith(gold) and word[len(gold):] in ('n', 'j', 'jn', 's'):
        return True
    if len(gold) >= 4 and word.startswith(gold[:-1]):
        tail = word[len(gold) - 1:]
        if tail in ('oj', 'ojn', 'aj', 'ajn', 'as', 'is', 'os', 'us', 'ata',
                    'inta', 'anta', 'onta'):
            return True
    return False


def assemble_surface_negatives(
    positives: list[Pair], eo_vocab_path: Path,
    known_golds: dict[str, set[str]],
    neg_per_pos: int = 1, vocab_cap: int = 100_000,
    cutoff: float = 0.7, seed: int = 42,
) -> list[Pair]:
    """For each positive, pick an EO lemma whose surface form is similar to
    the IO lemma (but is not a known gold or an obvious inflection of one)
    as a surface-similarity negative.

    Implementation uses `difflib.get_close_matches` (C-optimized stdlib) on
    a length-bucketed candidate pool, ~60× faster than a hand-rolled bounded
    Levenshtein for the same coverage.

    Vocab filtering:
      - lemma-shaped (`_LOWERCASE_LEMMA_RE`): drops punctuation noise like
        `rivereto),` that the raw frequency dump contains
      - lemma-ending (`o`/`a`/`e`/`i`): drops inflectional forms that aren't
        independent words

    Per-positive selection skips:
      - the IO lemma itself
      - any known gold (from `known_golds`)
      - obvious inflectional variants of any known gold (`rakonton` for
        gold `rakonto`)
    """
    if not eo_vocab_path.exists():
        logger.warning("EO vocab missing: %s — skipping surface negatives", eo_vocab_path)
        return []
    raw: list[str] = []
    with open(eo_vocab_path) as f:
        for line in f:
            w = line.strip()
            if (_LOWERCASE_LEMMA_RE.match(w) and len(w) >= 4
                    and w.endswith(_EO_LEMMA_ENDINGS)):
                raw.append(w)
                if len(raw) >= vocab_cap:
                    break
    by_length: dict[int, list[str]] = defaultdict(list)
    for w in raw:
        by_length[len(w)].append(w)
    logger.info("Surface-neg vocab: %d EO lemma-shaped entries (cap=%d)",
                len(raw), vocab_cap)
    rng = random.Random(seed)
    out: list[Pair] = []
    no_match = 0
    for p in positives:
        n = len(p.io)
        gold = known_golds.get(p.io, set())
        pool: list[str] = []
        for L in range(max(4, n - 2), n + 3):
            pool.extend(by_length.get(L, ()))
        if not pool:
            no_match += 1
            continue
        matches = difflib.get_close_matches(p.io, pool, n=10, cutoff=cutoff)
        kept = [
            m for m in matches
            if m != p.io
            and m not in gold
            and not any(_looks_like_inflection_of(m, g) for g in gold)
        ]
        if not kept:
            no_match += 1
            continue
        rng.shuffle(kept)
        for eo in kept[:neg_per_pos]:
            out.append(Pair(io=p.io, eo=eo, label=0, tag='surface'))
    logger.info("Surface-similar negatives: %d (positives without surface match: %d)",
                len(out), no_match)
    return out


def stratified_train_heldout_split(
    positives: list[Pair], heldout_size: int = 200, seed: int = 42,
    eligible_io_set: set[str] | None = None,
) -> tuple[list[Pair], list[Pair]]:
    """Stratified deterministic split by `tag`. Held-out gets a proportional
    number of positives from each source tier so the eval set matches the
    training distribution.

    `eligible_io_set` (optional): when given, the held-out set is drawn
    ONLY from positives whose IO lemma is in this set. Used by the trainer
    to ensure heldout positives have BERT candidates available for hard-
    negative scoring (the cross-encoder is deployed on BERT's candidate
    output, so out-of-pool positives can't be evaluated meaningfully).
    Train then excludes any positive whose IO is in the heldout's IO set —
    this prevents the model from seeing the heldout IO under a different
    EO during training (no cross-set leakage).
    """
    by_tag: dict[str, list[Pair]] = defaultdict(list)
    for p in positives:
        if eligible_io_set is not None and p.io not in eligible_io_set:
            continue
        by_tag[p.tag].append(p)
    rng = random.Random(seed)
    heldout: list[Pair] = []
    eligible_total = sum(len(v) for v in by_tag.values())
    if eligible_total == 0:
        logger.warning("No eligible positives for heldout — returning empty heldout")
        return list(positives), []
    for tag, items in sorted(by_tag.items()):
        rng.shuffle(items)
        n_heldout = max(1, round(heldout_size * len(items) / eligible_total))
        heldout.extend(items[:n_heldout])
    rng.shuffle(heldout)
    if len(heldout) > heldout_size:
        heldout = heldout[:heldout_size]
    heldout_ios = {p.io for p in heldout}
    train = [p for p in positives if p.io not in heldout_ios]
    logger.info("Split: train=%d heldout=%d (per-tag heldout: %s) | eligibility-filtered: %s",
                len(train), len(heldout),
                {tag: sum(1 for p in heldout if p.tag == tag) for tag in by_tag},
                eligible_io_set is not None)
    return train, heldout


def load_candidate_io_set(candidates_path: Path) -> set[str]:
    """Return the set of IO lemmas that have BERT candidates available.
    These are the inputs the cross-encoder will see at inference time."""
    with open(candidates_path) as f:
        cands = json.load(f)
    return set(cands.keys())


def dump_heldout_jsonl(
    heldout: list[Pair], candidates_path: Path, out_path: Path,
    neg_per_pos: int = 4,
) -> None:
    """Write the held-out positives plus their associated hard negatives as
    JSON-Lines for stable, auditable evaluation. Each line is one positive
    with its `(io, gold_eo, tag, hard_negatives)` bundle."""
    with open(candidates_path) as f:
        cands = json.load(f)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w') as f:
        for p in heldout:
            bucket = cands.get(p.io) or []
            negs = [_norm(c.get('epo')) for c in bucket
                    if _norm(c.get('epo')) and _norm(c.get('epo')) != p.eo][:neg_per_pos]
            f.write(json.dumps({
                'io': p.io, 'eo_gold': p.eo, 'tag': p.tag,
                'hard_negatives': negs,
            }, ensure_ascii=False) + '\n')
    logger.info("Wrote held-out set: %s (%d entries)", out_path, len(heldout))
