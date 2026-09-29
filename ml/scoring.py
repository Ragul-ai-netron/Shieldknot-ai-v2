from __future__ import annotations
from pathlib import Path
import joblib
import pandas as pd
from ml.features import make_features

ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = ROOT / "models" / "fraud_model.joblib"
_bundle = None


def load_model():
    global _bundle
    if _bundle is None:
        if not MODEL_PATH.exists():
            from ml.train import train
            train()
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def score_transaction(row: dict) -> dict:
    bundle = load_model()
    features = make_features(row)
    X = pd.DataFrame([features], columns=bundle["features"])
    score = float(bundle["model"].predict_proba(X)[0, 1])
    # Lightweight evidence proxy: combine model-global importance with the
    # observed feature magnitude. It is intentionally labeled as a signal,
    # not a causal explanation.
    importances = bundle["model"].named_steps["detector"].feature_importances_
    ranked = sorted(zip(bundle["features"], importances), key=lambda x: x[1], reverse=True)
    scale = {"amount_log":8.0,"velocity_1h":5.0,"velocity_24h":15.0,"device_reuse_24h":5.0,
             "account_age_days":365.0,"geo_distance_km":250.0,"chargeback_history":2.0,
             "return_rate":0.3,"new_device":1.0,"ip_risk":1.0,"payment_risk":1.0,
             "hour_risk":1.0,"merchant_risk":1.0,"amount_zscore":3.0}
    reasons=[]
    for f, imp in ranked:
        magnitude=min(abs(float(features[f]))/max(scale.get(f,1.0),1e-9),1.0)
        impact=float(imp*magnitude)
        if impact >= 0.02:
            reasons.append({"feature":f,"impact":round(impact,4),"direction":"risk signal"})
        if len(reasons)>=5: break
    band = "critical" if score >= .8 else "high" if score >= .6 else "medium" if score >= .35 else "low"
    return {"risk_score": round(score, 6), "risk_band": band, "reasons": reasons, "model": "fraud_model.joblib"}


def score_many(rows: list[dict]) -> list[float]:
    bundle = load_model()
    X = pd.DataFrame([make_features(r) for r in rows], columns=bundle["features"])
    return [float(x) for x in bundle["model"].predict_proba(X)[:,1]]
