# Use bidix as the BERT alignment seed dictionary

**Status:** plan, not implemented.
**Owner:** open.
**Cost:** code change ~30 lines + one re-run of steps 15→20 (no GPU, ~minutes).
**Expected gain:** materially better BERT translation candidates for non-cognate pairs.

## Motivation

BERT cross-lingual alignment in `15_bert_crosslingual_alignment.py` uses Procrustes rotation between the Ido and Esperanto embedding spaces. Procrustes needs a **seed dictionary** — a set of trusted (Ido, EO) pairs whose embeddings should align after rotation. Quality of the seed dictionary directly determines quality of the alignment, and therefore quality of every BERT-only translation candidate downstream.

### Current seed (cognate heuristic)

`create_seed_dictionary()` in `scripts/15_bert_crosslingual_alignment.py` builds the seed entirely from surface-form similarity:

1. Exact matches: words identical in both vocabularies (`domo == domo`, `libro == libro`).
2. Near matches: SequenceMatcher ratio ≥ 0.7 between non-identical words.
3. Capped at 500 pairs.

This works for cognate-shaped translations (Ido and Esperanto share a lot of Romance/Latin lexicon) but **misses every non-cognate pair**:

| Ido | Esperanto | Cognate seed? |
| --- | --- | --- |
| `domo` | `domo` | ✓ exact |
| `homaro` | `homaro` | ✓ exact |
| `nomo` | `nomo` | ✓ exact |
| `havar` | `havi` | ✗ (verb endings differ) |
| `bona` | `bona` | ✓ exact |
| `nia` | `nia` | ✓ exact |
| `lua` | `lia` | ✗ (different letters in pronoun) |
| `ed` | `kaj` | ✗ (totally different) |
| `od` | `aŭ` | ✗ |
| `kun` | `kun` | ✓ |
| `vidvino` | `vidvino` | ✓ |
| `kreesko` | `kreskoresto` | ✗ |

Most non-cognate function words and many derived forms get no seed coverage. The Procrustes rotation is anchored only on cognate-shaped pairs, so non-cognate translations end up unreliable — which is why ~70% of BERT-only translations were wrong in the 25-article audit (e.g. `donis → domon`, `kartago → goya`).

## Proposed seed (bidix-based)

Use the regenerated bidix (`extractor/dist/bidix_big.json`) as the seed source. Filter to high-confidence pairs:

- Source must include `io_wiktionary` OR `eo_wiktionary` OR `fr_wiktionary_meaning` (i.e. at least one Wiktionary on either side — not BERT-only or en-via-only, to avoid feedback loops).
- One translation per (lemma, pos) — pick the first wiktionary-confirmed EO target.
- Both Ido lemma and EO target must exist in the embedding vocabularies (`ido_vocabulary.txt` and the Esperanto vocab from `models/esperanto_clean__vocab.txt`).

Expected pair count: a few thousand to ~20k Wiktionary-confirmed pairs that are also in vocab. That's 40–400× more anchor data than the current 500.

## Implementation sketch

```python
# In scripts/15_bert_crosslingual_alignment.py

def create_seed_dictionary_from_bidix(bidix_path, ido_vocab, epo_vocab, max_pairs=10000):
    import json
    bidix = json.load(open(bidix_path))
    seeds = []
    ido_set = set(ido_vocab)
    epo_set = set(epo_vocab)
    LOW_QUAL = {'bert_embeddings', 'en_wiktionary_via'}
    for entry in bidix:
        lm = (entry.get('lemma') or '').lower()
        if lm not in ido_set:
            continue
        # pick first wiktionary-confirmed EO target
        for sense in entry.get('senses', []):
            for tr in sense.get('translations', []):
                if tr.get('lang') != 'eo':
                    continue
                eo = (tr.get('term') or '').lower()
                srcs = set(tr.get('sources') or [])
                if not (srcs - LOW_QUAL):
                    continue  # skip low-quality only
                if eo in epo_set:
                    seeds.append((lm, eo))
                    break
            else:
                continue
            break
    return seeds[:max_pairs]
```

CLI flag: `--seed-source {cognate,bidix}` so the cognate path stays available for ablation. If `--seed-source bidix`, also pass `--bidix-path extractor/dist/bidix_big.json`.

## Expected impact (testable)

- Run 15 + 20 with current cognate seeds → save `source_bert_embeddings.cognate.json`
- Run 15 + 20 with bidix seeds → save `source_bert_embeddings.bidix.json`
- Re-run the 25-article translation audit with each → compare clean rates and BERT-only translation accuracy.

The hypothesis is that the bidix-seed run cuts BERT-only error rate from ~70% to materially less, especially for non-cognate function words and derived forms. If it doesn't help (e.g. because the embeddings themselves don't capture the right contrasts), that's also useful information.

## Avoiding feedback loops

The bidix already contains BERT-derived translations (`bert_embeddings` source). If we used the entire bidix as seed, we'd be feeding BERT's prior output back into BERT's alignment, which would entrench errors. The filter `srcs - LOW_QUAL` (drop pairs whose only sources are `bert_embeddings` or `en_wiktionary_via`) breaks the loop: only Wiktionary-confirmed pairs become seeds.

## Why this is a separate initiative

- Doesn't depend on the io.wiktionary parse currently running.
- Doesn't need GPU re-fine-tuning — only the alignment step (15) needs to be re-run.
- Can be done after the current PR chain merges and the 25-article audit baseline is established.
