from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from lib.data import (  # noqa: E402
    REQUIRED_TRAIN_COLUMNS,
    feature_matrix,
    normalize_transactions,
    validate_transaction_schema,
)
from lib.constants import RISK_HIGH, RISK_MEDIUM  # noqa: E402


def metric(value: float) -> float:
    return float(value)


def tune_threshold(y_true, scores, target_recall: float = 0.95, floor: float = 0.05) -> float:
    """Smallest threshold reaching target recall with the best precision; floor otherwise."""
    precision_curve, recall_curve, thresholds = precision_recall_curve(y_true, scores)
    best_threshold = None
    best_precision = -1.0
    for p, r, t in zip(precision_curve[:-1], recall_curve[:-1], thresholds):
        if r >= target_recall and p > best_precision:
            best_precision = p
            best_threshold = t
    if best_threshold is None:
        return floor
    return float(max(best_threshold, floor))


def sparse_indices(n: int, max_points: int = 60) -> list[int]:
    if n <= max_points:
        return list(range(n))
    step = max(1, n // max_points)
    indices = list(range(0, n, step))
    if indices[-1] != n - 1:
        indices.append(n - 1)
    return indices[:max_points]


def _build_supervised_model():
    try:
        from xgboost import XGBClassifier

        return (
            XGBClassifier(
                n_estimators=180,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric="logloss",
                n_jobs=2,
                random_state=42,
            ),
            "XGBoost supervised",
        )
    except Exception:
        return (
            RandomForestClassifier(
                n_estimators=180,
                max_depth=10,
                class_weight="balanced",
                n_jobs=2,
                random_state=42,
            ),
            "Random Forest supervised",
        )


def balanced_sample(df: pd.DataFrame, normal_ratio: int, random_state: int) -> pd.DataFrame:
    fraud = df[df["isFraud"] == 1]
    normal = df[df["isFraud"] == 0]
    normal_count = min(len(normal), max(len(fraud) * normal_ratio, 5_000))
    normal_sample = normal.sample(normal_count, random_state=random_state) if len(normal) > normal_count else normal
    return pd.concat([fraud, normal_sample], ignore_index=True).sample(frac=1, random_state=random_state)


def train(input_path: Path, output_dir: Path, max_rows: int | None, normal_ratio: int, target_recall: float = 0.95) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(input_path, nrows=max_rows)
    errors = validate_transaction_schema(raw, required_columns=REQUIRED_TRAIN_COLUMNS, require_labels=True)
    if errors:
        raise ValueError("Invalid training data: " + "; ".join(errors))
    data = normalize_transactions(raw)
    scoped = data[data["type"].isin(["TRANSFER", "CASH_OUT"])].copy()
    if scoped.empty:
        raise ValueError("Invalid training data: no TRANSFER or CASH_OUT rows after normalization.")
    if scoped["isFraud"].nunique() < 2:
        raise ValueError("Invalid training data: scoped TRANSFER/CASH_OUT rows must contain both 0/1 labels.")
    trainable = balanced_sample(scoped, normal_ratio=normal_ratio, random_state=42)

    x = feature_matrix(trainable)
    y = trainable["isFraud"].astype(int)
    x_train, x_test, y_train, y_test, _rule_train, rule_test = train_test_split(
        x,
        y,
        trainable["isFlaggedFraud"].astype(int),
        test_size=0.25,
        stratify=y,
        random_state=42,
    )

    supervised, supervised_label = _build_supervised_model()
    supervised.fit(x_train, y_train)
    probabilities = supervised.predict_proba(x_test)[:, 1]
    threshold = tune_threshold(y_test, probabilities, target_recall=target_recall)
    predictions = (probabilities >= threshold).astype(int)
    fpr, tpr, _ = roc_curve(y_test, probabilities)
    precision_curve, recall_curve, _ = precision_recall_curve(y_test, probabilities)
    roc_idx = sparse_indices(len(fpr))
    pr_idx = sparse_indices(len(recall_curve))

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)
    iforest = IsolationForest(n_estimators=220, contamination=max(y.mean(), 0.001), random_state=42)
    iforest.fit(x_train_scaled)
    train_decisions = iforest.decision_function(x_train_scaled)
    iforest_predictions = (iforest.predict(x_test_scaled) == -1).astype(int)

    joblib.dump(
        {"model": supervised, "feature_columns": list(x.columns), "threshold": threshold},
        output_dir / "model_xgb.pkl",
    )
    joblib.dump(
        {
            "model": iforest,
            "scaler": scaler,
            "feature_columns": list(x.columns),
            "decision_min": float(train_decisions.min()),
            "decision_max": float(train_decisions.max()),
            "threshold": RISK_HIGH,
        },
        output_dir / "model_iforest.pkl",
    )
    joblib.dump({"feature_columns": list(x.columns)}, output_dir / "feature_pipeline.pkl")

    scored = scoped.sample(min(len(scoped), 50_000), random_state=42).copy()
    scored_probabilities = supervised.predict_proba(feature_matrix(scored))[:, 1]
    scored["risk_score"] = scored_probabilities
    scored["predicted_fraud"] = (scored["risk_score"] >= threshold).astype(int)
    scored["risk_level"] = pd.cut(
        scored["risk_score"],
        bins=[-0.01, RISK_MEDIUM, RISK_HIGH, 1.01],
        labels=["Low", "Medium", "High"],
        right=False,
    )
    scored.sort_values("risk_score", ascending=False).to_csv(output_dir / "scored_transactions.csv", index=False)

    xgb_confusion = confusion_matrix(y_test, predictions).tolist()
    iforest_confusion = confusion_matrix(y_test, iforest_predictions).tolist()
    rule_confusion = confusion_matrix(y_test, rule_test).tolist()

    metrics = {
        "models": [
            {
                "model": supervised_label,
                "precision": metric(precision_score(y_test, predictions, zero_division=0)),
                "recall": metric(recall_score(y_test, predictions, zero_division=0)),
                "f1": metric(f1_score(y_test, predictions, zero_division=0)),
                "auc_pr": metric(average_precision_score(y_test, probabilities)),
                "roc_auc": metric(roc_auc_score(y_test, probabilities)),
            },
            {
                "model": "Isolation Forest",
                "precision": metric(precision_score(y_test, iforest_predictions, zero_division=0)),
                "recall": metric(recall_score(y_test, iforest_predictions, zero_division=0)),
                "f1": metric(f1_score(y_test, iforest_predictions, zero_division=0)),
                "auc_pr": metric(average_precision_score(y_test, iforest_predictions)),
                "roc_auc": metric(roc_auc_score(y_test, iforest_predictions)),
            },
            {
                "model": "Bank rule isFlaggedFraud",
                "precision": metric(precision_score(y_test, rule_test, zero_division=0)),
                "recall": metric(recall_score(y_test, rule_test, zero_division=0)),
                "f1": metric(f1_score(y_test, rule_test, zero_division=0)),
                "auc_pr": metric(average_precision_score(y_test, rule_test)),
                "roc_auc": metric(roc_auc_score(y_test, rule_test)),
            },
        ],
        "confusion_matrix": xgb_confusion,
        "confusion_matrices": {
            "xgb": xgb_confusion,
            "iforest": iforest_confusion,
            "rule": rule_confusion,
        },
        "roc_curve": {
            "fpr": [float(fpr[index]) for index in roc_idx],
            "tpr": [float(tpr[index]) for index in roc_idx],
        },
        "pr_curve": {
            "recall": [float(recall_curve[index]) for index in pr_idx],
            "precision": [float(precision_curve[index]) for index in pr_idx],
        },
    }
    (output_dir / "model_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train PaySim fraud detection models.")
    parser.add_argument("--input", type=Path, required=True, help="Path to PaySim CSV file.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--max-rows", type=int, default=None)
    parser.add_argument("--normal-ratio", type=int, default=8)
    parser.add_argument("--target-recall", type=float, default=0.95)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    train(args.input, args.output_dir, args.max_rows, args.normal_ratio, args.target_recall)
