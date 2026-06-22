from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from lib.data import FEATURE_COLUMNS, feature_matrix, generate_demo_transactions, normalize_transactions  # noqa: E402
from lib.scoring import (  # noqa: E402
    build_full_scored_artifact,
    classify_risk,
    load_scored_transactions,
    score_single_transaction,
    score_transactions,
)
from lib.upload import score_uploaded_csv, scored_to_csv_bytes, validate_upload_columns  # noqa: E402


def test_demo_transactions_have_feature_contract() -> None:
    demo = generate_demo_transactions(rows=25, seed=7)
    matrix = feature_matrix(demo)
    assert list(matrix.columns) == FEATURE_COLUMNS
    assert matrix.isna().sum().sum() == 0


def test_score_transactions_returns_sorted_risk_scores() -> None:
    demo = generate_demo_transactions(rows=80, seed=11)
    scored = score_transactions(demo, model_key="heuristic")
    assert scored["risk_score"].between(0, 1).all()
    assert scored["risk_score"].is_monotonic_decreasing
    assert {"predicted_fraud", "risk_level"}.issubset(scored.columns)


def test_single_transaction_high_risk_scenario() -> None:
    result = score_single_transaction(
        {
            "step": 1,
            "type": "TRANSFER",
            "amount": 1_000_000,
            "oldbalanceOrg": 1_000_000,
            "newbalanceOrig": 0,
            "oldbalanceDest": 50_000,
            "newbalanceDest": 50_000,
            "nameDest": "C123",
        },
        model_key="heuristic",
    )
    assert result["risk_score"] >= 0.8
    assert classify_risk(float(result["risk_score"])) == "High"


def test_normalize_accepts_partial_rows() -> None:
    normalized = normalize_transactions(
        generate_demo_transactions(rows=1, seed=99)[["type", "amount", "oldbalanceOrg", "newbalanceOrig"]]
    )
    assert normalized["nameDest"].iloc[0] == ""
    assert normalized["isFraud"].iloc[0] == 0


def test_single_transaction_amount_affects_heuristic_score() -> None:
    base = {
        "step": 1,
        "type": "TRANSFER",
        "oldbalanceDest": 50_000,
        "newbalanceDest": 50_000,
        "nameDest": "C123",
    }
    low = score_single_transaction(
        {**base, "amount": 1_000, "oldbalanceOrg": 1_000, "newbalanceOrig": 0},
        model_key="heuristic",
    )
    high = score_single_transaction(
        {**base, "amount": 1_000_000, "oldbalanceOrg": 1_000_000, "newbalanceOrig": 0},
        model_key="heuristic",
    )
    assert high["risk_score"] > low["risk_score"]


def test_upload_csv_scores_transactions() -> None:
    raw = generate_demo_transactions(rows=12, seed=13)
    csv_bytes = scored_to_csv_bytes(raw)
    scored = score_uploaded_csv(csv_bytes, model_key="heuristic")
    assert {"risk_score", "risk_level", "predicted_fraud"}.issubset(scored.columns)
    assert scored["risk_score"].between(0, 1).all()


def test_upload_validation_reports_missing_columns() -> None:
    errors = validate_upload_columns(generate_demo_transactions(rows=1, seed=14)[["type", "amount"]])
    assert any("oldbalanceOrg" in error for error in errors)


def test_non_xgb_selection_rescores_saved_artifact(tmp_path: Path) -> None:
    raw = generate_demo_transactions(rows=20, seed=22)
    artifact = normalize_transactions(raw)
    artifact["risk_score"] = 0.0
    artifact["predicted_fraud"] = 0
    artifact.to_csv(tmp_path / "scored_transactions.csv", index=False)

    xgb_loaded = load_scored_transactions(model_key="xgb", artifacts_dir=tmp_path)
    heuristic_loaded = load_scored_transactions(model_key="heuristic", artifacts_dir=tmp_path)

    assert xgb_loaded["risk_score"].max() == 0.0
    assert heuristic_loaded["risk_score"].max() > 0.0
    assert set(heuristic_loaded["model_used"]) == {"Fallback risk rules"}


def test_upload_validation_accepts_large_full_dataset() -> None:
    raw = generate_demo_transactions(rows=200_010, seed=23)
    errors = validate_upload_columns(raw)
    assert errors == []


def test_full_scored_artifact_builds_and_loads_from_csv(tmp_path: Path) -> None:
    raw = generate_demo_transactions(rows=25, seed=24)
    input_path = tmp_path / "transactions.csv"
    raw.to_csv(input_path, index=False)

    output_path = build_full_scored_artifact(
        input_path,
        model_key="heuristic",
        artifacts_dir=tmp_path,
        chunksize=10,
    )
    loaded = load_scored_transactions(model_key="xgb", artifacts_dir=tmp_path)

    assert output_path.exists()
    assert len(loaded) == 25
    assert {"risk_score", "predicted_fraud", "risk_level"}.issubset(loaded.columns)
