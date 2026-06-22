from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import recall_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from train_models import tune_threshold  # noqa: E402


def test_tune_threshold_meets_target_recall() -> None:
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    scores = np.array([0.10, 0.20, 0.30, 0.55, 0.40, 0.62, 0.80, 0.95])
    threshold = tune_threshold(y, scores, target_recall=1.0)
    preds = (scores >= threshold).astype(int)
    assert recall_score(y, preds) >= 1.0
    assert threshold >= 0.05


def test_tune_threshold_result_is_at_least_floor() -> None:
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    scores = np.array([0.10, 0.20, 0.30, 0.55, 0.40, 0.62, 0.80, 0.95])
    # target_recall=0.5 → threshold around 0.40; floor=0.70 enforces minimum.
    threshold = tune_threshold(y, scores, target_recall=0.5, floor=0.70)
    assert threshold >= 0.70
