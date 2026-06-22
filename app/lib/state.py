from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from .data import generate_demo_transactions, normalize_transactions
from .scoring import (
    ARTIFACTS_DIR,
    FULL_SCORED_ARTIFACT,
    has_full_scored_artifact,
    load_scored_transactions,
    score_transactions,
)


UPLOADED_RAW_KEY = "uploaded_raw_transactions"
UPLOADED_LABEL_KEY = "uploaded_dataset_label"
UPLOADED_SOURCE_KEY = "uploaded_dataset_source_key"
UPLOADED_SCORED_KEY = "uploaded_scored_transactions"
UPLOADED_MODEL_KEY = "uploaded_scored_model_key"
SCORED_CSV_BYTES_KEY = "scored_csv_bytes"


def _artifact_signature(artifacts_dir: Path = ARTIFACTS_DIR) -> float:
    """Cache key that changes whenever the scored artifact is rebuilt."""
    for name in (FULL_SCORED_ARTIFACT, "scored_transactions.csv"):
        path = artifacts_dir / name
        if path.exists():
            return path.stat().st_mtime
    return 0.0


@st.cache_resource(show_spinner="Đang tải toàn bộ giao dịch PaySim đã chấm điểm…", max_entries=1)
def _load_full_scored_cached(model_key: str, artifact_signature: float) -> pd.DataFrame:
    """Load (and sort) the full scored dataset once per model, reused across reruns."""
    return load_scored_transactions(model_key=model_key)


@dataclass(frozen=True)
class ActiveDataset:
    scored: pd.DataFrame
    label: str
    is_demo: bool
    is_uploaded: bool


def set_uploaded_dataset(raw_df: pd.DataFrame, label: str, source_key: str | None = None) -> None:
    st.session_state[UPLOADED_RAW_KEY] = normalize_transactions(raw_df)
    st.session_state[UPLOADED_LABEL_KEY] = label
    st.session_state[UPLOADED_SOURCE_KEY] = source_key
    st.session_state.pop(UPLOADED_SCORED_KEY, None)
    st.session_state.pop(UPLOADED_MODEL_KEY, None)
    st.session_state.pop(SCORED_CSV_BYTES_KEY, None)


def clear_uploaded_dataset() -> None:
    st.session_state.pop(UPLOADED_RAW_KEY, None)
    st.session_state.pop(UPLOADED_LABEL_KEY, None)
    st.session_state.pop(UPLOADED_SOURCE_KEY, None)
    st.session_state.pop(UPLOADED_SCORED_KEY, None)
    st.session_state.pop(UPLOADED_MODEL_KEY, None)
    st.session_state.pop(SCORED_CSV_BYTES_KEY, None)


def uploaded_source_key() -> str | None:
    return st.session_state.get(UPLOADED_SOURCE_KEY)


def has_scored_artifact(artifacts_dir: Path = ARTIFACTS_DIR) -> bool:
    return has_full_scored_artifact(artifacts_dir) or (artifacts_dir / "scored_transactions.csv").exists()


def get_active_dataset(model_key: str = "xgb") -> ActiveDataset:
    if UPLOADED_RAW_KEY in st.session_state:
        raw = st.session_state[UPLOADED_RAW_KEY]
        label = st.session_state.get(UPLOADED_LABEL_KEY, "Uploaded CSV")
        if (
            st.session_state.get(UPLOADED_MODEL_KEY) != model_key
            or UPLOADED_SCORED_KEY not in st.session_state
        ):
            st.session_state[UPLOADED_SCORED_KEY] = score_transactions(raw, model_key=model_key)
            st.session_state[UPLOADED_MODEL_KEY] = model_key
            st.session_state.pop(SCORED_CSV_BYTES_KEY, None)
        return ActiveDataset(
            scored=st.session_state[UPLOADED_SCORED_KEY],
            label=label,
            is_demo=False,
            is_uploaded=True,
        )

    if has_scored_artifact():
        label = "Full PaySim scored artifact" if has_full_scored_artifact() else "Trained PaySim artifacts"
        return ActiveDataset(
            scored=_load_full_scored_cached(model_key, _artifact_signature()),
            label=label,
            is_demo=False,
            is_uploaded=False,
        )

    return ActiveDataset(
        scored=score_transactions(generate_demo_transactions(), model_key=model_key),
        label="PaySim demo data",
        is_demo=True,
        is_uploaded=False,
    )
