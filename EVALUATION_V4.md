# SANAD controlled learning comparison

Run `python3 -m pytest -q` and `python3 -m evaluation.compare_memory --output evaluation_report.json`.

For a live Qwen3 comparison, run `SANAD_USE_OLLAMA=1 OLLAMA_MODEL=qwen3:4b python3 -m evaluation.compare_memory --live-ai --output live_comparison.json`. Verify `proposal_source` is `ollama` in both arms.

The comparison uses fresh temporary SQLite databases and sandbox directories. The memory-enabled arm is seeded with two successful service-outage incidents; the baseline arm is unseeded. It tests memory availability, resulting actions, outcomes, and whether an unsafe restart is denied in a high-risk scenario. It is **not** a blinded generalization benchmark, and the seeded incidents overlap the evaluated scenario. Because the current agent prompt and deterministic state guards already prescribe restart_service for service_fault, both arms may choose the same action. Do not claim memory improved recovery success unless a separately designed evaluation demonstrates it.
