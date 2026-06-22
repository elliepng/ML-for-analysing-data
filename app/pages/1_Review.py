from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib.constants import PAYMENT_TYPES, RISK_MEDIUM
from lib.state import get_active_dataset
from lib.styling import configure_page, inject_global_css, page_intro
from lib.ui import data_source_banner, human_money, kpi_card, risk_badge, section_header, sidebar_brand, sidebar_cta, surface


configure_page("Transaction Review")
inject_global_css()


page_intro(
    "Transaction Review",
    "Prioritized queue for audit review with type, amount, and risk filters.",
    eyebrow="Audit queue",
)

with st.sidebar:
    sidebar_brand()
    model_key = st.selectbox("Model", ["xgb", "iforest", "heuristic"], format_func=str.upper)
    selected_types = st.multiselect("Transaction type", PAYMENT_TYPES, default=["TRANSFER", "CASH_OUT"])
    min_risk = st.slider("Risk threshold", 0.0, 1.0, RISK_MEDIUM, 0.05)
    amount_max = st.number_input("Maximum amount", min_value=0.0, value=10_000_000.0, step=50_000.0)
    sidebar_cta("Review high-risk transfers first", "Audit queue")

active = get_active_dataset(model_key=model_key)
df = active.scored
data_source_banner(active.label, is_demo=active.is_demo, is_uploaded=active.is_uploaded)
filtered = df[
    df["type"].isin(selected_types)
    & (df["risk_score"] >= min_risk)
    & (df["amount"] <= amount_max)
].copy()

review_count = len(filtered)
review_exposure = filtered["amount"].sum()
high_count = int((filtered["risk_level"] == "High").sum())

kpi_cols = st.columns(3)
with kpi_cols[0]:
    kpi_card("Transactions requiring review", f"{review_count:,}", tone="warn", icon="🔎")
with kpi_cols[1]:
    kpi_card("Filtered exposure", human_money(review_exposure), tone="bad" if review_exposure else "neutral", icon="💵")
with kpi_cols[2]:
    kpi_card("High-risk rows", f"{high_count:,}", tone="bad", icon="🚩")

st.write("")
st.markdown(
    "<div style='display:flex;align-items:center;gap:0.55rem;'>"
    "<span class='caption' style='font-weight:600'>Risk levels</span>"
    f"{risk_badge('High')}{risk_badge('Medium')}{risk_badge('Low')}"
    "</div>",
    unsafe_allow_html=True,
)

display_columns = [
    "step",
    "type",
    "amount",
    "nameOrig",
    "oldbalanceOrg",
    "newbalanceOrig",
    "nameDest",
    "oldbalanceDest",
    "newbalanceDest",
    "errorBalanceOrig",
    "errorBalanceDest",
    "risk_score",
    "risk_level",
]

st.write("")
with surface():
    section_header("Filtered review queue", "Sorted by model risk score for audit triage")
    st.dataframe(
        filtered[display_columns].head(300),
        width="stretch",
        hide_index=True,
        column_config={
            "amount": st.column_config.NumberColumn("Amount", format="$%.2f"),
            "oldbalanceOrg": st.column_config.NumberColumn("Old origin", format="$%.2f"),
            "newbalanceOrig": st.column_config.NumberColumn("New origin", format="$%.2f"),
            "oldbalanceDest": st.column_config.NumberColumn("Old dest", format="$%.2f"),
            "newbalanceDest": st.column_config.NumberColumn("New dest", format="$%.2f"),
            "errorBalanceOrig": st.column_config.NumberColumn("Origin error", format="$%.2f"),
            "errorBalanceDest": st.column_config.NumberColumn("Dest error", format="$%.2f"),
            "risk_score": st.column_config.ProgressColumn("Risk", min_value=0, max_value=1, format="%.3f"),
            "risk_level": st.column_config.TextColumn("Level"),
        },
    )
