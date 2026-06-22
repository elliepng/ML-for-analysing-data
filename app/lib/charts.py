from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .constants import RISK_HIGH
from .styling import TOKENS


PLOTLY_TEMPLATE = "plotly_white"


def apply_chart_layout(fig: go.Figure, height: int = 360, for_print: bool = False) -> go.Figure:
    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=height,
        paper_bgcolor="white" if for_print else "rgba(0,0,0,0)",
        plot_bgcolor="white" if for_print else "rgba(0,0,0,0)",
        font={"color": TOKENS["text"], "family": TOKENS["font_body"], "size": 12},
        margin={"l": 16, "r": 16, "t": 44 if for_print else 14, "b": 26},
        legend={"orientation": "h", "y": -0.2, "x": 0},
        colorway=[TOKENS["primary"], TOKENS["periwinkle"], TOKENS["risk_low"], TOKENS["risk_medium"], TOKENS["risk_high"]],
        hoverlabel={"font_family": TOKENS["font_body"]},
        title={"text": ""},
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    fig.update_yaxes(
        gridcolor="#eef0f8",
        zeroline=False,
    )
    return fig


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text="Không có giao dịch phù hợp bộ lọc",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"color": TOKENS["muted"], "size": 14},
    )
    fig.update_layout(xaxis={"visible": False}, yaxis={"visible": False})
    return apply_chart_layout(fig)


def risk_distribution(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return empty_figure("Risk score distribution")
    fig = px.histogram(
        df,
        x="risk_score",
        nbins=30,
        color="risk_level",
        color_discrete_map={"High": TOKENS["risk_high"], "Medium": TOKENS["risk_medium"], "Low": TOKENS["risk_low"]},
    )
    fig.update_traces(hovertemplate="Risk %{x:.3f}<br>Transactions %{y}<extra></extra>")
    return apply_chart_layout(fig)


def fraud_by_type(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return empty_figure("Flagged transactions by type")
    grouped = (
        df.groupby("type", as_index=False)
        .agg(transactions=("amount", "size"), predicted_fraud=("predicted_fraud", "sum"))
        .sort_values("transactions", ascending=False)
    )
    fig = go.Figure()
    fig.add_bar(x=grouped["type"], y=grouped["transactions"], name="Transactions", marker_color=TOKENS["accent"])
    fig.add_bar(x=grouped["type"], y=grouped["predicted_fraud"], name="Flagged", marker_color=TOKENS["risk_high"])
    fig.update_layout(barmode="group")
    fig.update_traces(hovertemplate="%{x}<br>Count %{y:,}<extra></extra>")
    return apply_chart_layout(fig)


def amount_vs_risk(df: pd.DataFrame) -> go.Figure:
    if df.empty:
        return empty_figure("Amount vs risk")
    fig = px.scatter(
        df,
        x="amount",
        y="risk_score",
        color="risk_level",
        size="amount",
        hover_data=["type", "oldbalanceOrg", "newbalanceOrig"],
        color_discrete_map={"High": TOKENS["risk_high"], "Medium": TOKENS["risk_medium"], "Low": TOKENS["risk_low"]},
        size_max=18,
    )
    fig.update_xaxes(type="log")
    fig.update_traces(hovertemplate="Amount $%{x:,.2f}<br>Risk %{y:.3f}<extra></extra>")
    fig.add_hline(y=RISK_HIGH, line_dash="dot", line_color=TOKENS["muted"])
    return apply_chart_layout(fig)


def exposure_trend(df: pd.DataFrame, bins: int = 30) -> go.Figure:
    if df.empty:
        return empty_figure("Exposure trend")
    bucket_count = min(bins, max(1, int(df["step"].nunique())))
    working = df.assign(flagged_amount=df["amount"].where(df["predicted_fraud"] == 1, 0)).copy()
    working["bucket"] = pd.cut(working["step"], bins=bucket_count)
    trend = working.groupby("bucket", observed=True, as_index=False).agg(exposure=("flagged_amount", "sum"))
    trend["x"] = range(len(trend))
    trend["cumulative_exposure"] = trend["exposure"].cumsum()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=trend["x"],
            y=trend["cumulative_exposure"],
            name="Flagged exposure",
            mode="lines",
            line_shape="spline",
            line={"color": TOKENS["navy"], "width": 3},
            fill="tozeroy",
            fillcolor="rgba(84, 104, 240, 0.12)",
            hovertemplate="Bucket %{x}<br>Cumulative exposure $%{y:,.2f}<extra></extra>",
        )
    )
    if not trend.empty:
        peak = trend.iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=[peak["x"]],
                y=[peak["cumulative_exposure"]],
                mode="markers",
                marker={"size": 10, "color": TOKENS["primary"], "line": {"color": "#ffffff", "width": 2}},
                showlegend=False,
                hovertemplate="Latest bucket %{x}<br>Cumulative exposure $%{y:,.2f}<extra></extra>",
            )
        )
    fig.update_layout(showlegend=False)
    return apply_chart_layout(fig, height=300)


def type_mix_donut(df: pd.DataFrame) -> go.Figure:
    """Power BI-style donut of transaction type composition."""
    if df.empty:
        return empty_figure("Type mix")
    counts = df["type"].value_counts()
    palette = [TOKENS["primary"], TOKENS["periwinkle"], TOKENS["risk_low"], TOKENS["risk_medium"], TOKENS["risk_high"]]
    fig = go.Figure(
        go.Pie(
            labels=counts.index.tolist(),
            values=counts.values.tolist(),
            hole=0.62,
            sort=False,
            marker={"colors": palette, "line": {"color": "#ffffff", "width": 2}},
            textinfo="none",
            hovertemplate="%{label}<br>%{value:,} (%{percent})<extra></extra>",
        )
    )
    fig = apply_chart_layout(fig, height=232)
    fig.update_layout(
        legend={"orientation": "v", "x": 1.0, "y": 0.5, "xanchor": "left", "font": {"size": 11}},
        margin={"l": 6, "r": 6, "t": 8, "b": 8},
    )
    return fig


def recall_gauge(value: float, target: float = 95.0) -> go.Figure:
    """Power BI-style half gauge with a target threshold tick."""
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%", "font": {"size": 36, "color": TOKENS["text"]}},
            gauge={
                "axis": {"range": [0, 100], "visible": False},
                "bar": {"color": TOKENS["primary"], "thickness": 0.3},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [{"range": [0, 100], "color": TOKENS["surface_alt"]}],
                "threshold": {"line": {"color": TOKENS["risk_high"], "width": 3}, "thickness": 0.85, "value": target},
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(
        height=210,
        margin={"l": 22, "r": 22, "t": 6, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": TOKENS["text"], "family": TOKENS["font_body"]},
    )
    return fig


def fraud_type_stacked(df: pd.DataFrame) -> go.Figure:
    """Horizontal stacked bars: flagged vs remaining volume per transaction type."""
    if df.empty:
        return empty_figure("Fraud by type")
    grouped = (
        df.groupby("type", as_index=False)
        .agg(total=("amount", "size"), flagged=("predicted_fraud", "sum"))
        .sort_values("total", ascending=True)
    )
    grouped["normal"] = grouped["total"] - grouped["flagged"]
    fig = go.Figure()
    fig.add_bar(y=grouped["type"], x=grouped["flagged"], name="Flagged", orientation="h", marker_color=TOKENS["risk_high"])
    fig.add_bar(y=grouped["type"], x=grouped["normal"], name="Normal", orientation="h", marker_color="#dfe3f5")
    fig.update_layout(barmode="stack")
    fig.update_traces(hovertemplate="%{y}<br>%{x:,}<extra></extra>")
    return apply_chart_layout(fig, height=240)


def confusion_matrix_figure(matrix: np.ndarray, for_print: bool = False) -> go.Figure:
    fig = px.imshow(
        matrix,
        text_auto=True,
        x=["Predicted normal", "Predicted fraud"],
        y=["Actual normal", "Actual fraud"],
        color_continuous_scale=[TOKENS["primary_soft"], TOKENS["periwinkle"], TOKENS["primary"]],
        title="Confusion matrix" if for_print else None,
    )
    fig.update_traces(textfont={"size": 15})
    fig.update_coloraxes(showscale=False)
    return apply_chart_layout(fig, height=340, for_print=for_print)


def curve_figure(title: str, x: list[float], y: list[float], x_title: str, y_title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", line={"color": TOKENS["accent"], "width": 3}))
    fig.update_layout(xaxis_title=x_title, yaxis_title=y_title)
    return apply_chart_layout(fig, height=340)
