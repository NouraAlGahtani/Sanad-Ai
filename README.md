# SANAD AI | سند

**Autonomous Recovery. Trusted by Design.**

SANAD is a security-aware incident investigation and recovery prototype built for the HUMAIN Future AI Builders Hackathon (2026). It combines local language-model reasoning, deterministic execution controls, and independent verification in a controlled enterprise incident simulator.

## Architecture

- **Incident ingestion:** Five reproducible enterprise fault and security scenarios.
- **Investigation:** Read-only health, configuration, metrics, and security tools; Qwen3 can select investigation tools through Ollama.
- **Assessment:** Deterministic fault classification and security-risk evaluation.
- **Recovery planning:** Qwen3 proposes an allowlisted action based on observed evidence and current state.
- **Safety enforcement:** Independent policy and state guards evaluate and, where necessary, correct or block proposals.
- **Execution:** Authorized actions affect only the isolated file-backed simulator.
- **Verification and accountability:** Post-action health checks, SHA-256 evidence fingerprints, and SQLite audit records.

## Requirements

- Python 3.10+
- Optional: Ollama with the `qwen3:4b` model for AI-driven investigation and proposals

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## Run with local AI

Install Ollama, then:

```bash
ollama pull qwen3:4b
export SANAD_USE_OLLAMA=1
export OLLAMA_MODEL=qwen3:4b
export OLLAMA_TIMEOUT=180
python3 app.py
```

Open `http://127.0.0.1:5000`.

Without Ollama, `python3 app.py` starts the deterministic fallback mode. The dashboard attributes each proposal to its actual source.

## Test

```bash
python3 -m pytest -q
```

## Scenario matrix

| Scenario | Expected behavior |
| --- | --- |
| Invalid deployment configuration | Restore valid configuration and verify health |
| Cascading worker and queue failure | Restart worker, drain backlog, verify health |
| Service outage | Restart service and verify health |
| Suspected intrusion | Preserve evidence and escalate |
| Ambiguous incident | Escalate when diagnosis is uncertain |

## API

`GET /api/scenarios` · `POST /api/run` · `GET /api/history` · `GET /api/health` · `GET /api/demo-health`

## Scope and safety

SANAD is a **local, file-backed simulation**, not a production incident-response controller. It does not execute arbitrary model-generated commands or change external services. Classification and authorization are deterministic; Qwen3 supplies investigation choices and recovery proposals when enabled. Reported recovery outcomes are verified against the simulator state, not live infrastructure. Escalation confirms a safety decision, not restoration of service.

## Identity

The original SANAD golden falcon head is a custom SVG vector mark inspired by Saudi falconry heritage.


### Attribution
Designed & Developed by Noura AlQahtani · HUMAIN Future AI Builders Hackathon 2026.
