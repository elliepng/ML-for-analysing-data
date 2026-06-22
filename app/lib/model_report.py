from __future__ import annotations

from pathlib import Path

import json
import numpy as np
import pandas as pd

from .constants import MODEL_LABELS


ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
MODEL_METRIC_NAMES = {
    "xgb": "XGBoost supervised",
    "iforest": "Isolation Forest",
    "heuristic": "Fallback risk rules",
    "rule": "Bank rule isFlaggedFraud",
}


DEMO_METRICS = pd.DataFrame(
    [
        {
            "model": "DEMO (chưa train) - train PaySim to populate real metrics",
            "precision": pd.NA,
            "recall": pd.NA,
            "f1": pd.NA,
            "auc_pr": pd.NA,
            "roc_auc": pd.NA,
        }
    ]
)


def metrics_path(artifacts_dir: Path = ARTIFACTS_DIR) -> Path:
    return artifacts_dir / "model_metrics.json"


def has_real_metrics(artifacts_dir: Path = ARTIFACTS_DIR) -> bool:
    return metrics_path(artifacts_dir).exists()


def _load_payload(artifacts_dir: Path = ARTIFACTS_DIR) -> dict:
    path = metrics_path(artifacts_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def selected_model_label(model_key: str) -> str:
    return MODEL_LABELS.get(model_key, model_key.upper())


def load_model_metrics(artifacts_dir: Path = ARTIFACTS_DIR, model_key: str | None = None) -> pd.DataFrame:
    payload = _load_payload(artifacts_dir)
    if not payload:
        return DEMO_METRICS
    metrics = pd.DataFrame(payload.get("models", DEMO_METRICS.to_dict("records")))
    if model_key is None:
        return metrics
    metric_name = MODEL_METRIC_NAMES.get(model_key)
    if metric_name is None:
        return metrics.iloc[0:0]
    filtered = metrics[metrics["model"].astype(str) == metric_name].reset_index(drop=True)
    if filtered.empty and model_key == "xgb" and not metrics.empty:
        # Supervised model is always the first row written by train_models.py,
        # even when XGBoost falls back to RandomForest.
        return metrics.iloc[0:1].reset_index(drop=True)
    return filtered


def load_confusion_matrix(artifacts_dir: Path = ARTIFACTS_DIR, model_key: str = "xgb") -> np.ndarray:
    payload = _load_payload(artifacts_dir)
    if not payload:
        return np.zeros((2, 2), dtype=int)
    matrices = payload.get("confusion_matrices", {})
    if model_key in matrices:
        return np.asarray(matrices[model_key])
    if model_key != "xgb":
        return np.zeros((2, 2), dtype=int)
    return np.asarray(payload.get("confusion_matrix", [[0, 0], [0, 0]]))


def load_curve_points(
    curve_name: str,
    x_key: str,
    y_key: str,
    artifacts_dir: Path = ARTIFACTS_DIR,
) -> tuple[list[float], list[float]] | None:
    payload = _load_payload(artifacts_dir)
    curve = payload.get(curve_name)
    if not curve:
        return None
    x_values = curve.get(x_key)
    y_values = curve.get(y_key)
    if not x_values or not y_values:
        return None
    return x_values, y_values


def load_roc_curve(artifacts_dir: Path = ARTIFACTS_DIR) -> tuple[list[float], list[float]] | None:
    return load_curve_points("roc_curve", "fpr", "tpr", artifacts_dir=artifacts_dir)


def load_pr_curve(artifacts_dir: Path = ARTIFACTS_DIR) -> tuple[list[float], list[float]] | None:
    return load_curve_points("pr_curve", "recall", "precision", artifacts_dir=artifacts_dir)
