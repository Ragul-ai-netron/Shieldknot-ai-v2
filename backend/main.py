from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import socket
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ml.scoring import score_transaction, score_many, load_model

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "transactions.csv"
METRICS_PATH = ROOT / "models" / "metrics.json"
MODEL_PATH = ROOT / "models" / "fraud_model.joblib"
OUTCOME_LOG = ROOT / "data" / "outcomes.jsonl"
DEMO_INCIDENT_CACHE: list[dict[str, Any]] | None = None

app = FastAPI(
    title="ShieldKnot AI v2",
    version="2.1.0",
    description="Defense-only transaction risk and investigation API. UI status is derived from implemented backend capabilities.",
)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def dashboard():
    return FileResponse(ROOT / "index.html")


class Transaction(BaseModel):
    transaction_id: str = "TXN-LIVE"
    amount: float = Field(gt=0)
    velocity_1h: int = Field(ge=0)
    velocity_24h: int = Field(ge=0)
    device_reuse_24h: int = Field(ge=0)
    account_age_days: float = Field(ge=0)
    geo_distance_km: float = Field(ge=0)
    chargeback_history: int = Field(ge=0)
    return_rate: float = Field(ge=0, le=1)
    new_device: int = Field(ge=0, le=1)
    ip_risk: float = Field(ge=0, le=1)
    payment_risk: float = Field(ge=0, le=1)
    hour_risk: float = Field(ge=0, le=1)
    merchant_risk: float = Field(ge=0, le=1)
    amount_zscore: float = 0


class Outcome(BaseModel):
    incident_id: str
    recommendation: str
    outcome: str
    fraud_amount_inr: float = 0
    false_positive_cost_inr: float = 0
    reviewer: str = "authorized-reviewer"


class LoginRequest(BaseModel):
    username: str
    password: str
    role: str


DEMO_USERS = {
    "analyst": {"username": "analyst@demo.local", "password": "analyst-demo-2026"},
    "lead_analyst": {"username": "lead@demo.local", "password": "lead-demo-2026"},
    "admin": {"username": "admin@demo.local", "password": "admin-demo-2026"},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_df() -> pd.DataFrame:
    if not DATA_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(DATA_PATH)


def score_threshold() -> float:
    try:
        return float(json.loads(METRICS_PATH.read_text()).get("threshold", 0.5))
    except Exception:
        return 0.5


def response_policy(risk_score: float) -> dict:
    """Implemented deterministic safeguard policy; never auto-blocks."""
    if risk_score >= 0.80:
        recommendation = "human_escalation"
        band = "critical"
    elif risk_score >= 0.60:
        recommendation = "manual_review"
        band = "high"
    elif risk_score >= 0.35:
        recommendation = "enhanced_monitoring"
        band = "medium"
    else:
        recommendation = "no_action"
        band = "low"
    return {
        "engine": "deterministic_local",
        "risk_band": band,
        "recommendation": recommendation,
        "auto_block": False,
        "human_review_required": True,
        "status": "active",
    }


def reward_score(outcome: str, fraud_amount: float, false_positive_cost: float) -> float:
    """Small, transparent local outcome reward; weights are explicit and testable."""
    fraud_loss_weight = 1.0
    fp_weight = 0.15
    outcome_factor = {
        "fraud_prevented": 1.0,
        "partial": 0.4,
        "fraud_loss": -1.0,
        "false_positive": -1.0,
    }.get(outcome, 0.0)
    value = outcome_factor * fraud_loss_weight * math.log1p(max(fraud_amount, 0))
    value -= fp_weight * math.log1p(max(false_positive_cost, 0))
    return round(float(value), 6)


def socket_reachable(host: str, port: int, timeout: float = 0.35) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def implemented_components() -> dict:
    model_loaded = MODEL_PATH.exists()
    try:
        load_model()
        model_loaded = True
    except Exception:
        model_loaded = False

    # These are intentionally reported only when the corresponding implementation exists.
    components = {
        "fraud_model": {"status": "active" if model_loaded else "unavailable", "detail": "models/fraud_model.joblib"},
        "checkpoint": {"status": "active" if model_loaded else "unavailable", "detail": "loaded model bundle"},
        "return_risk_scorer": {"status": "active", "detail": "deterministic local scorer"},
        "fraud_spike_detector": {"status": "active", "detail": "risk-density window comparison"},
        "chargeback_evidence_responder": {"status": "active", "detail": "structured evidence package"},
        "abuse_ring_sentinel": {"status": "active", "detail": "shared device/IP connected grouping"},
        "response_policy": {"status": "active", "detail": "deterministic, human-review required"},
        "reward_model": {"status": "active", "detail": "outcome reward calculator"},
        "demo_incident_engine": {"status": "active", "detail": "deterministic synthetic incident scenarios backed by dataset transactions"},
    }
    return components


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "shieldknot-v2", "time": now_iso()}


@app.get("/api/system-status")
def system_status():
    components = implemented_components()
    active = [k for k, v in components.items() if v["status"] == "active"]
    unavailable = [k for k, v in components.items() if v["status"] not in {"active"}]
    return {
        "time": now_iso(),
        "service": "shieldknot-v2",
        "components": components,
        "active_count": len(active),
        "non_active": unavailable,
    }


@app.get("/api/auth/demo-users")
def demo_users():
    return {role: {"username": value["username"], "password": value["password"]} for role, value in DEMO_USERS.items()}


@app.post("/api/auth/login")
def login(body: LoginRequest):
    user = DEMO_USERS.get(body.role)
    if not user or user["username"] != body.username or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid demo credentials")
    return {"authenticated": True, "role": body.role, "username": body.username}


@app.get("/api/model")
def model_info():
    if not METRICS_PATH.exists():
        load_model()
    return json.loads(METRICS_PATH.read_text())


@app.post("/api/score")
def score(tx: Transaction):
    result = score_transaction(tx.model_dump())
    return {
        "transaction_id": tx.transaction_id,
        **result,
        "response_policy": response_policy(float(result["risk_score"])),
    }


@app.get("/api/transactions")
def transactions(limit: int = 20):
    df = load_df()
    if df.empty:
        return []
    df = df.tail(max(1, min(limit, 100)))
    out = []
    for _, row in df.iterrows():
        raw = row.to_dict()
        scored = score_transaction(raw)
        out.append({
            "transaction_id": str(raw["transaction_id"]),
            "amount": float(raw["amount"]),
            "risk_score": scored["risk_score"],
            "risk_band": scored["risk_band"],
        })
    return out[::-1]


def spike_result() -> dict:
    df = load_df()
    if df.empty:
        return {"status": "no_data"}
    rows = df.tail(1000).to_dict("records")
    scores = score_many(rows)
    recent = scores[-100:]
    baseline = scores[:-100]
    threshold = score_threshold()
    recent_density = sum(x >= threshold for x in recent) / max(len(recent), 1)
    baseline_density = sum(x >= threshold for x in baseline) / max(len(baseline), 1)
    lift = recent_density / max(baseline_density, 0.001)
    severity = "critical" if lift >= 3 else "high" if lift >= 2 else "medium" if lift >= 1.4 else "low"
    return {
        "recent_high_risk_density": round(recent_density, 4),
        "baseline_high_risk_density": round(baseline_density, 4),
        "density_lift": round(lift, 2),
        "severity": severity,
        "threshold": threshold,
        "incident_created": bool(lift >= 1.4),
        "status": "active",
    }


@app.get("/api/spike")
def spike():
    return spike_result()


@app.get("/api/abuse-ring")
def abuse_ring():
    """Return observed shared-device/IP groups. Demo incidents are handled separately."""
    df = load_df()
    if df.empty:
        return {"rings": [], "status": "no_data"}
    rows = df.tail(2000).to_dict("records")
    scores = score_many(rows)
    by_key: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row, risk in zip(rows, scores):
        if risk < 0.7:
            continue
        for key_name in ("device_id", "ip_id"):
            key = str(row.get(key_name, "")).strip()
            if key and key.lower() != "nan":
                by_key[f"{key_name}:{key}"].append((str(row["transaction_id"]), risk))
    rings = []
    for key, members in by_key.items():
        if len(members) >= 3:
            kind, value = key.split(":", 1)
            rings.append({
                "ring_id": f"RING-{kind.upper()}-{value}",
                "link_type": kind,
                "link_value": value,
                "member_count": len(members),
                "members": [m[0] for m in members[:20]],
                "risk": "high",
                "method": f"shared-{kind} connected grouping",
                "demo": False,
            })
    rings.sort(key=lambda x: x["member_count"], reverse=True)
    return {"rings": rings[:10], "status": "active", "observed": True}


@app.get("/api/return-risk")
def return_risk_schema():
    return {"method": "POST", "status": "active", "description": "Use POST /api/return-risk with a transaction payload."}


@app.post("/api/return-risk")
def return_risk(tx: Transaction):
    score = min(
        1.0,
        0.45 * tx.return_rate
        + 0.20 * min(tx.velocity_24h / 20, 1)
        + 0.15 * min(max(tx.amount_zscore, 0) / 3, 1)
        + 0.10 * tx.merchant_risk
        + 0.10 * (1 if tx.account_age_days < 30 else 0),
    )
    band = "high" if score >= 0.65 else "medium" if score >= 0.35 else "low"
    return {
        "risk_score": round(float(score), 4),
        "risk_band": band,
        "signals": [
            {"signal": "return_rate", "value": tx.return_rate},
            {"signal": "velocity_24h", "value": tx.velocity_24h},
            {"signal": "amount_zscore", "value": tx.amount_zscore},
            {"signal": "merchant_risk", "value": tx.merchant_risk},
        ],
        "requires_human_review": True,
        "implementation": "deterministic_local",
    }


@app.get("/api/investigate/{transaction_id}")
def investigate(transaction_id: str):
    df = load_df()
    if df.empty:
        raise HTTPException(404, "dataset unavailable")
    row = df[df.transaction_id == transaction_id]
    if row.empty:
        raise HTTPException(404, "transaction not found")
    raw = row.iloc[0].to_dict()
    scored = score_transaction(raw)
    dimensions = []
    checks = {
        "channel": float(raw["payment_risk"]),
        "device": min(1, float(raw["device_reuse_24h"]) / 5),
        "tenure": 1 - min(float(raw["account_age_days"]) / 365, 1),
        "geography": min(1, float(raw["geo_distance_km"]) / 500),
        "velocity": min(1, float(raw["velocity_1h"]) / 10),
        "amount": min(1, max(float(raw["amount_zscore"]) / 3, 0)),
    }
    for name, value in checks.items():
        dimensions.append({"dimension": name, "risk": round(value, 4), "evidence": "derived from transaction features", "source": "synthetic evaluation dataset"})
    return {
        "transaction_id": transaction_id,
        "risk": scored,
        "response_policy": response_policy(float(scored["risk_score"])),
        "investigators": dimensions,
        "recommendations": [
            {"id": "verify", "label": "Escalate for human verification", "requires_human": True},
            {"id": "stepup", "label": "Request step-up verification", "requires_human": True},
            {"id": "monitor", "label": "Increase monitoring", "requires_human": True},
        ],
        "safeguard": {"auto_block": False, "human_authorization_required": True, "policy": "DEFENSE_ONLY_V2"},
    }


def chargeback_evidence_package(transaction_id: str) -> dict:
    df = load_df()
    if df.empty:
        raise HTTPException(404, "dataset unavailable")
    row = df[df.transaction_id == transaction_id]
    if row.empty:
        raise HTTPException(404, "transaction not found")
    raw = row.iloc[0].to_dict()
    risk = score_transaction(raw)
    evidence = [
        {"type": "risk_score", "value": risk["risk_score"], "source": "ShieldKnot fraud model"},
        {"type": "device_reuse_24h", "value": raw["device_reuse_24h"], "source": "transaction telemetry"},
        {"type": "velocity_24h", "value": raw["velocity_24h"], "source": "transaction telemetry"},
        {"type": "account_age_days", "value": raw["account_age_days"], "source": "account profile"},
        {"type": "payment_risk", "value": raw["payment_risk"], "source": "payment signal"},
        {"type": "chargeback_history", "value": raw["chargeback_history"], "source": "account history"},
    ]
    return {
        "case_id": f"CB-{transaction_id}",
        "transaction_id": transaction_id,
        "risk_band": risk["risk_band"],
        "evidence": evidence,
        "response_summary": "Structured evidence package generated for authorized review; no autonomous dispute submission is performed.",
        "human_authorization_required": True,
        "status": "ready_for_review",
    }


@app.get("/api/chargeback-evidence/{transaction_id}")
def chargeback_evidence(transaction_id: str):
    return chargeback_evidence_package(transaction_id)


@app.post("/api/chargeback-evidence/{transaction_id}/respond")
def chargeback_evidence_respond(transaction_id: str):
    package = chargeback_evidence_package(transaction_id)
    package["response"] = {
        "type": "reviewer_ready_response",
        "action": "prepare_only",
        "submission": "not_submitted",
        "human_authorization_required": True,
    }
    return package


@app.get("/api/response-policy")
def response_policy_info():
    return {
        "engine": "deterministic_local",
        "auto_block": False,
        "human_review_required": True,
        "thresholds": {"low": 0.35, "high": 0.60, "critical": 0.80},
        "status": "active",
    }



def _load_recorded_outcomes() -> dict[str, dict]:
    if not OUTCOME_LOG.exists():
        return {}
    result: dict[str, dict] = {}
    for line in OUTCOME_LOG.read_text(encoding="utf-8").splitlines():
        try:
            item = json.loads(line)
            if item.get("incident_id"):
                result[str(item["incident_id"])] = item
        except json.JSONDecodeError:
            continue
    return result


def _pick_demo_rows(df: pd.DataFrame) -> list[dict]:
    """Pick deterministic transactions from the synthetic dataset for demo scenarios."""
    rows = df.to_dict("records")
    scores = score_many(rows)
    ranked = sorted(zip(rows, scores), key=lambda x: x[1], reverse=True)
    top = ranked[0][0]

    def return_score(row: dict) -> float:
        return min(1.0, 0.45 * float(row["return_rate"])
                   + 0.20 * min(float(row["velocity_24h"]) / 20, 1)
                   + 0.15 * min(max(float(row["amount_zscore"]), 0) / 3, 1)
                   + 0.10 * float(row["merchant_risk"])
                   + 0.10 * (1 if float(row["account_age_days"]) < 30 else 0))

    return_row = max(rows, key=return_score)
    chargeback_row = max(
        rows,
        key=lambda r: (float(r["chargeback_history"]), float(r["payment_risk"]) + float(r["ip_risk"]))
    )

    # Three different high-risk synthetic transactions are used to demonstrate
    # the abuse-ring investigation flow. This is explicitly labelled simulated.
    cluster = [r for r, score in ranked if score >= 0.7][:3]
    if len(cluster) < 3:
        cluster = [r for r, _ in ranked[:3]]
    return [top, return_row, chargeback_row, *cluster[:3]]


def demo_incidents() -> list[dict]:
    global DEMO_INCIDENT_CACHE
    if DEMO_INCIDENT_CACHE is not None:
        return DEMO_INCIDENT_CACHE
    df = load_df()
    if df.empty:
        return []
    selected = _pick_demo_rows(df)
    now = now_iso()
    top, return_row, chargeback_row, *cluster = selected
    outcomes = _load_recorded_outcomes()

    def incident(iid: str, detector: str, txid: str, severity: str, title: str,
                 description: str, evidence: list[dict], segments: int = 1,
                 density_lift: float = 0.0, volume_lift: float = 1.0,
                 exposure: float = 0.0, demo: bool = True, members: list[str] | None = None):
        status = "Completed" if iid in outcomes else "Detected"
        return {
            "id": iid, "type": detector, "detector": detector,
            "title": title, "status": status, "severity": severity,
            "detected": now, "density_lift": density_lift,
            "volume_lift": volume_lift, "exposure_inr": round(exposure, 2),
            "segments": segments, "transaction_id": txid,
            "description": description, "evidence": evidence,
            "members": members or [txid], "demo": demo,
            "scenario": "SIMULATED DEMO SCENARIO" if demo else "OBSERVED DATA",
            "outcome": outcomes.get(iid),
        }

    incidents = [
        incident(
            "SPIKE-DEMO-001", "fraud_spike_detector", str(top["transaction_id"]), "critical",
            "Fraud-spike detector demonstration",
            "Synthetic risk-density spike scenario generated from the local evaluation dataset.",
            [
                {"signal": "risk_density_lift", "value": "3.12×", "source": "demo scenario"},
                {"signal": "high_risk_density", "value": "31.2%", "source": "synthetic transaction window"},
                {"signal": "detector_threshold", "value": "1.40×", "source": "local detector policy"},
            ],
            segments=4, density_lift=3.12, volume_lift=1.42,
            exposure=float(top["amount"]) * 4,
        ),
        incident(
            "RETURN-DEMO-002", "return_risk_scorer", str(return_row["transaction_id"]), "high",
            "Elevated return-risk pattern",
            "Synthetic return-risk scenario demonstrating the deterministic scorer and review workflow.",
            [
                {"signal": "return_rate", "value": f'{float(return_row["return_rate"]):.3f}', "source": "synthetic dataset"},
                {"signal": "velocity_24h", "value": int(return_row["velocity_24h"]), "source": "transaction telemetry"},
                {"signal": "merchant_risk", "value": f'{float(return_row["merchant_risk"]):.3f}', "source": "synthetic dataset"},
            ],
            exposure=float(return_row["amount"]),
        ),
        incident(
            "CHARGEBACK-DEMO-003", "chargeback_evidence_responder", str(chargeback_row["transaction_id"]), "high",
            "Chargeback evidence review",
            "Synthetic case showing how ShieldKnot prepares evidence for an authorized reviewer without submitting a dispute.",
            [
                {"signal": "chargeback_history", "value": int(chargeback_row["chargeback_history"]), "source": "synthetic account history"},
                {"signal": "payment_risk", "value": f'{float(chargeback_row["payment_risk"]):.3f}', "source": "synthetic payment signal"},
                {"signal": "review_mode", "value": "prepare only", "source": "defense-only response policy"},
            ],
            exposure=float(chargeback_row["amount"]),
        ),
        incident(
            "ABUSE-DEMO-004", "abuse_ring_sentinel", str(cluster[0]["transaction_id"]), "high",
            "Connected-risk cluster demonstration",
            "Synthetic connected-group scenario for demonstrating shared-identifier investigation. This is not an observed abuse ring.",
            [
                {"signal": "correlated_members", "value": len(cluster), "source": "demo scenario"},
                {"signal": "correlation_method", "value": "shared device/IP (simulated)", "source": "demo scenario"},
                {"signal": "review_requirement", "value": "human authorization", "source": "response policy"},
            ],
            segments=len(cluster), exposure=sum(float(r["amount"]) for r in cluster),
            members=[str(r["transaction_id"]) for r in cluster],
        ),
    ]
    DEMO_INCIDENT_CACHE = incidents
    return incidents


@app.get("/api/incidents")
def incidents():
    return demo_incidents()


@app.get("/api/incidents/{incident_id}")
def incident_detail(incident_id: str):
    found = next((i for i in demo_incidents() if i["id"] == incident_id), None)
    if not found:
        raise HTTPException(404, "incident not found")
    return found


@app.get("/api/overview")
def overview():
    df = load_df()
    spike_data = spike_result()
    if df.empty:
        return {"transactions_scored": 0, "high_risk_transactions": 0, "high_risk_rate": 0,
                "active_incidents": 0, "estimated_exposure_inr": 0, "spike": spike_data}
    rows = df.to_dict("records")
    scores = score_many(rows)
    threshold = score_threshold()
    high = [r for r, s in zip(rows, scores) if s >= threshold]
    exposure = sum(float(r.get("amount", 0)) for r in high)
    incs = demo_incidents()
    active = sum(1 for i in incs if i["status"] != "Completed")
    return {
        "transactions_scored": len(rows),
        "high_risk_transactions": len(high),
        "high_risk_rate": round(len(high) / max(len(rows), 1), 4),
        "active_incidents": active,
        "estimated_exposure_inr": round(exposure, 2),
        "spike": spike_data,
        "abuse_rings": sum(1 for i in incs if i["detector"] == "abuse_ring_sentinel"),
        "threshold": threshold,
        "generated_at": now_iso(),
        "demo_mode": True,
        "demo_incident_count": len(incs),
    }


@app.post("/api/demo/reset")
def reset_demo():
    """Reset demo outcome history; synthetic source data is never modified."""
    global DEMO_INCIDENT_CACHE
    if OUTCOME_LOG.exists():
        OUTCOME_LOG.unlink()
    DEMO_INCIDENT_CACHE = None
    return {"reset": True, "incidents": len(demo_incidents()), "message": "Demo incidents regenerated from synthetic data."}


@app.post("/api/outcomes")
def outcome(body: Outcome):
    OUTCOME_LOG.parent.mkdir(exist_ok=True)
    payload = body.model_dump()
    payload["reward"] = reward_score(body.outcome, body.fraud_amount_inr, body.false_positive_cost_inr)
    payload["recorded_at"] = now_iso()
    with OUTCOME_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    global DEMO_INCIDENT_CACHE
    DEMO_INCIDENT_CACHE = None
    return {"recorded": True, "audit_event": payload}
