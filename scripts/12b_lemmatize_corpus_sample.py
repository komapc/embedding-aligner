#!/usr/bin/env python3
"""Lemmatize a sample of the Ido training corpus for the PR D Colab experiment.

Picks the first N sentences from data/raw/ido_corpus.txt, lemmatizes each
token via lt-proc against apertium-ido/ido.automorf.bin, and writes:

  data/processed/ido_corpus_lemma_30k.txt   (lemmatized text — train on this)
  data/processed/ido_corpus_surface_30k.txt (same sentences, surface forms — control)

The two files have the same lines so the experiment can train two models
(surface vs lemma) on identical data scope.

Reuses scripts/lib/ido_lemmatize.lemmatize_words.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib.ido_lemmatize import lemmatize_words


def main() -> int:
    ap = argparse.ArgumentParser()
    base = Path(__file__).resolve().parents[1]
    ap.add_argument("--input", type=Path, default=base / "data/raw/ido_corpus.txt")
    ap.add_argument("--surface-out", type=Path, default=base / "data/processed/ido_corpus_surface_30k.txt")
    ap.add_argument("--lemma-out", type=Path, default=base / "data/processed/ido_corpus_lemma_30k.txt")
    ap.add_argument("--ido-automorf", type=Path, default=base.parent.parent / "apertium-ido/ido.automorf.bin")
    ap.add_argument("--n", type=int, default=30000, help="Number of sentences to take")
    ap.add_argument("--batch-tokens", type=int, default=2000, help="Lemmatize this many tokens per lt-proc call")
    args = ap.parse_args()

    print(f"Reading first {args.n:,} sentences from {args.input}...")
    with open(args.input, encoding="utf-8") as f:
        sentences = []
        for i, line in enumerate(f):
            if i >= args.n:
                break
            sentences.append(line.rstrip("\n"))
    print(f"  loaded {len(sentences):,} sentences")

    # Tokenize on whitespace, dedupe vocabulary, lemmatize once
    print("Collecting unique tokens...")
    unique_tokens: set[str] = set()
    for s in sentences:
        unique_tokens.update(s.split())
    tokens = sorted(unique_tokens)
    print(f"  {len(tokens):,} unique tokens")

    print(f"Lemmatizing via lt-proc ({args.ido_automorf})...")
    # lt-proc only handles word-shaped input. Pre-filter to alphabetic tokens;
    # non-alphabetic ones (punctuation, numbers, mixed) pass through unchanged.
    import re
    alpha_re = re.compile(r"^[A-Za-z\-]+$")
    alpha_tokens = [t for t in tokens if alpha_re.match(t) and len(t) >= 2]
    print(f"  {len(alpha_tokens):,} alphabetic tokens to lemmatize ({len(tokens) - len(alpha_tokens):,} skipped)")

    lemma_map: dict[str, str] = {}
    for i in range(0, len(alpha_tokens), args.batch_tokens):
        chunk = alpha_tokens[i : i + args.batch_tokens]
        m = lemmatize_words(chunk, args.ido_automorf)
        lemma_map.update(m)
        if (i // args.batch_tokens) % 5 == 0:
            print(f"  {i + len(chunk):,}/{len(alpha_tokens):,} tokens...")

    print(f"Writing surface-form sample to {args.surface_out}...")
    args.surface_out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.surface_out, "w", encoding="utf-8") as f:
        for s in sentences:
            f.write(s + "\n")

    print(f"Writing lemmatized sample to {args.lemma_out}...")
    with open(args.lemma_out, "w", encoding="utf-8") as f:
        for s in sentences:
            lemmatized = " ".join(lemma_map.get(tok, tok) for tok in s.split())
            f.write(lemmatized + "\n")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
