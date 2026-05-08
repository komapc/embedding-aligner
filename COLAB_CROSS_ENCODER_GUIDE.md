# Cross-encoder Training (Colab)

Train the IO↔EO cross-encoder re-ranker on Google Colab's free T4 GPU.
~30–45 minutes wall-clock end-to-end.

## One-click open

[Open `train_cross_encoder.ipynb` in Colab](https://colab.research.google.com/github/komapc/embedding-aligner/blob/master/notebooks/train_cross_encoder.ipynb)

That's it. Set Runtime → T4 GPU, then Runtime → Run all. Total interaction:
~3 clicks (open, runtime change, run all). Trained model lands in your
browser's Downloads folder as a ~500 MB tarball.

## What the notebook does

| Step | What | Time |
|---|---|---|
| 1 | `nvidia-smi` GPU check | 2 s |
| 2 | Clone repo + install deps | 30 s |
| 3 | `wget` extractor inputs from release asset | 5 s |
| 4 | Run `scripts/16_train_cross_encoder.py` (3 epochs, FP16) | ~25–35 min |
| 5 | Tar + browser download trained model | ~30 s |

## Acceptance gate

After training, the notebook logs `Final held-out metrics: {...}`.
Target: **F1 ≥ 0.85** on the 200-pair held-out set. Below that, the seed
data or hard-negative construction needs revisiting before continuing
to PR B.

## After download — install on your laptop

```bash
mkdir -p ~/projects/apertium-dev/projects/embedding-aligner/models
tar xzf ~/Downloads/cross-encoder-io-eo.tar.gz \
  -C ~/projects/apertium-dev/projects/embedding-aligner/
ls ~/projects/apertium-dev/projects/embedding-aligner/models/cross-encoder-io-eo/
```

Then PR B's `scripts/19_cross_encoder_rerank.py` (forthcoming) consumes it.

## Tips

- **Don't close the tab.** Colab disconnects after ~90s of inactivity.
- If the runtime dies mid-training, the last `save_strategy='epoch'`
  checkpoint lives in `models/cross-encoder-io-eo/checkpoint-N/`. Restart
  the cell with `Trainer.train(resume_from_checkpoint=True)`.
- For a smaller / faster smoke test (~5 min instead of 30) — change the
  step-4 cell to `--epochs 1 --batch-size 16` first, just to verify the
  end-to-end pipeline runs cleanly.

## Updating the release asset

If `bilingual_raw.json` or `io_eo_langlinks.json` change in extractor:

```bash
cd ~/projects/apertium-dev/extractor
tar czf /tmp/cross_encoder_inputs.tar.gz \
  work/bilingual_raw.json work/io_eo_langlinks.json

cd ~/projects/apertium-dev/projects/embedding-aligner
gh release upload cross-encoder-inputs /tmp/cross_encoder_inputs.tar.gz --clobber
```
