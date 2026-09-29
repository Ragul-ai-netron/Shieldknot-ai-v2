# ShieldKnot AI v2

<p align="center">
  <img src="static/ShieldKnot_AI_V2_Proper_Banner.gif" alt="ShieldKnot AI v2" width="900">
</p>

<p align="center">
  <strong>DEFENSIVE FRAUD INTELLIGENCE</strong><br>
  <em>AI works with you. People stay in control.</em>
</p>

---

## THIRAZEN™

**Turning ideas into products.**

## ShieldKnot AI

**Defensive Fraud Intelligence**

ShieldKnot AI v2 is a defensive transaction-risk demonstration built to detect suspicious patterns, investigate evidence, explain risk signals, and keep consequential responses under human control.

> **Human review remains required for consequential actions.**

## What the demo demonstrates

**Detect → Investigate → Explain → Human Review → Respond**

### Implemented defensive services

| Component | Purpose |
|---|---|
| Fraud-Spike Detector | Detects unusual transaction-risk spikes. |
| Return-Risk Scorer | Scores return-related risk using the local model/data pipeline. |
| Chargeback Evidence Responder | Prepares evidence for human review; it does not autonomously submit disputes. |
| Abuse-Ring Sentinel | Surfaces shared device/IP patterns and related demo incidents. |
| Fraud Model | Local transaction-risk model used by the scoring pipeline. |
| Checkpoint | Local model checkpoint artifact. |
| Reward Model | Transparent local reward/outcome calculator. |
| Response Policy | Deterministic defensive policy with human-review requirements. |
| Demo Incident Engine | Generates deterministic simulated incidents for demonstrations. |

## Demo incidents

The project includes deterministic simulated scenarios so the complete workflow can be demonstrated without relying on live fraud:

- `SPIKE-DEMO-001` — fraud-spike scenario
- `RETURN-DEMO-002` — return-risk scenario
- `CHARGEBACK-DEMO-003` — chargeback-evidence scenario
- `ABUSE-DEMO-004` — abuse-ring scenario

These are explicitly marked **SIMULATED DEMO SCENARIO**.

## System status

The application reports component status from the backend implementation.

Services such as PostgreSQL, Redis, Redpanda, and an external LLM are not presented as active infrastructure unless they are actually configured and implemented.

## Safety design

- No autonomous blocking or punishment.
- No autonomous chargeback submission.
- Human review is required for consequential responses.
- Risk explanations and evidence are surfaced for investigators.
- Demo incidents are synthetic and clearly identified.
- The response policy is deterministic and inspectable.
- The project does not claim production infrastructure that is not present.

## API

The FastAPI backend includes:

- `GET /api/health`
- `GET /api/system-status`
- `GET /api/auth/demo-users`
- `POST /api/auth/login`
- `GET /api/model`
- `POST /api/score`
- `GET /api/transactions`
- `GET /api/spike`
- `GET /api/abuse-ring`
- `GET /api/return-risk`
- `POST /api/return-risk`
- `GET /api/investigate/{transaction_id}`
- `GET /api/chargeback-evidence/{transaction_id}`
- `POST /api/chargeback-evidence/{transaction_id}/respond`
- `GET /api/response-policy`
- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- `GET /api/overview`
- `POST /api/demo/reset`
- `POST /api/outcomes`

## 🚀 Live Demo

**[Open ShieldKnot AI v2 Live Demo](https://ragul-ai-netron.github.io/shieldknot-ai-v2-live/)**

The public demo runs as a browser-based GitHub Pages deployment using synthetic demo data.

**Workflow:** Detect → Investigate → Explain → Human Review → Respond

## Run locally

### Python

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

### Docker

```bash
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000
```

## Demo accounts

| Role | Username | Password |
|---|---|---|
| Analyst | `analyst@demo.local` | `analyst-demo-2026` |
| Lead Analyst | `lead@demo.local` | `lead-demo-2026` |
| Admin | `admin@demo.local` | `admin-demo-2026` |

These are demo-only credentials.

## Project philosophy

> **Build → Break → Fix → Ship**

Build systems. Test them. Fix what breaks. Ship working products.

---

**ShieldKnot AI v2**  
**THIRAZEN™**  
*Turning ideas into products.*

