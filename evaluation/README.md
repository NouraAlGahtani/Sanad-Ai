# SANAD held-out evaluation

20 seeded, frozen synthetic incident cases. They are new **instances of supported fault categories**, not evidence of open-world detection of arbitrary novel attacks. `heldout_cases.json` contains the predeclared expected outcomes. Do not edit it after seeing results.

## Run (from project root)

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest -q
python3 evaluation/run_heldout.py
```

The above evaluates the full engine in deterministic mode by default. To evaluate Qwen3, start Ollama and run:

```bash
ollama pull qwen3:4b
SANAD_USE_OLLAMA=1 OLLAMA_MODEL=qwen3:4b python3 evaluation/run_heldout.py --require-ai
```

Review `evaluation/results/summary.json`, `results.csv`, and `details.json`. The runner records AI versus fallback/state-guard attribution; a high pass rate with fallback is **not** evidence of model generalization. Each case uses an isolated sandbox and database.

## Methodology and limitations

Cases were generated with fixed seed 20261030 and frozen before execution, varying service identifiers, health observations, configuration faults, queue backlogs, request rates, authentication failures, and logs. Expected classifications, ordered actions and outcomes are declared before evaluation. No training or tuning on these cases. The synthetic cases are variants of known incident families; test novel incident families separately before claiming broad generalization.

The `evaluation_event` keyword is an internal engine test entry point only; the existing Flask API remains restricted to its original registered scenarios. No production infrastructure is affected.
