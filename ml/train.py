"""Train and evaluate the ShieldKnot fraud model."""
from __future__ import annotations
import json
from pathlib import Path
import joblib
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from ml.features import FEATURES, make_features

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "transactions.csv"
MODEL = ROOT / "models" / "fraud_model.joblib"
METRICS = ROOT / "models" / "metrics.json"


def train():
    if not DATA.exists():
        from data.generate_dataset import generate
        DATA.parent.mkdir(exist_ok=True)
        generate().to_csv(DATA, index=False)
    df = pd.read_csv(DATA)
    X = pd.DataFrame([make_features(r) for r in df.to_dict("records")], columns=FEATURES)
    y = df["fraud"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=2026, stratify=y
    )
    model = Pipeline([
        ("scale", StandardScaler()),
        ("detector", ExtraTreesClassifier(
            n_estimators=120, max_depth=None, min_samples_leaf=3,
            class_weight="balanced", random_state=2026, n_jobs=-1
        )),
    ])
    model.fit(X_train, y_train)
    p = model.predict_proba(X_test)[:, 1]
    # Operational threshold is selected on validation-like held-out test only
    # for this demo artifact; production should lock it before final evaluation.
    threshold = 0.50
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred).ravel()
    metrics = {
        "dataset": "synthetic",
        "rows": int(len(df)),
        "test_rows": int(len(X_test)),
        "fraud_rate": round(float(y.mean()), 6),
        "threshold": threshold,
        "precision": round(float(precision_score(y_test, pred, zero_division=0)), 6),
        "recall": round(float(recall_score(y_test, pred, zero_division=0)), 6),
        "f1": round(float(f1_score(y_test, pred, zero_division=0)), 6),
        "roc_auc": round(float(roc_auc_score(y_test, p)), 6),
        "false_positive_rate": round(float(fp / max(fp + tn, 1)), 6),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "false_positive_cost_inr": 400,
        "estimated_test_fp_cost_inr": int(fp * 400),
        "feature_importance": dict(sorted(
            zip(FEATURES, model.named_steps["detector"].feature_importances_),
            key=lambda x: x[1], reverse=True
        )),
    }
    MODEL.parent.mkdir(exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES, "metrics": metrics}, MODEL)
    METRICS.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    train()
