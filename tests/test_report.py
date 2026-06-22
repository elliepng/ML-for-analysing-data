from __future__ import annotations

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from lib.data import generate_demo_transactions  # noqa: E402
from lib.model_report import load_confusion_matrix, load_model_metrics  # noqa: E402
from lib.report_builder import build_audit_report, summarize_scored  # noqa: E402
from lib.scoring import score_transactions  # noqa: E402


def _metrics(label: str = "XGBoost supervised") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "model": label,
                "precision": 0.9,
                "recall": 0.8,
                "f1": 0.85,
                "auc_pr": 0.88,
                "roc_auc": 0.92,
            }
        ]
    )


def test_build_audit_report_returns_pdf_bytes() -> None:
    scored = score_transactions(generate_demo_transactions(rows=60, seed=5), model_key="heuristic")
    pdf = build_audit_report(scored, scored.head(15), _metrics(), np.array([[50, 2], [3, 5]]))
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1_000


def test_report_uses_supplied_scored_kpis_with_demo_metrics() -> None:
    scored = score_transactions(generate_demo_transactions(rows=40, seed=9), model_key="heuristic")
    summary = summarize_scored(scored)
    pdf = build_audit_report(
        scored,
        scored.head(15),
        _metrics("DEMO (chưa train) - train PaySim to populate real metrics"),
        np.array([[0, 0], [0, 0]]),
    )
    assert pdf.startswith(b"%PDF")
    assert summary["total"] == len(scored)
    assert summary["flagged"] == int(scored["predicted_fraud"].sum())


def test_summary_uses_full_scope_not_top_rows() -> None:
    scored = score_transactions(generate_demo_transactions(rows=120, seed=3), model_key="heuristic")
    top = scored.head(15)
    assert summarize_scored(scored)["total"] == 120
    assert len(top) == 15


def test_model_report_filters_metrics_and_confusion_by_model(tmp_path: Path) -> None:
    payload = {
        "models": [
            {"model": "XGBoost supervised", "precision": 1.0, "recall": 0.9, "f1": 0.95, "auc_pr": 0.9, "roc_auc": 0.9},
            {"model": "Isolation Forest", "precision": 0.4, "recall": 0.3, "f1": 0.34, "auc_pr": 0.2, "roc_auc": 0.6},
        ],
        "confusion_matrix": [[9, 1], [2, 8]],
        "confusion_matrices": {"xgb": [[9, 1], [2, 8]], "iforest": [[7, 3], [5, 5]]},
    }
    (tmp_path / "model_metrics.json").write_text(json.dumps(payload), encoding="utf-8")

    metrics = load_model_metrics(tmp_path, model_key="iforest")
    confusion = load_confusion_matrix(tmp_path, model_key="iforest")

    assert metrics["model"].tolist() == ["Isolation Forest"]
    assert confusion.tolist() == [[7, 3], [5, 5]]
