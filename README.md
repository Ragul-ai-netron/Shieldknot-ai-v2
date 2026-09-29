# ShieldKnot AI v2 — THIRAZEN Demo

ShieldKnot AI is a **defense-only transaction-risk demonstration**. **THIRAZEN** is the branding/parent identity; the AI/product name remains **ShieldKnot AI**.

## What is actually implemented

- Fraud transaction scoring: `POST /api/score`
- Return-risk scorer: `POST /api/return-risk`
- Fraud-spike detector: `GET /api/spike`
- Abuse-ring sentinel: `GET /api/abuse-ring` for observed shared device/IP groups
- Chargeback evidence responder: `GET/POST /api/chargeback-evidence/{transaction_id}`
- Transaction investigation: `GET /api/investigate/{transaction_id}`
- Deterministic response policy: `GET /api/response-policy`
- Local outcome reward calculation: `POST /api/outcomes`
- Model/held-out metrics: `GET /api/model`
- Truthful component status: `GET /api/system-status`
- Seeded local demo authentication: `/api/auth/demo-users` and `/api/auth/login`
- Responsive PC/tablet/mobile UI
- THIRAZEN branding asset at `/static/thirazen-logo.png`

## Demo incident workflow

The local demo includes a deterministic **demo incident engine** so the Incident Queue is populated every time without pretending that a real production alert occurred.

The four scenarios are explicitly labelled `SIMULATED DEMO SCENARIO`:

1. Fraud-spike detector demonstration
2. Elevated return-risk pattern
3. Chargeback evidence review
4. Connected-risk cluster demonstration

Each scenario references synthetic dataset transactions and can be opened in Investigation. The workflow demonstrates:

`detector → incident → evidence → investigation → response policy → human review → outcome`

Recorded outcomes are written to `data/outcomes.jsonl`. `POST /api/demo/reset` resets the demo outcome state without modifying the synthetic transaction dataset.

## What is not included

PostgreSQL, Redis, Redpanda/Kafka and external LLM services are **not** part of this repository. The UI does not claim they are active.

The reward model is a transparent local outcome-reward calculator, not a separately trained neural reward model.

## Run

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/`.

## Demo authentication

Selecting `analyst`, `lead_analyst`, or `admin` fills the local demo username and password. The password input is masked by default and has a show/hide control.

These are demo credentials only; this is not production authentication.

## Safety boundary

The application is intentionally defense-only. Recommendations require human review and the response policy never performs autonomous blocking or dispute submission.
