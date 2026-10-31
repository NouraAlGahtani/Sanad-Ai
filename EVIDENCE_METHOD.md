# SANAD AI — Evidence and claims register

The figures in `docs/assets/evidence-*.svg` are derived from terminal summaries supplied by the developer on 2026-10-31. They are not generated from archived raw run files in this package.

## What is supported
- 20/20 held-out-instance pass, Qwen involved in all 20, zero fallback, mean 1598.32 ms.
- 12/12 adversarial pass after safety gate revision, Qwen involved in all 12, zero fallback, mean 1569.12 ms.
- 9/12 adversarial before revision, same dataset hash, mean 1576.01 ms.
- Proposal alignment 3/5 held-out and 2/7 adversarial, total 5/12.

## What is not established
- Unseen fault-family performance; cross-system comparison; cost per incident; statistical confidence intervals; production reliability; LLM advantage over deterministic baseline.

## Next tests
- Commit immutable new-family benchmark with hidden labels and hashes.
- Run deterministic baseline and full SANAD with identical inputs, budgets, and scoring.
- Inspect misclassifications, proposal-policy disagreement, unsafe actions, and over-escalation.
- Repeat seeds and report confidence intervals where sample size supports them.
