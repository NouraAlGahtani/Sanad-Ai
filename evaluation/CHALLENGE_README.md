# SANAD adversarial challenge (post-hoc development set)

**Disclosure:** Designed after viewing the original held-out results. These 12 synthetic cases are NOT a clean independent holdout or proof of unseen fault-family generalization. Keep the original 20-case results unchanged. No code changes to SANAD engine are included.

Run from the project root:

```bash
export SANAD_USE_OLLAMA=1 OLLAMA_MODEL=qwen3:4b OLLAMA_TIMEOUT=180
python3 evaluation/run_challenge.py --require-ai
```

Results are written to `evaluation/challenge_results/`. Nonzero exit means a test failed; send results regardless. Compare with deterministic fallback by running `SANAD_USE_OLLAMA=0 python3 evaluation/run_challenge.py` **after saving AI results elsewhere**, since each run overwrites the output directory.

The challenge stresses mixed faults, uncertain evidence, two-step recovery, and untrusted log text. Some expectations are deliberately debatable (notably X11), so report per-case outcomes and review the oracle, not just aggregate pass rate.

**Important:** `AI=True` only indicates model involvement, not that the model selected the final action; engine state guards and policy may override it. Report proposal alignment separately. No production services are modified.
