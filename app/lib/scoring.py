from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from .constants import AMOUNT_REFERENCE, MODEL_LABELS, RISK_HIGH, RISK_MEDIUM
from .data import feature_matrix, generate_demo_transactions, normalize_transactions, read_scored_artifact
from .styling import TOKENS


ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"
FULL_SCORED_ARTIFACT = "full_scored_transactions.parquet"


def classify_risk(score: float) -> str:
    if score >= RISK_HIGH:
        return "High"
    if score >= RISK_MEDIUM:
        return "Medium"
    return "Low"


def risk_color(score: float) -> str:
    if score >= RISK_HIGH:
        return TOKENS["risk_high"]
    if score >= RISK_MEDIUM:
        return TOKENS["risk_medium"]
    return TOKENS["risk_low"]


def heuristic_risk(df: pd.DataFrame, model_key: str = "heuristic") -> np.ndarray:
    normalized = normalize_transactions(df)
    amount_rank = np.log1p(normalized["amount"]) / np.log1p(AMOUNT_REFERENCE)
    amount_rank = amount_rank.clip(0, 1)
    risky_type = normalized["type"].isin(["TRANSFER", "CASH_OUT"]).astype(float)
    origin_error = (
        normalized["errorBalanceOrig"] / np.maximum(normalized["amount"], 1)
    ).clip(0, 1)
    dest_error = (
        normalized["errorBalanceDest"] / np.maximum(normalized["amount"], 1)
    ).clip(0, 1)
    zeroed = normalized["zeroedOrigin"].astype(float)
    merchant_penalty = normalized["isMerchant"].astype(float) * 0.08

    weights = {
        "xgb": (0.36, 0.24, 0.16, 0.16, 0.10),
        "iforest": (0.34, 0.18, 0.22, 0.18, 0.08),
        "heuristic": (0.36, 0.24, 0.16, 0.16, 0.12),
    }.get(model_key, (0.36, 0.24, 0.16, 0.16, 0.12))

    score = (
        weights[0] * amount_rank
        + weights[1] * risky_type
        + weights[2] * origin_error
        + weights[3] * dest_error
        + weights[4] * zeroed
        - merchant_penalty
    )
    return np.asarray(score.clip(0, 1), dtype=float)


def _decision_scores_to_risk(raw_scores: np.ndarray, model: dict[str, Any] | None = None) -> np.ndarray:
    raw = np.asarray(raw_scores, dtype=float)
    score_min = model.get("decision_min") if model else None
    score_max = model.get("decision_max") if model else None
    if score_min is not None and score_max is not None and score_max > score_min:
        return 1 - ((raw - score_min) / (score_max - score_min))
    if raw.size > 1 and raw.max() > raw.min():
        return 1 - ((raw - raw.min()) / (raw.max() - raw.min()))
    return 1 / (1 + np.exp(8 * raw))


def _load_joblib(name: str, artifacts_dir: Path) -> Any | None:
    path = artifacts_dir / name
    if not path.exists():
        return None
    return joblib.load(path)


def full_scored_artifact_path(artifacts_dir: Path = ARTIFACTS_DIR) -> Path:
    return artifacts_dir / FULL_SCORED_ARTIFACT


def has_full_scored_artifact(artifacts_dir: Path = ARTIFACTS_DIR) -> bool:
    return full_scored_artifact_path(artifacts_dir).exists()


def score_transactions(
    df: pd.DataFrame,
    model_key: str = "xgb",
    artifacts_dir: Path = ARTIFACTS_DIR,
) -> pd.DataFrame:
    scored = normalize_transactions(df)
    model_filename = {"xgb": "model_xgb.pkl", "iforest": "model_iforest.pkl"}.get(model_key)
    model = _load_joblib(model_filename, artifacts_dir) if model_filename else None
    matrix = feature_matrix(scored)

    risk_score: np.ndarray
    if model is None:
        risk_score = heuristic_risk(scored, model_key=model_key)
    elif isinstance(model, dict) and "model" in model:
        estimator = model["model"]
        columns = model.get("feature_columns", matrix.columns)
        model_matrix = matrix.reindex(columns=columns, fill_value=0)
        if "scaler" in model and model["scaler"] is not None:
            model_matrix = model["scaler"].transform(model_matrix)
        if hasattr(estimator, "predict_proba"):
            risk_score = estimator.predict_proba(model_matrix)[:, 1]
        else:
            raw = estimator.decision_function(model_matrix)
            risk_score = _decision_scores_to_risk(raw, model)
    elif hasattr(model, "predict_proba"):
        risk_score = model.predict_proba(matrix)[:, 1]
    else:
        raw = model.decision_function(matrix)
        risk_score = _decision_scores_to_risk(raw)

    scored["risk_score"] = np.round(np.asarray(risk_score).clip(0, 1), 6)
    threshold = model.get("threshold", RISK_HIGH) if isinstance(model, dict) else RISK_HIGH
    scored["predicted_fraud"] = (scored["risk_score"] >= threshold).astype(int)
    scored["risk_level"] = scored["risk_score"].map(classify_risk)
    scored["model_used"] = MODEL_LABELS.get(model_key, model_key)
    return scored.sort_values("risk_score", ascending=False).reset_index(drop=True)


def build_full_scored_artifact(
    input_path: Path,
    *,
    model_key: str = "xgb",
    artifacts_dir: Path = ARTIFACTS_DIR,
    chunksize: int = 200_000,
) -> Path:
    """Score a large CSV in chunks and persist a full UI-ready Parquet artifact."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    artifacts_dir.mkdir(parents=True, exist_ok=True)
    output_path = full_scored_artifact_path(artifacts_dir)
    tmp_path = output_path.with_suffix(".tmp.parquet")
    tmp_path.unlink(missing_ok=True)

    writer: pq.ParquetWriter | None = None
    wrote_rows = False
    try:
        for chunk in pd.read_csv(input_path, chunksize=chunksize):
            scored_chunk = score_transactions(chunk, model_key=model_key, artifacts_dir=artifacts_dir)
            table = pa.Table.from_pandas(scored_chunk, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(tmp_path, table.schema)
            writer.write_table(table)
            wrote_rows = True
    except Exception:
        if writer is not None:
            writer.close()
        tmp_path.unlink(missing_ok=True)
        raise

    if writer is not None:
        writer.close()
    if not wrote_rows:
        tmp_path.unlink(missing_ok=True)
        raise ValueError(f"No rows were scored from {input_path}.")
    tmp_path.replace(output_path)
    return output_path


def load_scored_transactions(model_key: str = "xgb", artifacts_dir: Path = ARTIFACTS_DIR) -> pd.DataFrame:
    full_artifact = full_scored_artifact_path(artifacts_dir)
    # The full Parquet already carries engineered features + risk columns, so we
    # skip the (expensive, redundant) normalize pass over millions of rows.
    artifact = pd.read_parquet(full_artifact) if full_artifact.exists() else None
    if artifact is None:
        artifact = read_scored_artifact(artifacts_dir / "scored_transactions.csv")
    if artifact is not None and {"risk_score", "predicted_fraud"}.issubset(artifact.columns):
        if model_key != "xgb":
            return score_transactions(artifact, model_key=model_key, artifacts_dir=artifacts_dir)
        artifact["risk_level"] = artifact["risk_score"].map(classify_risk)
        artifact["model_used"] = MODEL_LABELS.get(model_key, model_key)
        return artifact.sort_values("risk_score", ascending=False).reset_index(drop=True)
    return score_transactions(generate_demo_transactions(), model_key=model_key, artifacts_dir=artifacts_dir)


def score_single_transaction(transaction: dict[str, Any], model_key: str = "xgb") -> dict[str, Any]:
    scored = score_transactions(pd.DataFrame([transaction]), model_key=model_key)
    row = scored.iloc[0].to_dict()
    row["risk_color"] = risk_color(float(row["risk_score"]))
    return row
