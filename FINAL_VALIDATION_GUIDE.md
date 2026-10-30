# SANAD AI — Final Validation Pack

This pack retains the working v6 application and adds `evaluation/final_validation.py` plus `validation_report.json`.

## Run

```bash
python3 -m pytest -q
python3 -m py_compile app.py
python3 -m evaluation.final_validation --output validation_report.json
SANAD_USE_OLLAMA=1 OLLAMA_MODEL=qwen3:4b python3 -m evaluation.compare_memory --live-ai --output live_comparison.json
SANAD_USE_OLLAMA=1 OLLAMA_MODEL=qwen3:4b python3 app.py
```

## What the evaluation establishes

- 40 seeded synthetic training sequences; 80 *separate* seeded synthetic test sequences. Calibration is frozen throughout the test. Compare threshold-warning accuracy, missed breaches and mean absolute error.
- Two synthetic security scenarios test that the forecast cycle escalates without executing disruptive recovery.
- Existing memory comparison tests AI proposal attribution and policy gating. It does **not** establish that memory improves AI recovery decisions.
- The existing automated suite covers 35 checks.

## Important limitations

- The generator intentionally adds a systematic +25 requests/min shift. The adaptive bias corrector is expected to improve on this specific pattern. These numbers must not be described as production, representative real-world, or broad held-out AI performance.
- Forecast decisions are observation/escalation only. No automated preventive infrastructure recovery is implemented.
- `ollama_requested` does not prove the model was used: inspect `proposal_source` in the live comparison report.
- Run the application and scenarios on the actual Mac before presenting. `python -m pytest` alone does not verify Flask route startup.

## Suggested judge demonstration (2–3 minutes)

1. **Problem:** Enterprise service recovery is slow, and unguarded AI recovery can destroy incident evidence.
2. **Detection:** Show a service outage and a suspicious intrusion scenario.
3. **Forecast:** Show the four-step telemetry demonstration and explain next-sample trend extrapolation and outcome feedback.
4. **Recovery and safety:** Show authorized sandbox service restart, then high-risk preservation/escalation with no restart.
5. **Learning:** Show incident memory, the frozen synthetic comparison, and explain exactly what is learned (historical outcome statistics and forecast bias), and what is not (Qwen weights).
6. **Evidence:** Show the forensic record and run `python3 -m pytest -q`.

## Judging criteria evidence

- **Task performance:** Verified sandbox recoveries and synthetic forecast test; additional varied unseen incident tests still needed.
- **Robustness/adaptation:** Safety challenge and adaptive bias-correction comparison.
- **Evaluation/iteration:** Reproducible seeded comparison, test suite, frozen test calibration.
- **Technical judgment:** Independent deterministic policy; no speculative disruptive actions.
- **Engineering quality:** Modular Python/Flask code, SQLite audit records, test command.
- **Communication:** Dashboard plus concise, qualified results.
