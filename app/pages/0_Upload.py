from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from lib.constants import REPORT_ANALYST, RISK_HIGH  # noqa: E402
from lib.data import generate_demo_transactions  # noqa: E402
from lib.model_report import load_confusion_matrix, load_model_metrics, selected_model_label  # noqa: E402
from lib.report_builder import build_audit_report  # noqa: E402
from lib.scoring import build_full_scored_artifact, has_full_scored_artifact  # noqa: E402
from lib.state import clear_uploaded_dataset, get_active_dataset, set_uploaded_dataset, uploaded_source_key  # noqa: E402
from lib.styling import configure_page, inject_global_css, page_intro  # noqa: E402
from lib.ui import (  # noqa: E402
    data_source_banner,
    human_money,
    kpi_card,
    section_header,
    sidebar_brand,
    sidebar_cta,
    surface,
)
from lib.upload import read_uploaded_csv, scored_to_csv_bytes, validate_upload_columns  # noqa: E402


configure_page("Upload and Score")
inject_global_css()

LOCAL_PAYSIM_PATH = Path(__file__).resolve().parents[2] / "data" / "raw" / "paysim dataset.csv"


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    return read_uploaded_csv(file_bytes)


with st.sidebar:
    sidebar_brand()
    model_key = st.selectbox("Model", ["xgb", "iforest", "heuristic"], format_func=str.upper)
    min_risk = st.slider("Report risk threshold", 0.0, 1.0, RISK_HIGH, 0.05)
    sidebar_cta("Generate audit evidence after scoring", "PDF ready")

page_intro(
    "Upload & Score",
    "Upload transaction CSVs, run classification, download scored results, and generate audit evidence.",
    eyebrow="Data intake",
)

st.info(
    "App hỗ trợ upload và chấm điểm toàn bộ file CSV tới 600 MB. File lớn sẽ cần thêm RAM và thời gian xử lý trong lần score đầu tiên."
)

local_ready = LOCAL_PAYSIM_PATH.exists()

if local_ready:
    entry_col, guide_col = st.columns([1.15, 0.85])
else:
    entry_col = st.container()

with entry_col:
    with surface():
        section_header("Upload transaction file", "Nạp dữ liệu để chấm điểm, xem preview và xuất bằng chứng")
        uploaded = st.file_uploader("Tải file giao dịch (CSV) — tối đa 600 MB", type=["csv"])
        left, right = st.columns([0.7, 0.3])
        with left:
            st.caption("Cột bắt buộc: type, amount, oldbalanceOrg, newbalanceOrig, oldbalanceDest, newbalanceDest.")
        with right:
            use_demo = st.button("Dùng dữ liệu PaySim demo")

if local_ready:
    with guide_col:
        with surface():
            section_header("PaySim local full", "Dùng file thực nghiệm có sẵn mà không cần upload qua browser.")
            st.markdown(
                "- Tạo cache scored đầy đủ từ `data/raw/paysim dataset.csv`.\n"
                "- Cache được lưu trong `artifacts/full_scored_transactions.parquet`.\n"
                "- Các trang dashboard sẽ tự dùng cache này khi không có upload session."
            )
            artifact_ready = has_full_scored_artifact()
            st.caption(
                "Trạng thái: đã có PaySim local · "
                + ("đã có cache full scored" if artifact_ready else "chưa có cache full scored")
            )
            if st.button("Tạo/dùng PaySim full cache"):
                try:
                    with st.spinner("Đang score toàn bộ PaySim và lưu cache Parquet..."):
                        build_full_scored_artifact(LOCAL_PAYSIM_PATH, model_key=model_key)
                        clear_uploaded_dataset()
                    st.success("Đã tạo cache PaySim full. Dashboard sẽ dùng full scored artifact.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Không tạo được PaySim full cache: {exc}")

if use_demo:
    set_uploaded_dataset(
        generate_demo_transactions(rows=750, seed=42),
        "PaySim demo uploaded to session",
        source_key="demo:750:42",
    )
    st.toast("Demo data loaded into session.", icon="🛡️")

if uploaded is not None:
    try:
        uploaded_file_id = getattr(uploaded, "file_id", "")
        current_source = f"{uploaded.name}:{uploaded.size}:{uploaded_file_id}"
        if uploaded_source_key() != current_source:
            with st.spinner("Đang đọc & xử lý toàn bộ file..."):
                raw = parse_csv(uploaded.getvalue())
                errors = validate_upload_columns(raw)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                set_uploaded_dataset(raw, uploaded.name, source_key=current_source)
                st.success(f"Đã nạp toàn bộ {len(raw):,} dòng từ {uploaded.name}.")
        else:
            st.info(f"Đang dùng file đã nạp: {uploaded.name}.")
    except Exception as exc:
        st.error(f"Could not parse CSV: {exc}")

active = get_active_dataset(model_key)
data_source_banner(active.label, is_demo=active.is_demo, is_uploaded=active.is_uploaded)

if active.is_uploaded and st.button("Clear uploaded session data"):
    clear_uploaded_dataset()
    st.rerun()

scored = active.scored
filtered = scored[scored["risk_score"] >= min_risk]
flagged = int(scored["predicted_fraud"].sum())
exposure = scored.loc[scored["predicted_fraud"] == 1, "amount"].sum()

kpi_cols = st.columns(4)
with kpi_cols[0]:
    kpi_card("Rows scored", f"{len(scored):,}", icon="🗂️")
with kpi_cols[1]:
    kpi_card("Flagged fraud", f"{flagged:,}", tone="bad", icon="🚩")
with kpi_cols[2]:
    kpi_card("Exposure", human_money(exposure), tone="warn", icon="💵")
with kpi_cols[3]:
    kpi_card("Above report threshold", f"{len(filtered):,}", tone="neutral", icon="📊")

st.write("")
with surface():
    section_header("Scored transactions", "Download or review the classified transaction file")
    preview = scored.head(300)[
        ["step", "type", "amount", "errorBalanceOrig", "errorBalanceDest", "risk_score", "risk_level", "predicted_fraud"]
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
            "predicted_fraud": st.column_config.CheckboxColumn("Flagged"),
        },
    )

download_cols = st.columns(2)
with download_cols[0]:
    if st.button("Chuẩn bị scored CSV"):
        st.session_state["scored_csv_bytes"] = scored_to_csv_bytes(scored)
    if "scored_csv_bytes" in st.session_state:
        st.download_button(
            "Tải scored CSV",
            data=st.session_state["scored_csv_bytes"],
            file_name="scored_transactions_23051894.csv",
            mime="text/csv",
        )
with download_cols[1]:
    if st.button("Tạo audit PDF"):
        report_scope = scored[scored["risk_score"] >= min_risk]
        report_rows = report_scope.sort_values("risk_score", ascending=False).head(15)
        pdf_bytes = build_audit_report(
            report_scope,
            report_rows,
            load_model_metrics(model_key=model_key),
            load_confusion_matrix(model_key=model_key),
            analyst=REPORT_ANALYST,
            model_label=selected_model_label(model_key),
        )
        st.download_button(
            "Tải audit PDF",
            data=pdf_bytes,
            file_name="audit_report_23051894.pdf",
            mime="application/pdf",
        )
