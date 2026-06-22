from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib.charts import amount_vs_risk, fraud_by_type, risk_distribution
from lib.state import get_active_dataset
from lib.styling import configure_page, inject_global_css, page_intro
from lib.ui import data_source_banner, section_header, sidebar_brand, sidebar_cta, surface


configure_page("Analytics")
inject_global_css()


with st.sidebar:
    sidebar_brand()
    model_key = st.selectbox("Model", ["xgb", "iforest", "heuristic"], format_func=str.upper)
    min_risk = st.slider("Minimum risk", 0.0, 1.0, 0.0, 0.05)
    sidebar_cta("Use analytics to explain report visuals", "Evidence view")

page_intro(
    "Analytics",
    "Explore distribution, transaction mix, and amount-risk relationships for the active dataset.",
    eyebrow="Exploration",
)

active = get_active_dataset(model_key=model_key)
data_source_banner(active.label, is_demo=active.is_demo, is_uploaded=active.is_uploaded)
filtered = active.scored[active.scored["risk_score"] >= min_risk]

left, right = st.columns([1, 1])
with left:
    with surface():
        section_header("Risk distribution", "How model scores cluster across the filtered dataset")
        st.plotly_chart(risk_distribution(filtered), use_container_width=True)
with right:
    with surface():
        section_header("Fraud by type", "Flagged volume compared with transaction mix")
        st.plotly_chart(fraud_by_type(filtered), use_container_width=True)

st.write("")
with surface():
    section_header("Amount vs risk", "Large balance movements with high risk scores are prioritized")
    st.plotly_chart(amount_vs_risk(filtered.head(500)), use_container_width=True)
