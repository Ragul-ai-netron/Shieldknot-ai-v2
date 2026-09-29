"""Generate a reproducible synthetic transaction dataset for ShieldKnot.

The dataset is intentionally synthetic. It exists for local development and
for a transparent, reproducible held-out evaluation; it is not production data.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd


def generate(n: int = 30000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    amount = np.exp(rng.normal(np.log(1200), 0.9, n)).clip(50, 50000)
    velocity_1h = rng.poisson(1.6, n)
    velocity_24h = velocity_1h + rng.poisson(5.0, n)
    device_reuse = rng.poisson(1.5, n)
    account_age = rng.exponential(420, n).clip(1, 3000)
    geo_distance = rng.exponential(40, n).clip(0, 2000)
    chargebacks = rng.binomial(4, 0.07, n)
    return_rate = rng.beta(2, 15, n)
    new_device = rng.binomial(1, 0.14, n)
    ip_risk = rng.beta(1.5, 8, n)
    payment_risk = rng.beta(1.8, 9, n)
    hour_risk = rng.beta(2, 10, n)
    merchant_risk = rng.beta(2, 9, n)
    amount_z = rng.normal(0, 1, n)

    # Latent fraud propensity. Labels are generated from the same observable
    # signals with controlled noise so the benchmark measures a learnable
    # detector rather than an impossible random-label task.
    z = (
        0.55*np.log1p(amount) + 0.65*velocity_1h + 0.12*velocity_24h
        + 0.50*device_reuse - 0.0015*account_age + 0.004*geo_distance
        + 0.9*chargebacks + 4.0*return_rate + 1.0*new_device
        + 4.0*ip_risk + 3.5*payment_risk + 2.0*hour_risk
        + 2.8*merchant_risk + 0.9*amount_z
    )
    noisy = z + rng.normal(0, 0.55, n)
    cutoff = np.quantile(noisy, 0.93)
    fraud = (noisy >= cutoff).astype(int)

    df = pd.DataFrame({
        "transaction_id": [f"TXN-{i:07d}" for i in range(n)],
        "account_id": [f"ACC-{x:06d}" for x in rng.integers(0, 20000, n)],
        "device_id": [f"DEV-{x:05d}" for x in rng.integers(0, 5000, n)],
        "ip_id": [f"IP-{x:05d}" for x in rng.integers(0, 7000, n)],
        "amount": amount.round(2), "velocity_1h": velocity_1h,
        "velocity_24h": velocity_24h, "device_reuse_24h": device_reuse,
        "account_age_days": account_age.round(1), "geo_distance_km": geo_distance.round(2),
        "chargeback_history": chargebacks, "return_rate": return_rate.round(4),
        "new_device": new_device, "ip_risk": ip_risk.round(4),
        "payment_risk": payment_risk.round(4), "hour_risk": hour_risk.round(4),
        "merchant_risk": merchant_risk.round(4), "amount_zscore": amount_z.round(4),
        "fraud": fraud,
    })
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=30000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="data/transactions.csv")
    args = parser.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    df = generate(args.n, args.seed)
    df.to_csv(args.out, index=False)
    print(f"wrote {len(df):,} rows to {args.out}; fraud rate={df.fraud.mean():.3f}")
