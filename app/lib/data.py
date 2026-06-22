from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .constants import BASE_COLUMNS, FEATURE_COLUMNS, PAYMENT_TYPES


REQUIRED_TRAIN_COLUMNS = set(BASE_COLUMNS)
REQUIRED_UPLOAD_COLUMNS = {
    "type",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
}
NUMERIC_COLUMNS = [
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]


def validate_transaction_schema(
    df: pd.DataFrame,
    *,
    required_columns: set[str] | None = None,
    require_labels: bool = False,
) -> list[str]:
    """Return hard validation errors for real data paths.

    normalize_transactions is intentionally permissive for demo/manual scoring.
    Training and upload use this stricter gate so bad source data is not silently
    converted into zeros or default transaction types.
    """
    required = required_columns or REQUIRED_UPLOAD_COLUMNS
    missing = sorted(required - set(df.columns))
    errors = [f"Missing required column: {column}" for column in missing]
    if errors:
        return errors

    numeric_to_check = [column for column in NUMERIC_COLUMNS if column in required or column in df.columns]
    for column in numeric_to_check:
        invalid = pd.to_numeric(df[column], errors="coerce").isna() & df[column].notna()
        if invalid.any():
            errors.append(f"Column {column} contains {int(invalid.sum()):,} non-numeric value(s).")

    if require_labels:
        labels = pd.to_numeric(df["isFraud"], errors="coerce")
        if labels.isna().any():
            errors.append("Column isFraud contains non-numeric label value(s).")
        elif not labels.isin([0, 1]).all():
            errors.append("Column isFraud must contain only 0/1 labels.")
        elif labels.nunique() < 2:
            errors.append("Column isFraud must contain both normal and fraud rows for training.")

    return errors


def normalize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Return PaySim-style rows with engineered features used by the dashboard."""
    normalized = df.copy()

    for column in BASE_COLUMNS:
        if column not in normalized.columns:
            if column in {"isFraud", "isFlaggedFraud"}:
                normalized[column] = 0
            elif column in {"nameOrig", "nameDest"}:
                normalized[column] = ""
            elif column == "type":
                normalized[column] = "TRANSFER"
            else:
                normalized[column] = 0.0

    for column in NUMERIC_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce").fillna(0)

    normalized["type"] = normalized["type"].fillna("TRANSFER").astype(str).str.upper()
    normalized["nameDest"] = normalized["nameDest"].fillna("").astype(str)

    normalized["errorBalanceOrig"] = (
        normalized["oldbalanceOrg"] - normalized["amount"] - normalized["newbalanceOrig"]
    ).abs()
    normalized["errorBalanceDest"] = (
        normalized["oldbalanceDest"] + normalized["amount"] - normalized["newbalanceDest"]
    ).abs()
    normalized["isMerchant"] = normalized["nameDest"].str.startswith("M").astype(int)
    normalized["zeroedOrigin"] = (
        (normalized["oldbalanceOrg"] > 0) & (normalized["newbalanceOrig"] == 0)
    ).astype(int)

    for payment_type in PAYMENT_TYPES:
        normalized[f"type_{payment_type}"] = (normalized["type"] == payment_type).astype(int)

    for column in FEATURE_COLUMNS:
        if column not in normalized.columns:
            normalized[column] = 0

    return normalized


def feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    normalized = normalize_transactions(df)
    return normalized[FEATURE_COLUMNS].astype(float)


def generate_demo_transactions(rows: int = 750, seed: int = 42) -> pd.DataFrame:
    """Create a deterministic PaySim-like sample for demos before Kaggle data is added."""
    rng = np.random.default_rng(seed)
    tx_type = rng.choice(
        PAYMENT_TYPES,
        size=rows,
        p=[0.34, 0.20, 0.26, 0.14, 0.06],
    )
    amount = rng.lognormal(mean=10.8, sigma=1.15, size=rows).round(2)
    amount = np.clip(amount, 250, 9_500_000)
    old_origin = rng.lognormal(mean=11.4, sigma=1.0, size=rows).round(2)
    old_dest = rng.lognormal(mean=11.2, sigma=1.15, size=rows).round(2)

    risky_type = np.isin(tx_type, ["TRANSFER", "CASH_OUT"])
    high_amount = amount > np.quantile(amount, 0.82)
    zero_origin = risky_type & (rng.random(rows) < 0.22)
    suspicious = risky_type & high_amount & (zero_origin | (rng.random(rows) < 0.25))

    new_origin = np.maximum(old_origin - amount, 0).round(2)
    new_origin[zero_origin] = 0

    dest_error = suspicious & (rng.random(rows) < 0.65)
    new_dest = (old_dest + amount).round(2)
    new_dest[dest_error] = old_dest[dest_error]

    is_fraud = suspicious.astype(int)
    merchant_dest = rng.random(rows) < 0.20
    name_dest_prefix = np.where(merchant_dest, "M", "C")

    demo = pd.DataFrame(
        {
            "step": rng.integers(1, 744, size=rows),
            "type": tx_type,
            "amount": amount,
            "nameOrig": [f"C{100000000 + i}" for i in range(rows)],
            "oldbalanceOrg": old_origin,
            "newbalanceOrig": new_origin,
            "nameDest": [f"{name_dest_prefix[i]}{900000000 + i}" for i in range(rows)],
            "oldbalanceDest": old_dest,
            "newbalanceDest": new_dest,
            "isFraud": is_fraud,
            "isFlaggedFraud": ((amount > 200_000) & (tx_type == "TRANSFER")).astype(int),
        }
    )
    return normalize_transactions(demo)


def read_scored_artifact(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        return None
    return normalize_transactions(pd.read_csv(path))
