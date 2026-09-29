"""Feature engineering shared by training and inference."""
from __future__ import annotations

FEATURES = [
    "amount_log", "velocity_1h", "velocity_24h", "device_reuse_24h",
    "account_age_days", "geo_distance_km", "chargeback_history",
    "return_rate", "new_device", "ip_risk", "payment_risk", "hour_risk",
    "merchant_risk", "amount_zscore",
]


def make_features(row: dict) -> dict:
    import math
    amount = max(float(row.get("amount", 0)), 0.01)
    return {
        "amount_log": math.log1p(amount),
        "velocity_1h": float(row.get("velocity_1h", 0)),
        "velocity_24h": float(row.get("velocity_24h", 0)),
        "device_reuse_24h": float(row.get("device_reuse_24h", 0)),
        "account_age_days": float(row.get("account_age_days", 0)),
        "geo_distance_km": float(row.get("geo_distance_km", 0)),
        "chargeback_history": float(row.get("chargeback_history", 0)),
        "return_rate": float(row.get("return_rate", 0)),
        "new_device": float(row.get("new_device", 0)),
        "ip_risk": float(row.get("ip_risk", 0)),
        "payment_risk": float(row.get("payment_risk", 0)),
        "hour_risk": float(row.get("hour_risk", 0)),
        "merchant_risk": float(row.get("merchant_risk", 0)),
        "amount_zscore": float(row.get("amount_zscore", 0)),
    }
