from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib.constants import REPORT_ANALYST, RISK_HIGH
from lib.model_report import has_real_metrics, load_confusion_matrix, load_model_metrics, selected_model_label
from lib.report_builder import build_audit_report
from lib.state import get_active_dataset
from lib.styling import configure_page, inject_global_css, page_intro
from lib.ui import data_source_banner, human_money, kpi_card, section_header, sidebar_brand, sidebar_cta, surface


configure_page("Generate Audit Report")
inject_global_css()


@st.cache_data(show_spinner=False)
def cached_metrics(selected_model: str) -> pd.DataFrame:
    return load_model_metrics(model_key=selected_model)


@st.cache_data(show_spinner=False)
def cached_confusion_matrix(selected_model: str) -> np.ndarray:
    return load_confusion_matrix(model_key=selected_model)


with st.sidebar:
    sidebar_brand()
    model_key = st.selectbox("Model", ["xgb", "iforest", "heuristic"], format_func=str.upper)
    min_risk = st.slider("Risk threshold", 0.0, 1.0, RISK_HIGH, 0.05)
    top_n = st.number_input("Top transactions", min_value=5, max_value=15, value=15, step=5)
    sidebar_cta("Export a polished audit PDF", "Download ready")

page_intro(
    "Generate Report",
    "Create a downloadable audit PDF from the scored transaction queue and model evidence.",
    eyebrow="Audit export",
)

active = get_active_dataset(model_key=model_key)
df = active.scored
data_source_banner(active.label, is_demo=active.is_demo, is_uploaded=active.is_uploaded)
filtered = df[df["risk_score"] >= min_risk]
metrics = cached_metrics(model_key)
confusion = cached_confusion_matrix(model_key)

if not has_real_metrics():
    st.warning("Hãy train trên PaySim trước khi dùng PDF này như bằng chứng cuối cùng.")

flagged = int(filtered["predicted_fraud"].sum()) if not filtered.empty else 0
exposure = filtered.loc[filtered["predicted_fraud"] == 1, "amount"].sum() if not filtered.empty else 0
flag_rate = flagged / len(filtered) * 100 if len(filtered) else 0

kpi_cols = st.columns(4)
with kpi_cols[0]:
    kpi_card("Rows in report scope", f"{len(filtered):,}", icon="🗂️")
with kpi_cols[1]:
    kpi_card("Flagged fraud", f"{flagged:,}", delta=f"{flag_rate:.3f}% of scope", tone="bad", icon="🚩")
with kpi_cols[2]:
    kpi_card("Exposure", human_money(exposure), tone="warn", icon="💵")
with kpi_cols[3]:
    kpi_card("Risk threshold", f"{min_risk:.2f}", tone="neutral", icon="📊")

st.write("")
with surface():
    section_header("Report preview", f"Top {top_n} transactions that will be included in the PDF table")
    preview = filtered.sort_values("risk_score", ascending=False).head(int(top_n))[
        ["step", "type", "amount", "errorBalanceOrig", "errorBalanceDest", "risk_score", "risk_level"]
    ]
    st.dataframe(
        preview,
        width="stretch",
        hide_index=True,
        column_config={
            "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "errorBalanceOrig": st.column_config.NumberColumn("Origin error", format="$%.2f"),
            "errorBalanceDest": st.column_config.NumberColumn("Dest error", format="$%.2f"),
            "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=1, format="%.3f"),
            "risk_level": st.column_config.TextColumn("Level"),
        },
    )

if st.button("Tạo báo cáo PDF", type="primary"):
    report_rows = filtered.sort_values("risk_score", ascending=False).head(int(top_n)).copy()
    pdf_bytes = build_audit_report(
        filtered,
        report_rows,
        metrics,
        confusion,
        analyst=REPORT_ANALYST,
        model_label=selected_model_label(model_key),
    )
    st.download_button(
        "Tải báo cáo PDF",
        data=pdf_bytes,
        file_name="audit_report_23051894.pdf",
        mime="application/pdf",
    )
