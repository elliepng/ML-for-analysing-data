from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib.charts import confusion_matrix_figure, curve_figure  # noqa: E402
from lib.model_report import (  # noqa: E402
    has_real_metrics,
    load_confusion_matrix,
    load_model_metrics,
    load_pr_curve,
    load_roc_curve,
)
from lib.styling import configure_page, inject_global_css, page_intro  # noqa: E402
from lib.ui import section_header, sidebar_brand, sidebar_cta, surface  # noqa: E402


configure_page("Model Analysis")
inject_global_css()


@st.cache_data(show_spinner=False)
def cached_metrics() -> pd.DataFrame:
    return load_model_metrics()


@st.cache_data(show_spinner=False)
def cached_confusion_matrix() -> np.ndarray:
    return load_confusion_matrix()


@st.cache_data(show_spinner=False)
def cached_real_metrics_status() -> bool:
    return has_real_metrics()


with st.sidebar:
    sidebar_brand()
    st.caption("Model evidence is read from artifacts/model_metrics.json.")
    sidebar_cta("Train PaySim to unlock real curves", "Model evidence")

page_intro(
    "Model Analysis",
    "Evidence page for comparing anomaly detection, supervised learning, and the legacy rule.",
    eyebrow="Model evidence",
)

metrics = cached_metrics()

if not cached_real_metrics_status():
    st.warning("Chưa có metrics thật. Hãy chạy train_models.py để hiện đầy đủ metric và curve từ PaySim.")

left, right = st.columns(2)
with left:
    with surface():
        section_header("Model comparison", "Precision, recall, F1, AUC-PR, and ROC-AUC from the held-out test set")
        st.dataframe(
            metrics,
            width="stretch",
            hide_index=True,
            column_config={
                "precision": st.column_config.NumberColumn("Precision", format="%.3f"),
                "recall": st.column_config.NumberColumn("Recall", format="%.3f"),
                "f1": st.column_config.NumberColumn("F1", format="%.3f"),
                "auc_pr": st.column_config.NumberColumn("AUC-PR", format="%.3f"),
                "roc_auc": st.column_config.NumberColumn("ROC-AUC", format="%.3f"),
            },
        )
with right:
    with surface():
        section_header("Confusion matrix", "XGBoost predictions at the configured risk threshold")
        st.plotly_chart(confusion_matrix_figure(cached_confusion_matrix()), use_container_width=True)

st.write("")
left_curve, right_curve = st.columns(2)
with left_curve:
    roc_points = load_roc_curve()
    if roc_points:
        x, y = roc_points
        with surface():
            section_header("ROC curve", "Higher true-positive capture at lower false-positive cost is better")
            st.plotly_chart(
                curve_figure("ROC curve", x, y, "False positive rate", "True positive rate"),
                use_container_width=True,
            )
    else:
        st.warning("Chưa có ROC thật — hãy chạy train_models.py để sinh artifacts/model_metrics.json.")

with right_curve:
    pr_points = load_pr_curve()
    if pr_points:
        recall, precision = pr_points
        with surface():
            section_header("Precision-recall curve", "Preferred over accuracy because fraud is a rare class")
            st.plotly_chart(
                curve_figure("Precision-recall curve", recall, precision, "Recall", "Precision"),
                use_container_width=True,
            )
    else:
        st.warning("Chưa có Precision-Recall thật — hãy chạy train_models.py để sinh artifacts/model_metrics.json.")

st.info("Tập trung vào precision, recall, F1 và AUC-PR. Accuracy bị lệch vì class fraud quá mất cân bằng.")
