from __future__ import annotations

from pathlib import Path

ARTIFACTS_DIR = Path(__file__).resolve().parents[2] / "artifacts"

RISK_HIGH = 0.80
RISK_MEDIUM = 0.50
AMOUNT_REFERENCE = 10_000_000
REPORT_ANALYST = "Phạm Ngọc Ánh – 23051894"

PAYMENT_TYPES = ["CASH_OUT", "TRANSFER", "PAYMENT", "CASH_IN", "DEBIT"]

BASE_COLUMNS = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "isFraud",
    "isFlaggedFraud",
]

FEATURE_COLUMNS = [
    "step",
    "amount",
    "oldbalanceOrg",
    "newbalanceOrig",
    "oldbalanceDest",
    "newbalanceDest",
    "errorBalanceOrig",
    "errorBalanceDest",
    "isMerchant",
    "zeroedOrigin",
    "type_CASH_OUT",
    "type_TRANSFER",
    "type_PAYMENT",
    "type_CASH_IN",
    "type_DEBIT",
]

MODEL_LABELS = {
    "xgb": "XGBoost supervised",
    "iforest": "Isolation Forest anomaly",
    "heuristic": "Fallback risk rules",
}
