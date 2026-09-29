# ShieldKnot AI v2 — Rework notes

## Branding
- Product/AI name remains **ShieldKnot AI**.
- **THIRAZEN** is branding only and is shown as `ShieldKnot AI by THIRAZEN`.
- Added the supplied THIRAZEN logo to `static/thirazen-logo.png`.

## Demo incidents
- Added a deterministic local demo incident engine.
- Four labelled synthetic scenarios are available on startup:
  - Fraud-spike detector demonstration
  - Elevated return-risk pattern
  - Chargeback evidence review
  - Connected-risk cluster demonstration
- Incidents reference synthetic dataset transactions.
- Completed outcomes persist in `data/outcomes.jsonl`.
- `/api/demo/reset` resets demo outcomes.

## Truthful service status
- Added `demo_incident_engine` to the actual backend status.
- PostgreSQL, Redis, Redpanda/Kafka and external LLM services remain absent because they are not implemented in this repository.
- No UI status card claims those services are active.

## UI
- Responsive layout for desktop, tablet and mobile.
- Mobile navigation drawer.
- THIRAZEN branding in navigation/login/footer.
- Demo environment labels.
- Masked password with show/hide control.
- Incident queue now has populated demo scenarios and clearer evidence.
- Investigation view shows detector evidence, risk, policy and human-review safeguards.
- Improved mobile tables and cards.

## Verification
- 6 automated tests pass.
- Python modules compile successfully.
- Frontend JavaScript passes Node syntax validation.
