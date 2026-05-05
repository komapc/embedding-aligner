"""Ido morphological lemmatization via Apertium lt-proc.

Wraps `lt-proc -a apertium-ido/ido.automorf.bin` to canonicalize a list of
surface forms. For each input word:

  - if lt-proc has at least one analysis, pick the best reading and reconstruct
    its canonical lemma (stem + POS-suffix);
  - if lt-proc cannot analyze it (e.g. proper nouns, loanwords, or lemmas
    missing from apertium-ido's monodix), pass the surface through unchanged
    so BERT can still attempt a translation.

Reading-selection (multi-analysis tie-break): prefer a reading WITHOUT any
`der_*` tag when one exists. Rationale: when lt-proc returns both
`kre<vblex><der_act>...` and `kread<n>` for "kreado", the second reading
treats it as a base lemma in its own right (which it is — the dix has it as
a noun) and is the canonicalization users expect.

The lt-proc subprocess is invoked once with all words piped to stdin
(null-flush mode `-z`) — avoids ~40k subprocess starts.
"""
from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


# Apertium-Ido has a single verb paradigm `ar__vblex` — no -ir/-or verbs in
# the monodix — so <vblex> always maps to +ar.
_POS_SUFFIX = {
    'n':     'o',
    'adj':   'a',
    'adv':   'e',
    'vblex': 'ar',
}
# Closed-class POS where the stem IS the lemma (no suffix to add): pronouns,
# numerals, determiners, prepositions, conjunctions, proper nouns,
# interjections.
_NO_SUFFIX_POS = frozenset({'prn', 'num', 'det', 'pr', 'cnjcoo', 'cnjsub',
                            'np', 'ij', 'prep_art', 'rel'})

# Apertium "derivation" tags. A reading containing any of these is a derived
# form (e.g. kreado = krear + der_act); we prefer the non-derived reading at
# tie-break time so a separate noun lemma (if one exists) wins.
_DER_TAG_RE = re.compile(r'<der_[a-z_]+>')

# `^surface/reading1/reading2/.../$` — readings separated by `/`.
# `^*surface$` for unanalyzable. Apertium uses `<tag>` for tags.
_READING_TAG_RE = re.compile(r'<([a-z_]+)>')


def _parse_lt_proc_output(line: str) -> tuple[str, list[str]] | None:
    """Parse one `^...$` block. Returns (surface, [reading1, reading2, ...])
    or None if unparseable. Unanalyzable forms come back as
    `^*surface$` (no `/` — no readings)."""
    line = line.strip()
    if not line.startswith('^') or not line.endswith('$'):
        return None
    inner = line[1:-1]
    parts = inner.split('/')
    surface = parts[0]
    readings = parts[1:]
    if surface.startswith('*'):
        # rare alternate form: `*^word$` (unanalyzable in different position)
        surface = surface.lstrip('*')
    # readings starting with `*` mean "unanalyzable" — drop them
    readings = [r for r in readings if not r.startswith('*')]
    return surface, readings


def _pick_reading(readings: list[str]) -> str | None:
    """Tie-break across multiple readings: prefer a reading without any
    `der_*` tag. Falls back to the first reading."""
    if not readings:
        return None
    non_derived = [r for r in readings if not _DER_TAG_RE.search(r)]
    return non_derived[0] if non_derived else readings[0]


def _extract_base_from_derivation(readings: list[str]) -> str | None:
    """If any reading is a NOUN derivation (contains a `der_*` tag with
    outer POS `<n>`), reconstruct the underlying base lemma from that
    reading and return it.

    For example, `kre<vblex><der_act><n><sg>` is the `der_act` action-noun
    derivation of base `kre<vblex>` → reconstructs to `krear`. Returns None
    when no reading has a noun-derivation tag.

    Used to collapse derivable noun surface forms (kreado, kreanto, kreajo)
    onto their base verb, since Apertium's paradigm rules can re-derive the
    Esperanto translation from the base.

    Adjective derivations (participles like `skribita` → `skrib<vblex><der_ppas><adj>`)
    are NOT collapsed: io.wiktionary lists those as standalone adjective lemmas
    in the monodix, which beats the verb-paradigm path in apertium's bidix
    selection. Until the extractor stops emitting empty-sense monodix entries
    for these, BERT-provided translations are the safer path.
    """
    for reading in readings:
        if not _DER_TAG_RE.search(reading):
            continue
        m = re.match(r'^([^<]+)(.*)$', reading)
        if not m:
            continue
        stem, tagstr = m.group(1), m.group(2)
        # Find the POS tag immediately AFTER the first der_*. If it's not 'n',
        # skip this reading (participles, etc. — see docstring).
        after_der_match = re.search(r'<der_[a-z_]+>(.*)$', tagstr)
        if after_der_match:
            outer_tags = _READING_TAG_RE.findall(after_der_match.group(1))
            outer_pos = next((t for t in outer_tags if t in _POS_SUFFIX or t in _NO_SUFFIX_POS), None)
            if outer_pos is not None and outer_pos != 'n':
                continue
        # Truncate tag string at the FIRST der_* — base reading is everything
        # before the derivation.
        before_der = re.split(r'<der_', tagstr, maxsplit=1)[0]
        tags = _READING_TAG_RE.findall(before_der)
        for tag in tags:
            if tag in _POS_SUFFIX:
                return stem + _POS_SUFFIX[tag]
            if tag in _NO_SUFFIX_POS:
                return stem
    return None


def _reading_to_lemma(reading: str) -> str | None:
    """Reconstruct the canonical Apertium-Ido lemma from a `stem<tag1><tag2>...`
    reading. Returns None if no usable POS tag is found."""
    # split off the stem (everything before the first <tag>)
    m = re.match(r'^([^<]+)(.*)$', reading)
    if not m:
        return None
    stem, tagstr = m.group(1), m.group(2)
    tags = _READING_TAG_RE.findall(tagstr)
    # Find the first POS tag — it determines the suffix.
    for tag in tags:
        if tag in _POS_SUFFIX:
            return stem + _POS_SUFFIX[tag]
        if tag in _NO_SUFFIX_POS:
            return stem
    return None


def lemmatize_words(words: Iterable[str], automorf_path: Path,
                    drop_derivable: bool = True) -> dict[str, str]:
    """Run lt-proc once on all words; return {surface -> canonical_lemma}.

    The mapping always has an entry for every input word: lemmatized when
    possible, surface unchanged otherwise. Caller is responsible for any
    downstream deduplication.

    `drop_derivable=True` (default) collapses morphologically-derivable
    surface forms onto their base lemma. e.g. when `kreado` analyzes as
    `kre<vblex><der_act><n>...` AND `kread<n>`, return `krear` instead of
    `kreado` — Apertium's paradigm rules can re-derive `kreado` from `krear`,
    so BERT doesn't need to translate it separately.
    `drop_derivable=False` reverts to the prior behavior (prefer non-derived
    reading when both exist).
    """
    words = list(words)
    if not words:
        return {}

    if not automorf_path.exists():
        raise FileNotFoundError(f"lt-proc analyzer not found: {automorf_path}")

    # Feed one word per line. lt-proc preserves the line structure so we can
    # zip output lines with input words. Words containing characters lt-proc
    # treats as separators (e.g. hyphens) produce multiple `^...$` blocks on
    # their output line — we treat those as unanalyzable.
    payload = '\n'.join(words) + '\n'
    proc = subprocess.run(
        ['lt-proc', str(automorf_path)],
        input=payload, capture_output=True, text=True, check=True,
    )

    out_lines = proc.stdout.split('\n')
    # Drop a trailing empty line caused by the final '\n'.
    if out_lines and out_lines[-1] == '':
        out_lines.pop()

    if len(out_lines) != len(words):
        logger.warning(
            "lt-proc returned %d output lines for %d input words — alignment mismatch",
            len(out_lines), len(words),
        )

    out: dict[str, str] = {}
    for word, line in zip(words, out_lines):
        blocks = re.findall(r'\*?\^[^$]*\$', line)
        if len(blocks) != 1:
            # Word was tokenized into multiple pieces (hyphens, etc.) — can't
            # cleanly recover a lemma; pass surface through.
            out[word] = word
            continue
        parsed = _parse_lt_proc_output(blocks[0])
        if parsed is None:
            out[word] = word
            continue
        surface, readings = parsed
        # PR C: when any reading is a derivation, route to the base lemma.
        # Caller's dedup will collapse onto the base if it's also in vocab.
        if drop_derivable:
            base = _extract_base_from_derivation(readings)
            if base is not None:
                out[word] = base
                continue
        reading = _pick_reading(readings)
        if reading is None:
            out[word] = word
            continue
        lemma = _reading_to_lemma(reading)
        out[word] = lemma if lemma else word

    # Catch any words lt-proc dropped from the output entirely.
    for word in words:
        out.setdefault(word, word)

    return out
