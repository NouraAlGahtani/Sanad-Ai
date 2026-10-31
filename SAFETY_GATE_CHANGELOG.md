# Safety gate correction — post-challenge development change

Previous live Qwen challenge result: 9/12; failed X05, X06, X11. The controller previously allowed `no_action` for medium/high-risk incidents. This revision denies `no_action` (and recovery actions) for any non-low-risk incident, causing verified `blocked_and_escalated` behavior through the existing Engine path. It does not change assessment classifications, model prompts, expected labels, or benchmark datasets.

Local tests: `python -m unittest discover -s tests -q` passed 11 tests. Deterministic smoke run: 12/12 with AI disabled; **not a live-Qwen result**. Run both `evaluation/run_challenge.py --require-ai` and `evaluation/run_heldout.py --require-ai` on a machine with Ollama to establish new live results. Retain the original 9/12 as the pre-change result.

**Known evaluation concern:** X11 describes a healthy service with normal telemetry but expects escalation because its log says 'conservative escalation expected'. This is not strong independent ground truth. Do not advertise X11 as proof of attack detection or treat its expected action as necessarily optimal. Review its oracle separately and use a newly frozen independent benchmark for generalization claims.

**Additional caveat:** This is a risk-based policy gate, not a guarantee that every risky event will be classified correctly. The current model may still propose `no_action`; the policy prevents silent inaction for incidents assessed as non-low risk. Proposal alignment must be reported separately.
