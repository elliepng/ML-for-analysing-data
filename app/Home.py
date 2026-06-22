from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib.charts import exposure_trend, fraud_type_stacked, recall_gauge, type_mix_donut
from lib.model_report import has_real_metrics, load_model_metrics
from lib.state import get_active_dataset
from lib.styling import configure_page, inject_global_css
from lib.ui import (
    empty_state,
    human_money,
    model_compare,
    note_card,
    pbi_header,
    pbi_kpi,
    risk_mix,
    section_header,
    sidebar_brand,
    sidebar_cta,
    stat_panel,
    surface,
)


configure_page("Fraud Detection Overview")
inject_global_css()


with st.sidebar:
    sidebar_brand()
    st.header("Controls")
    model_key = st.selectbox("Model", ["xgb", "iforest", "heuristic"], format_func=str.upper)
    min_risk = st.slider("Minimum risk", 0.0, 1.0, 0.0, 0.05)
    st.caption("Artifacts are loaded when available; otherwise demo data is generated.")
    sidebar_cta("Upload CSV to score real transactions", "Open Upload page")

active = get_active_dataset(model_key=model_key)
df = active.scored
filtered = df[df["risk_score"] >= min_risk].copy()

total_transactions = len(filtered)
flagged = int(filtered["predicted_fraud"].sum())
flag_rate = (flagged / total_transactions * 100) if total_transactions else 0
estimated_loss = filtered.loc[filtered["predicted_fraud"] == 1, "amount"].sum()
high_count = int((filtered["risk_level"] == "High").sum())
medium_count = int((filtered["risk_level"] == "Medium").sum())
low_count = int((filtered["risk_level"] == "Low").sum())

source = "Demo" if active.is_demo else ("Upload" if active.is_uploaded else "PaySim")
pbi_header(
    "Fraud Analytics — PaySim Audit",
    f"FAA4023 · 23051894 · cập nhật {datetime.now():%d %b %Y, %H:%M}",
    chips=[
        ("Source", source),
        ("Model", model_key.upper()),
        ("Risk ≥", f"{min_risk:.2f}"),
        ("Rows", f"{total_transactions:,}"),
    ],
)

# --- Sparkline series (binned by PaySim step) ---
spark_tx = spark_flag = spark_exp = spark_high = None
if not filtered.empty and filtered["step"].nunique() > 1:
    bins = min(12, int(filtered["step"].nunique()))
    work = filtered.assign(flagged_amount=filtered["amount"].where(filtered["predicted_fraud"] == 1, 0))
    work["_bucket"] = pd.cut(work["step"], bins=bins)
    agg = work.groupby("_bucket", observed=True).agg(
        tx=("amount", "size"),
        flag=("predicted_fraud", "sum"),
        exp=("flagged_amount", "sum"),
        high=("risk_level", lambda s: int((s == "High").sum())),
    )
    spark_tx = agg["tx"].tolist()
    spark_flag = agg["flag"].tolist()
    spark_exp = agg["exp"].cumsum().tolist()
    spark_high = agg["high"].tolist()

kpi_cols = st.columns(4)
with kpi_cols[0]:
    pbi_kpi("Transactions scored", f"{total_transactions:,}", delta="100% scored", spark=spark_tx)
with kpi_cols[1]:
    pbi_kpi("Flagged fraud", f"{flagged:,}", delta=f"{flag_rate:.2f}% of scope", tone="bad", spark=spark_flag)
with kpi_cols[2]:
    pbi_kpi("Estimated exposure", human_money(estimated_loss), delta="flagged amount", tone="warn", spark=spark_exp)
with kpi_cols[3]:
    pbi_kpi("High-risk rows", f"{high_count:,}", delta="risk ≥ 0.80", tone="bad", spark=spark_high)

# --- Model metrics ---
metrics = load_model_metrics()
xgb_recall = xgb_precision = xgb_auc_pr = xgb_f1 = xgb_roc_auc = 0.0
if has_real_metrics() and "recall" in metrics.columns:
    xgb_rows = metrics.iloc[0:1]
    if not xgb_rows.empty:
        xgb_recall = float(xgb_rows.iloc[0]["recall"]) * 100
        xgb_precision = float(xgb_rows.iloc[0].get("precision", 0)) * 100
        xgb_auc_pr = float(xgb_rows.iloc[0].get("auc_pr", 0)) * 100
        xgb_f1 = float(xgb_rows.iloc[0].get("f1", 0)) * 100
        xgb_roc_auc = float(xgb_rows.iloc[0].get("roc_auc", 0)) * 100

model_rows: list[tuple[str, float, float]] = []
if has_real_metrics() and "recall" in metrics.columns:
    short_name = {
        "XGBoost supervised": "XGBoost",
        "Random Forest supervised": "Random Forest",
        "Isolation Forest": "Isolation Forest",
        "Bank rule isFlaggedFraud": "Bank rule (cũ)",
    }
    for _, mrow in metrics.iterrows():
        name = str(mrow["model"])
        try:
            model_rows.append((short_name.get(name, name), float(mrow["recall"]) * 100, float(mrow["auc_pr"]) * 100))
        except (TypeError, ValueError):
            continue

st.write("")

# --- Mid row: exposure trend + type donut ---
mid_left, mid_right = st.columns([1.55, 1])
with mid_left:
    with surface():
        section_header("Flagged exposure trend", "Cumulative flagged amount by PaySim step")
        if filtered.empty:
            empty_state("", "Chưa có giao dịch trong scope", "Hạ ngưỡng Minimum risk ở thanh bên để hiện biểu đồ.")
        else:
            st.plotly_chart(exposure_trend(filtered), use_container_width=True)
with mid_right:
    with surface():
        section_header("Transaction type mix", "Tỷ trọng các loại giao dịch trong scope")
        if filtered.empty:
            empty_state("", "Không có dữ liệu", "Điều chỉnh bộ lọc để xem thành phần loại giao dịch.")
        else:
            st.plotly_chart(type_mix_donut(filtered), use_container_width=True)

st.write("")

# --- Bottom row: top risky matrix + recall gauge + fraud by type ---
bot_left, bot_mid, bot_right = st.columns([1.4, 0.85, 1])
with bot_left:
    with surface():
        section_header("Top risky transactions", "Highest exposure rows in the current filter")
        if filtered.empty:
            empty_state("", "Không có giao dịch khớp bộ lọc", "Giảm Minimum risk hoặc đổi model ở thanh bên.")
        else:
            risk_mix(high_count, medium_count, low_count)
            top_rows = filtered.sort_values("risk_score", ascending=False).head(8)[
                ["type", "step", "amount", "risk_score", "risk_level"]
            ]
            st.dataframe(
                top_rows,
                width="stretch",
                hide_index=True,
                column_config={
                    "type": st.column_config.TextColumn("Type"),
                    "step": st.column_config.NumberColumn("Step", format="%d"),
                    "amount": st.column_config.NumberColumn("Amount", format="$%.0f"),
                    "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=1, format="%.3f"),
                    "risk_level": st.column_config.TextColumn("Level"),
                },
            )
with bot_mid:
    with surface():
        section_header("Model recall", "XGBoost · target 95%")
        if has_real_metrics():
            st.plotly_chart(recall_gauge(xgb_recall, target=95.0), use_container_width=True)
            stat_panel(
                [
                    ("Precision", f"{xgb_precision:.1f}%", "good"),
                    ("F1-score", f"{xgb_f1:.1f}%", "neutral"),
                    ("AUC-PR", f"{xgb_auc_pr:.1f}%", "warn"),
                    ("ROC-AUC", f"{xgb_roc_auc:.1f}%", "neutral"),
                ]
            )
        else:
            note_card(
                "Model metrics chưa sẵn sàng",
                "Train PaySim (scripts/train_models.py) để hiện Recall, Precision và AUC-PR thật.",
            )
with bot_right:
    with surface():
        section_header("Fraud by type", "Flagged vs total volume")
        if filtered.empty:
            empty_state("", "Không có dữ liệu", "Điều chỉnh bộ lọc để xem phân bố theo loại giao dịch.")
        else:
            st.plotly_chart(fraud_type_stacked(filtered), use_container_width=True)

# --- Model comparison ---
if model_rows:
    st.write("")
    with surface():
        section_header("Model comparison", "Recall và AUC-PR trên tập test PaySim tách riêng")
        model_compare(model_rows)
