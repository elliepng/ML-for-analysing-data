from __future__ import annotations

from io import BytesIO, StringIO

import pandas as pd

from .data import REQUIRED_UPLOAD_COLUMNS, normalize_transactions, validate_transaction_schema
from .scoring import score_transactions


MIN_UPLOAD_COLUMNS = REQUIRED_UPLOAD_COLUMNS


def validate_upload_columns(df: pd.DataFrame) -> list[str]:
    """Validate uploaded CSV before full-dataset scoring."""
    return validate_transaction_schema(df, required_columns=MIN_UPLOAD_COLUMNS)


def read_uploaded_csv(file_bytes: bytes) -> pd.DataFrame:
    buffer = BytesIO(file_bytes)
    return pd.read_csv(buffer)


def score_uploaded_csv(file_bytes: bytes, model_key: str = "xgb") -> pd.DataFrame:
    raw = read_uploaded_csv(file_bytes)
    errors = validate_upload_columns(raw)
    if errors:
        raise ValueError("; ".join(errors))
    return score_transactions(normalize_transactions(raw), model_key=model_key)


def scored_to_csv_bytes(scored: pd.DataFrame) -> bytes:
    output = StringIO()
    scored.to_csv(output, index=False)
    return output.getvalue().encode("utf-8")
