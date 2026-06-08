#!/usr/bin/env python3
"""Build a clean Ido text corpus from an io.wikipedia XML dump.

Streams the (bz2) dump, keeps main-namespace articles (ns 0, non-redirect),
strips wikicode via mwparserfromhell, and writes one cleaned paragraph per
line. This is the MLM fine-tuning input for `13_finetune_bert.py`.

Replaces the previously untracked, hand-built corpus artifact so the
fine-tuning input is fully regeneratable from the dump.

Usage:
    python3 scripts/build_ido_corpus.py \
        --dump ../../extractor/data/raw/iowiki-latest-pages-articles.xml.bz2 \
        --output data/processed/ido_wikipedia_corpus.txt
"""
from __future__ import annotations

import argparse
import bz2
import logging
import re
from pathlib import Path
from xml.etree.ElementTree import iterparse

import mwparserfromhell

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# MediaWiki dumps namespace every tag; strip it to match bare local names.
_NS_RE = re.compile(r'\{.*\}')
_WS_RE = re.compile(r'\s+')
# File/Image links + <ref>…</ref> survive strip_code as caption/footnote junk
# (`thumb|320px|...`). Remove them from the raw wikitext before parsing.
_FILE_LINK_RE = re.compile(r'\[\[\s*(?:File|Image|Imajo|Dosiero|Arkivo)\s*:.*?\]\]',
                           re.IGNORECASE | re.DOTALL)
_REF_RE = re.compile(r'<ref[^>]*>.*?</ref>|<ref[^>]*/>', re.IGNORECASE | re.DOTALL)
# Residual layout tokens that mark a fragment as non-prose.
_MARKUP_TOKEN_RE = re.compile(r'(?:\bthumb\b|\b\d+px\b|\{\{|\}\}|\[\[|\]\]|\bISBN\b|https?://|\|)')
# Sentence splitter: end punctuation + space + capital / digit start.
_SENT_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-ZĈĜĤĴŜŬ0-9])')
_MIN_WORDS = 4
_MAX_WORDS = 120


def _local(tag: str) -> str:
    return _NS_RE.sub('', tag)


def clean_wikitext(text: str) -> list[str]:
    """Strip wikicode to clean, sentence-per-line prose.

    Matches the format `13_finetune_bert.load_corpus` expects (one sentence
    per line, truncated at 256 tokens): paragraphs are sentence-split, and
    fragments still carrying layout markup are dropped.
    """
    text = _FILE_LINK_RE.sub(' ', text)
    text = _REF_RE.sub(' ', text)
    try:
        plain = mwparserfromhell.parse(text).strip_code(normalize=True, collapse=True)
    except Exception:
        return []
    out = []
    for para in plain.split('\n'):
        para = _WS_RE.sub(' ', para).strip()
        if not para:
            continue
        for sent in _SENT_SPLIT_RE.split(para):
            sent = sent.strip()
            n = len(sent.split())
            if n < _MIN_WORDS or n > _MAX_WORDS:
                continue
            if _MARKUP_TOKEN_RE.search(sent):
                continue
            out.append(sent)
    return out


def iter_articles(dump_path: Path):
    """Yield (title, wikitext) for main-namespace, non-redirect pages."""
    opener = bz2.open if dump_path.suffix == '.bz2' else open
    with opener(dump_path, 'rb') as fh:
        title = ns = text = None
        is_redirect = False
        for event, elem in iterparse(fh, events=('start', 'end')):
            tag = _local(elem.tag)
            if event == 'end':
                if tag == 'title':
                    title = elem.text
                elif tag == 'ns':
                    ns = elem.text
                elif tag == 'redirect':
                    is_redirect = True
                elif tag == 'text':
                    text = elem.text
                elif tag == 'page':
                    if ns == '0' and not is_redirect and text:
                        yield title, text
                    title = ns = text = None
                    is_redirect = False
                    elem.clear()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    here = Path(__file__).resolve().parent.parent
    ap.add_argument('--dump', type=Path,
                    default=here.parents[1] / 'extractor' / 'data' / 'raw'
                    / 'iowiki-latest-pages-articles.xml.bz2')
    ap.add_argument('--output', type=Path,
                    default=here / 'data' / 'processed' / 'ido_wikipedia_corpus.txt')
    args = ap.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    n_articles = n_lines = n_words = 0
    with open(args.output, 'w', encoding='utf-8') as out:
        for title, wikitext in iter_articles(args.dump):
            lines = clean_wikitext(wikitext)
            if not lines:
                continue
            n_articles += 1
            for line in lines:
                out.write(line + '\n')
                n_lines += 1
                n_words += len(line.split())
            if n_articles % 5000 == 0:
                logger.info("  %d articles, %d lines so far...", n_articles, n_lines)

    logger.info("Wrote %s", args.output)
    logger.info("  articles kept: %d | lines: %d | words: %d", n_articles, n_lines, n_words)


if __name__ == '__main__':
    main()
