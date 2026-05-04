#!/usr/bin/env python3
"""Preprocess the Ido BERT vocabulary file.

Three stages, applied in order:

1. **Junk shape filter** — drop entries that aren't Ido lemma-shaped:
   - length < 3 (closed-class function words handled via overrides upstream)
   - contains digit, parens, quotes, dollar/percent signs, etc.
   - contains non-Latin characters (Esperanto special chars are not Ido)
   - is just punctuation or symbol fragments

2. **Apertium lemmatization** (optional, default ON) — collapse surface forms
   to canonical lemmas via lt-proc against `apertium-ido/ido.automorf.bin`.
   `kreas/kreis/kreis -> krear`, `kati -> kato`, etc. Forms lt-proc cannot
   analyze (proper nouns, loanwords, lemmas missing from the monodix) pass
   through unchanged so BERT can still attempt a translation.

3. **Wiktionary-covered filter** (optional, default ON) — skip entries that
   io_wiktionary already has a usable Esperanto translation for. BERT's value
   is in covering the long tail; running it on already-covered words wastes
   compute and tends to produce noisy candidates that pollute the bidix.

Reads:  data/ido_vocabulary.txt
Reads:  ../../apertium-ido/ido.automorf.bin (for lemmatization)
Reads:  ../../extractor/work/io_wiktionary_processed.json (for skip filter)
Writes: data/ido_vocabulary_filtered.txt
"""
import argparse
import json
import logging
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib.ido_lemmatize import lemmatize_words

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Allowed shape: ASCII letters + hyphen, length >= 3.
# Capitalized proper nouns (e.g. Berlin, Mainz, Hokeo) pass since they're
# valid Ido lemmas. Esperanto-only diacritics (ĉ/ĝ/ĥ/ĵ/ŝ/ŭ) are NOT Ido
# orthography — drop them.
_LEMMA_RE = re.compile(r'^[a-zA-Z][a-zA-Z\-]+$')

# Verb conjugation surface forms (-as/-is/-os/-us/-ez) aren't lemmas — they're
# inflections of -ar/-ir verbs. Capitalized forms (Markus, Edipus) excluded
# by the all-lowercase check.
_VERB_INFL_RE = re.compile(r'^[a-z]{2,}(?:as|is|os|us|ez)$')


def is_valid_ido_lemma(lm: str) -> bool:
    if not lm or len(lm) < 3:
        return False
    if not _LEMMA_RE.match(lm):
        return False
    # Drop verb conjugation surface forms (esas, esis, esos, etc.)
    if len(lm) <= 8 and _VERB_INFL_RE.match(lm):
        return False
    return True


def load_wiktionary_covered(processed_path: Path) -> set:
    """Return set of lowercase Ido lemmas that io.wiktionary has at least
    one Esperanto translation for. These are the words BERT can SKIP."""
    if not processed_path.exists():
        logger.warning("io_wiktionary_processed.json not found at %s — skip filter disabled", processed_path)
        return set()
    data = json.load(open(processed_path))
    entries = data.get('entries', data) if isinstance(data, dict) else data
    covered = set()
    for e in entries or []:
        lm = (e.get('lemma') or '').lower().strip()
        if not lm:
            continue
        # Has at least one EO translation?
        has_eo = any(
            tr.get('lang') == 'eo' and tr.get('term')
            for s in (e.get('senses') or [])
            for tr in (s.get('translations') or [])
        )
        if has_eo:
            covered.add(lm)
    logger.info("Wiktionary-covered Ido lemmas (with EO translation): %d", len(covered))
    return covered


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', type=Path, default=Path(__file__).resolve().parents[1] / 'data' / 'ido_vocabulary.txt')
    ap.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'data' / 'ido_vocabulary_filtered.txt')
    ap.add_argument('--io-processed', type=Path,
                    default=Path(__file__).resolve().parents[3] / 'extractor' / 'work' / 'io_wiktionary_processed.json',
                    help='io_wiktionary_processed.json (used for skip-covered filter)')
    ap.add_argument('--ido-automorf', type=Path,
                    default=Path(__file__).resolve().parents[3] / 'apertium-ido' / 'ido.automorf.bin',
                    help='Apertium-Ido analyzer binary (used for lemmatization)')
    ap.add_argument('--no-skip-covered', action='store_true',
                    help='Disable skipping Wiktionary-covered lemmas (run BERT on everything)')
    ap.add_argument('--no-lemmatize', action='store_true',
                    help='Disable Apertium lemmatization (keep surface forms as-is)')
    args = ap.parse_args()

    raw = [line.rstrip('\n') for line in open(args.input)]
    logger.info("Loaded %d raw vocab entries from %s", len(raw), args.input)

    covered = set() if args.no_skip_covered else load_wiktionary_covered(args.io_processed)

    # Stage 1: shape filter
    after_shape = []
    drop_shape = 0
    for w in raw:
        if not is_valid_ido_lemma(w):
            drop_shape += 1
            continue
        after_shape.append(w)

    # Stage 2: Apertium lemmatization (collapse surface forms)
    if args.no_lemmatize:
        lemma_map = {w: w for w in after_shape}
        analyzed = unanalyzable = 0
    else:
        logger.info("Lemmatizing %d entries via lt-proc (%s)...", len(after_shape), args.ido_automorf)
        lemma_map = lemmatize_words(after_shape, args.ido_automorf)
        analyzed = sum(1 for w, lm in lemma_map.items() if lm != w)
        unanalyzable = sum(1 for w, lm in lemma_map.items() if lm == w)

    # Dedupe by canonical lemma; preserve insertion order from `after_shape`.
    seen: set[str] = set()
    after_lemma: list[str] = []
    collapsed = 0
    for w in after_shape:
        lm = lemma_map[w]
        if lm in seen:
            collapsed += 1
            continue
        seen.add(lm)
        after_lemma.append(lm)

    # Stage 3: Wiktionary-covered filter (now applied lemma-vs-lemma).
    kept = []
    drop_wikt = 0
    for w in after_lemma:
        if w.lower() in covered:
            drop_wikt += 1
            continue
        kept.append(w)

    logger.info("Filter results:")
    logger.info("  dropped (junk shape):           %5d  (%.1f%%)", drop_shape, drop_shape * 100 / len(raw))
    logger.info("  lemmatized (surface != lemma):  %5d", analyzed)
    logger.info("  unanalyzable (surface fallback):%5d", unanalyzable)
    logger.info("  collapsed (deduped by lemma):   %5d", collapsed)
    logger.info("  dropped (Wiktionary-covered):   %5d  (%.1f%%)", drop_wikt, drop_wikt * 100 / len(raw))
    logger.info("  kept (BERT will translate):     %5d  (%.1f%%)", len(kept), len(kept) * 100 / len(raw))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w') as f:
        for w in kept:
            f.write(w + '\n')
    logger.info("Wrote %s (%d entries)", args.output, len(kept))


if __name__ == '__main__':
    main()
