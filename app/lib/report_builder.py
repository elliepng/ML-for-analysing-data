from __future__ import annotations

from datetime import datetime
from io import BytesIO
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "matplotlib-cache"))

import matplotlib
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .charts import confusion_matrix_figure
from .constants import RISK_HIGH, REPORT_ANALYST


FOOTER_TEXT = "FAA4023 - Data Analysis in Accounting"
FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"


def register_unicode_fonts() -> tuple[str, str]:
    font_dir = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    regular = font_dir / "DejaVuSans.ttf"
    bold = font_dir / "DejaVuSans-Bold.ttf"
    try:
        pdfmetrics.registerFont(TTFont("DejaVu", str(regular)))
        pdfmetrics.registerFont(TTFont("DejaVu-Bold", str(bold)))
        return "DejaVu", "DejaVu-Bold"
    except Exception:
        return FONT_REGULAR, FONT_BOLD


FONT_REGULAR, FONT_BOLD = register_unicode_fonts()


def summarize_scored(scored: pd.DataFrame) -> dict[str, float | int]:
    total = len(scored)
    flagged = int(scored["predicted_fraud"].sum()) if "predicted_fraud" in scored else 0
    flagged_rate = flagged / total if total else 0.0
    exposure = float(scored.loc[scored.get("predicted_fraud", 0) == 1, "amount"].sum()) if total else 0.0
    return {
        "total": total,
        "flagged": flagged,
        "flagged_rate": flagged_rate,
        "exposure": exposure,
    }


def money(value: float) -> str:
    return f"${value:,.2f}"


def number(value: float) -> str:
    return f"{value:.3f}"


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(FONT_REGULAR, 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(0.55 * inch, 0.45 * inch, FOOTER_TEXT)
    canvas.drawRightString(A4[0] - 0.55 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def _table(data: list[list[object]], header: bool = True, row_colors: list[str] | None = None) -> Table:
    table = Table(data, repeatRows=1 if header else 0)
    style = TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), FONT_REGULAR),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )
    if row_colors:
        for row_index, color in enumerate(row_colors, start=1):
            style.add("BACKGROUND", (0, row_index), (-1, row_index), colors.HexColor(color))
    table.setStyle(style)
    return table


def _confusion_image(confusion: np.ndarray) -> Image | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import io

        fig, ax = plt.subplots(figsize=(4.5, 2.8), dpi=200)
        im = ax.imshow(confusion, cmap="Blues", interpolation="nearest")
        
        # Add values inside cells
        for i in range(2):
            for j in range(2):
                color = "white" if confusion[i, j] > confusion.max() / 2 else "black"
                ax.text(j, i, f"{confusion[i, j]:,}", ha="center", va="center", color=color, fontweight="bold", fontsize=9)
                
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Pred normal", "Pred fraud"], fontsize=8)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Actual normal", "Actual fraud"], fontsize=8)
        ax.set_title("Confusion matrix", fontsize=10, fontweight="bold", pad=8)
        
        fig.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        
        return Image(buf, width=4.5 * inch, height=2.8 * inch)
    except Exception as exc:
        print(f"Failed to generate confusion matrix image using Matplotlib: {exc}")
        return None


def _curves_image() -> Image | None:
    try:
        from .model_report import load_roc_curve, load_pr_curve
        roc_points = load_roc_curve()
        pr_points = load_pr_curve()
        if not roc_points and not pr_points:
            return None
            
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import io

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(6.5, 2.5), dpi=200)
        
        if roc_points:
            fpr, tpr = roc_points
            ax1.plot(fpr, tpr, color="#5468f0", lw=2)
            ax1.plot([0, 1], [0, 1], color="#cbd5e1", linestyle="--")
            ax1.set_xlabel("False positive rate", fontsize=7)
            ax1.set_ylabel("True positive rate", fontsize=7)
            ax1.set_title("ROC Curve", fontsize=9, fontweight="bold")
            ax1.tick_params(axis="both", which="major", labelsize=7)
            ax1.grid(True, linestyle=":", alpha=0.6)
            
        if pr_points:
            recall, precision = pr_points
            ax2.plot(recall, precision, color="#5468f0", lw=2)
            ax2.set_xlabel("Recall", fontsize=7)
            ax2.set_ylabel("Precision", fontsize=7)
            ax2.set_title("Precision-Recall Curve", fontsize=9, fontweight="bold")
            ax2.tick_params(axis="both", which="major", labelsize=7)
            ax2.grid(True, linestyle=":", alpha=0.6)
            
        fig.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        
        return Image(buf, width=6.5 * inch, height=2.5 * inch)
    except Exception as exc:
        print(f"Failed to generate curves image using Matplotlib: {exc}")
        return None


def build_audit_report(
    scope: pd.DataFrame,
    table_rows: pd.DataFrame,
    metrics: pd.DataFrame,
    confusion: np.ndarray,
    *,
    analyst: str = REPORT_ANALYST,
    model_label: str = "XGBoost supervised",
    generated_at: datetime | None = None,
) -> bytes:
    generated_at = generated_at or datetime.now()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )
    styles = getSampleStyleSheet()
    for style_name in ("Title", "Heading1", "Heading2", "BodyText"):
        styles[style_name].fontName = FONT_REGULAR
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName=FONT_BOLD,
            fontSize=22,
            leading=26,
            spaceAfter=16,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontName=FONT_BOLD,
            fontSize=13,
            leading=16,
            spaceBefore=10,
        )
    )
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=9, leading=12))

    summary = summarize_scored(scope)
    elements: list[object] = []

    elements.append(Paragraph("AUDIT FRAUD DETECTION REPORT", styles["ReportTitle"]))
    elements.append(Paragraph(f"Analyst: {analyst}", styles["BodyText"]))
    elements.append(Paragraph(f"Generated at: {generated_at:%Y-%m-%d %H:%M}", styles["BodyText"]))
    elements.append(Paragraph(f"Model: {model_label}", styles["BodyText"]))
    elements.append(Spacer(1, 0.35 * inch))

    elements.append(Paragraph("Executive summary", styles["SectionTitle"]))
    kpi_data = [
        ["Metric", "Value"],
        ["Total transactions", f"{summary['total']:,}"],
        ["Flagged transactions", f"{summary['flagged']:,}"],
        ["Flagged rate", f"{summary['flagged_rate'] * 100:.3f}%"],
        ["Estimated exposure", money(float(summary["exposure"]))],
        ["Risk threshold", number(RISK_HIGH)],
    ]
    elements.append(_table(kpi_data))

    elements.append(Paragraph("Model performance", styles["SectionTitle"]))
    metric_columns = [col for col in ["model", "precision", "recall", "f1", "auc_pr", "roc_auc"] if col in metrics.columns]
    metric_data = [metric_columns]
    for _, row in metrics[metric_columns].iterrows():
        metric_data.append(
            [
                str(row[col]) if col == "model" or pd.isna(row[col]) else f"{float(row[col]):.3f}"
                for col in metric_columns
            ]
        )
    elements.append(_table(metric_data))
    elements.append(Spacer(1, 0.15 * inch))

    image = _confusion_image(confusion)
    if image is not None:
        elements.append(image)
    else:
        confusion_data = [
            ["", "Pred normal", "Pred fraud"],
            ["Actual normal", confusion[0, 0], confusion[0, 1]],
            ["Actual fraud", confusion[1, 0], confusion[1, 1]],
        ]
        elements.append(_table(confusion_data))

    elements.append(PageBreak())
    elements.append(Paragraph("Top 15 high-risk transactions", styles["SectionTitle"]))
    top = table_rows.sort_values("risk_score", ascending=False).head(15)
    top_data = [["Step", "Type", "Amount", "Err Orig", "Err Dest", "Risk", "Level"]]
    row_colors = []
    for _, row in top.iterrows():
        top_data.append(
            [
                int(row.get("step", 0)),
                str(row.get("type", "")),
                money(float(row.get("amount", 0))),
                money(float(row.get("errorBalanceOrig", 0))),
                money(float(row.get("errorBalanceDest", 0))),
                number(float(row.get("risk_score", 0))),
                str(row.get("risk_level", "")),
            ]
        )
        row_colors.append("#fee2e2" if row.get("risk_level") == "High" else "#ffffff")
    elements.append(_table(top_data, row_colors=row_colors))
    elements.append(Spacer(1, 0.15 * inch))

    curves_img = _curves_image()
    if curves_img is not None:
        elements.append(curves_img)

    elements.append(Paragraph("Method notes", styles["SectionTitle"]))
    elements.append(
        Paragraph(
            "PaySim transactions are scored with accounting-oriented balance features including origin and destination balance errors, zeroed origin balance, merchant destination flag, and transaction type indicators. Precision, recall, F1, AUC-PR, and confusion matrix are used because fraud is a rare class and accuracy can be misleading.",
            styles["BodySmall"],
        )
    )

    doc.build(elements, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
