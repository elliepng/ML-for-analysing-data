from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib.constants import PAYMENT_TYPES, RISK_HIGH, RISK_MEDIUM  # noqa: E402
from lib.scoring import score_single_transaction  # noqa: E402
from lib.styling import configure_page, inject_global_css, page_intro  # noqa: E402
from lib.ui import kpi_card, risk_badge, section_header, sidebar_brand, sidebar_cta, surface  # noqa: E402


configure_page("New Transaction Scoring")
inject_global_css()

page_intro(
    "New Transaction Scoring",
    "Manual transaction scoring for demo and audit triage scenarios.",
    eyebrow="Manual scoring",
)

with st.sidebar:
    sidebar_brand()
    model_key = st.selectbox("Model", ["xgb", "heuristic"], format_func=str.upper)
    st.caption("Manual scoring uses XGBoost when artifacts exist. Isolation Forest is evaluated in batch on the Model page.")
    sidebar_cta("Score one transaction before release", "Manual check")

form_col, help_col = st.columns([1.25, 0.75])
with form_col:
    with surface():
        section_header("Transaction input", "Nhập một giao dịch mẫu để chấm điểm ngay")
        with st.form("score_transaction"):
            col1, col2, col3 = st.columns(3)
            with col1:
                step = st.number_input("Step", min_value=1, value=372, step=1)
                tx_type = st.selectbox("Type", PAYMENT_TYPES, index=1)
                amount = st.number_input("Amount", min_value=0.0, value=750_000.0, step=10_000.0)
            with col2:
                old_origin = st.number_input("Old balance origin", min_value=0.0, value=750_000.0, step=10_000.0)
                new_origin = st.number_input("New balance origin", min_value=0.0, value=0.0, step=10_000.0)
            with col3:
                old_dest = st.number_input("Old balance destination", min_value=0.0, value=100_000.0, step=10_000.0)
                new_dest = st.number_input("New balance destination", min_value=0.0, value=100_000.0, step=10_000.0)
                is_merchant = st.checkbox("Destination is merchant", value=False)

            submitted = st.form_submit_button("Score transaction")
with help_col:
    with surface():
        section_header("Khi nào score tăng", "Các dấu hiệu này thường kéo risk score đi lên.")
        st.markdown(
            "- Amount lớn so với số dư gốc.\n"
            "- Origin về 0 nhưng đích không tăng tương ứng.\n"
            "- TRANSFER và CASH_OUT thường cần nhìn kỹ hơn."
        )

if submitted:
    dest_prefix = "M" if is_merchant else "C"
    result = score_single_transaction(
        {
            "step": step,
            "type": tx_type,
            "amount": amount,
            "nameOrig": "C_DEMO_ORIGIN",
            "oldbalanceOrg": old_origin,
            "newbalanceOrig": new_origin,
            "nameDest": f"{dest_prefix}_DEMO_DEST",
            "oldbalanceDest": old_dest,
            "newbalanceDest": new_dest,
            "isFraud": 0,
            "isFlaggedFraud": 0,
        },
        model_key=model_key,
    )
    score = float(result["risk_score"])
    kpi_card(
        "Risk score",
        f"{score:.3f}",
        tone="bad" if score >= RISK_HIGH else "warn" if score >= RISK_MEDIUM else "good",
        icon="📈",
    )
    st.markdown(
        risk_badge(str(result["risk_level"])),
        unsafe_allow_html=True,
    )
    if score >= RISK_HIGH:
        st.error("Ưu tiên manual review trước khi release. Kiểm tra biến động số dư và counterparties.")
    elif score >= RISK_MEDIUM:
        st.warning("Cần xem lại balance movement và bằng chứng giao dịch trước khi chấp nhận.")
    else:
        st.success("Theo input hiện tại, giao dịch này có tín hiệu tương đối bình thường.")
