from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from html import escape

import streamlit as st

from .styling import TOKENS


TONE_COLORS = {
    "neutral": TOKENS["accent"],
    "good": TOKENS["risk_low"],
    "warn": TOKENS["risk_medium"],
    "bad": TOKENS["risk_high"],
}


def _safe(value: object) -> str:
    return escape(str(value))


def human_money(value: float) -> str:
    """Compact currency so large KPI values fit on one line (e.g. $216.7M)."""
    amount = float(value)
    magnitude = abs(amount)
    if magnitude >= 1e9:
        return f"${amount / 1e9:.2f}B"
    if magnitude >= 1e6:
        return f"${amount / 1e6:.2f}M"
    if magnitude >= 1e3:
        return f"${amount / 1e3:.1f}K"
    return f"${amount:,.0f}"


def kpi_card(label: str, value: str, delta: str | None = None, tone: str = "neutral", icon: str = "▦") -> None:
    delta_color = {
        "good": TOKENS["risk_low"],
        "warn": TOKENS["risk_medium"],
        "bad": TOKENS["risk_high"],
    }.get(tone, TOKENS["muted"])
    delta_html = (
        f"<div class='kpi-delta' style='color:{delta_color}'>{delta}</div>"
        if delta
        else "<div class='kpi-delta' style='visibility:hidden'>&nbsp;</div>"
    )
    st.markdown(
        f"""
        <div class="kpi-card {tone}">
            <div class="kpi-chip">{icon}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_strip(items: list[tuple[str, str, str | None]]) -> None:
    blocks = []
    for label, value, note in items:
        note_html = f"<div class='metric-mini-note'>{_safe(note)}</div>" if note else ""
        blocks.append(
            f"""
            <div class="metric-mini">
                <div class="metric-mini-label">{_safe(label)}</div>
                <div class="metric-mini-value">{_safe(value)}</div>
                {note_html}
            </div>
            """
        )
    st.markdown(f"<div class='metric-strip'>{''.join(blocks)}</div>", unsafe_allow_html=True)


def callout_card(title: str, text: str, tone: str = "info") -> None:
    mapping = {
        "info": ("i", TOKENS["primary_soft"], TOKENS["primary"]),
        "success": ("✓", TOKENS["risk_low_bg"], TOKENS["risk_low"]),
        "warning": ("!", TOKENS["risk_medium_bg"], TOKENS["risk_medium"]),
        "danger": ("!", TOKENS["risk_high_bg"], TOKENS["risk_high"]),
    }
    icon, bg, fg = mapping.get(tone, mapping["info"])
    st.markdown(
        f"""
        <div class="callout-card">
            <div class="callout-icon" style="background:{bg};color:{fg};">{icon}</div>
            <div>
                <div class="callout-title">{_safe(title)}</div>
                <p class="callout-text">{_safe(text)}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def checklist_card(title: str, items: list[str], subtitle: str | None = None) -> None:
    subtitle_html = f"<p class='section-subtitle'>{_safe(subtitle)}</p>" if subtitle else ""
    items_html = "".join(f"<li>{_safe(item)}</li>" for item in items)
    st.markdown(
        f"""
        <div class="checklist-card">
            <h3 class="section-title">{_safe(title)}</h3>
            {subtitle_html}
            <ul>{items_html}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _sparkline_svg(values: list[float], color: str, width: int = 84, height: int = 28) -> str:
    cleaned = [float(v) for v in values if v is not None]
    if len(cleaned) < 2:
        return ""
    low, high = min(cleaned), max(cleaned)
    span = (high - low) or 1.0
    count = len(cleaned)
    points = []
    for index, value in enumerate(cleaned):
        x = index / (count - 1) * width
        y = height - 2 - ((value - low) / span) * (height - 4)
        points.append(f"{x:.1f},{y:.1f}")
    pts = " ".join(points)
    return (
        f"<svg class='pbi-spark' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>"
        f"<polyline points='{pts}' fill='none' stroke='{color}' stroke-width='2' "
        f"stroke-linecap='round' stroke-linejoin='round'/></svg>"
    )


def pbi_header(title: str, subtitle: str, chips: list[tuple[str, str]]) -> None:
    """Power BI-style report header band with read-only context chips."""
    chip_html = "".join(
        f"<div class='pbi-chip'><span class='pbi-chip-k'>{_safe(key)}</span>"
        f"<span class='pbi-chip-v'>{_safe(val)}</span></div>"
        for key, val in chips
    )
    st.markdown(
        f"""
        <div class="pbi-header">
            <div class="pbi-header-l">
                <div class="pbi-monogram">FA</div>
                <div>
                    <div class="pbi-header-title">{_safe(title)}</div>
                    <div class="pbi-header-sub">{_safe(subtitle)}</div>
                </div>
            </div>
            <div class="pbi-slicers">{chip_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def pbi_kpi(label: str, value: str, delta: str | None = None, tone: str = "neutral", spark: list[float] | None = None) -> None:
    """Power BI-style KPI card: label, big value, delta and a sparkline. No icons."""
    delta_color = {
        "good": TOKENS["risk_low"],
        "warn": TOKENS["risk_medium"],
        "bad": TOKENS["risk_high"],
    }.get(tone, TOKENS["muted"])
    spark_color = {
        "good": TOKENS["risk_low"],
        "warn": TOKENS["risk_medium"],
        "bad": TOKENS["risk_high"],
    }.get(tone, TOKENS["primary"])
    delta_html = f"<div class='pbi-kpi-delta' style='color:{delta_color}'>{_safe(delta)}</div>" if delta else "<div class='pbi-kpi-delta'>&nbsp;</div>"
    spark_html = _sparkline_svg(spark, spark_color) if spark else ""
    st.markdown(
        f"""
        <div class="pbi-kpi {tone}">
            <div class="pbi-kpi-lab">{_safe(label)}</div>
            <div class="pbi-kpi-val">{_safe(value)}</div>
            <div class="pbi-kpi-foot">{delta_html}{spark_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def empty_state(icon: str, title: str, hint: str) -> None:
    """Consistent placeholder for sections whose data is empty/filtered out."""
    icon_html = f"<div class='empty-state-icon'>{icon}</div>" if icon else ""
    st.markdown(
        f"<div class='empty-state'>{icon_html}<div class='empty-state-title'>{_safe(title)}</div>"
        f"<p class='empty-state-hint'>{_safe(hint)}</p></div>",
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f"<p class='section-subtitle'>{subtitle}</p>" if subtitle else ""
    st.markdown(
        f"""
        <div>
            <h3 class="section-title">{title}</h3>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def risk_badge(level: str) -> str:
    mapping = {
        "High": (TOKENS["risk_high"], TOKENS["risk_high_bg"]),
        "Medium": (TOKENS["risk_medium"], TOKENS["risk_medium_bg"]),
        "Low": (TOKENS["risk_low"], TOKENS["risk_low_bg"]),
    }
    foreground, background = mapping.get(level, (TOKENS["muted"], TOKENS["surface_alt"]))
    return f"<span class='risk-pill' style='background:{background};color:{foreground}'>{level}</span>"


@contextmanager
def surface() -> Iterator[None]:
    with st.container(border=True):
        yield


def sidebar_brand() -> None:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">FA</div>
            <div>
                <div class="sidebar-brand-title">Fraud Audit</div>
                <div class="sidebar-brand-subtitle">FAA4023 · 23051894</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_cta(title: str, button_label: str | None = None, icon: str = "") -> None:
    icon_html = f"<div class='cta-icon'>{icon}</div>" if icon else ""
    tag_html = f"<div class='cta-tag'>{_safe(button_label)} →</div>" if button_label else ""
    st.markdown(
        f"<div class='cta-card'>{icon_html}<div class='cta-title'>{_safe(title)}</div>{tag_html}</div>",
        unsafe_allow_html=True,
    )


def data_source_banner(label: str, *, is_demo: bool, is_uploaded: bool) -> None:
    if is_demo:
        st.info("Đang dùng dữ liệu DEMO. Upload CSV hoặc train PaySim để có kết quả thật.")
    elif is_uploaded:
        st.success(f"Đang dùng dữ liệu upload: {label}")
    else:
        st.success(f"Đang dùng dữ liệu artifacts đã train: {label}")


def feature_card(title: str, desc: str, badges: list[tuple[str, str]]) -> None:
    items = "".join(
        f"<div style='display:flex;justify-content:space-between;margin:0.35rem 0;'>"
        f"<span style='opacity:.85'>{label}</span><b>{value}</b></div>"
        for label, value in badges
    )
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:1.1fr 0.9fr;gap:1.1rem;align-items:center;">
          <div>
            <h3 style="margin:0 0 .5rem">{title}</h3>
            <p style="color:{TOKENS['muted']};margin:0">{desc}</p>
          </div>
          <div class="promo-grad" style="background:linear-gradient(150deg,{TOKENS['grad_from']},{TOKENS['grad_to']});
               color:#fff;border-radius:{TOKENS['radius']};padding:1.1rem 1.2rem;box-shadow:{TOKENS['shadow']};
               min-height:150px;display:flex;flex-direction:column;justify-content:center;">
            <div style="font-size:.72rem;font-weight:800;letter-spacing:.12em;opacity:.78;margin-bottom:.55rem;">FRAUD MODEL</div>
            {items}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def ring_card(title: str, subtitle: str, percent: float) -> None:
    pct = max(0, min(100, percent))
    st.markdown(
        f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
             background:{TOKENS['navy']};color:#fff;border-radius:{TOKENS['radius']};
             padding:1.3rem 1.4rem;box-shadow:{TOKENS['shadow']};">
          <div><div style="opacity:.75;font-size:.85rem">{title}</div>
               <div style="font-family:{TOKENS['font_heading']};font-size:1.4rem;font-weight:800">{subtitle}</div></div>
          <div style="width:84px;height:84px;border-radius:999px;display:grid;place-items:center;
               background:conic-gradient({TOKENS['periwinkle']} {pct * 3.6:.0f}deg, rgba(255,255,255,.16) 0);">
            <div style="width:64px;height:64px;border-radius:999px;background:{TOKENS['navy']};
                 display:grid;place-items:center;font-weight:800;font-size:0.95rem">{pct:.1f}%</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mini_stat(label: str, value: str, tone: str = "neutral") -> None:
    color = {
        "good": TOKENS["risk_low"],
        "warn": TOKENS["risk_medium"],
        "bad": TOKENS["risk_high"],
    }.get(tone, TOKENS["primary"])
    st.markdown(
        f"""
        <div style="background:{TOKENS['surface']};border-radius:{TOKENS['radius_sm']};
             box-shadow:{TOKENS['shadow_sm']};padding:.75rem .9rem;margin-top:.7rem;
             display:flex;justify-content:space-between;align-items:center;">
          <span style="color:{TOKENS['muted']};font-size:.82rem;font-weight:600">{label}</span>
          <b style="color:{color};font-size:.96rem">{value}</b>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_panel(items: list[tuple[str, str, str]]) -> None:
    """One cohesive card holding several label/value rows (replaces stacked mini_stats)."""
    tone_color = {"good": TOKENS["risk_low"], "warn": TOKENS["risk_medium"], "bad": TOKENS["risk_high"]}
    rows = ""
    for index, (label, value, tone) in enumerate(items):
        color = tone_color.get(tone, TOKENS["primary"])
        divider = f"border-top:1px solid {TOKENS['border']};" if index else ""
        rows += (
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding:0.62rem 0;{divider}'>"
            f"<span style='color:{TOKENS['muted']};font-size:0.82rem;font-weight:600'>{label}</span>"
            f"<b style='color:{color};font-size:0.96rem'>{value}</b></div>"
        )
    st.markdown(
        f"<div style='background:{TOKENS['surface']};border-radius:{TOKENS['radius_sm']};"
        f"box-shadow:{TOKENS['shadow_sm']};padding:0.2rem 0.95rem;margin-top:0.75rem'>{rows}</div>",
        unsafe_allow_html=True,
    )


def note_card(title: str, text: str) -> None:
    """Muted info card for empty states (e.g. metrics before training)."""
    st.markdown(
        f"""
        <div style="background:{TOKENS['surface']};border-radius:{TOKENS['radius']};
             box-shadow:{TOKENS['shadow']};padding:1.25rem 1.3rem;height:100%;
             display:flex;flex-direction:column;justify-content:center;">
          <div style="font-family:{TOKENS['font_heading']};font-weight:800;color:{TOKENS['text']}">{title}</div>
          <p style="color:{TOKENS['muted']};margin:0.45rem 0 0;font-size:0.88rem;line-height:1.45">{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def model_compare(rows: list[tuple[str, float, float]]) -> None:
    """Compact model comparison bars. rows = list of (name, recall%, auc_pr%)."""
    bars = ""
    for name, recall, auc in rows:
        bars += (
            f"<div style='margin:0.55rem 0'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;'>"
            f"<span style='color:{TOKENS['text']};font-weight:600'>{name}</span>"
            f"<span style='color:{TOKENS['muted']}'>R {recall:.1f}% · AUC-PR {auc:.1f}%</span></div>"
            f"<div style='height:6px;border-radius:999px;background:{TOKENS['surface_alt']};margin-top:0.3rem'>"
            f"<div style='width:{max(0, min(100, auc)):.1f}%;height:6px;border-radius:999px;"
            f"background:linear-gradient(90deg,{TOKENS['primary']},{TOKENS['periwinkle']})'></div></div></div>"
        )
    st.markdown(
        f"<div style='margin-top:1rem;border-top:1px solid {TOKENS['border']};padding-top:0.8rem'>"
        f"<div style='font-size:0.74rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;"
        f"color:{TOKENS['muted']};margin-bottom:0.3rem'>Model comparison · AUC-PR</div>{bars}</div>",
        unsafe_allow_html=True,
    )


def risk_mix(high: int, medium: int, low: int) -> None:
    """Slim stacked bar + counts showing the High/Medium/Low risk distribution."""
    total = max(high + medium + low, 1)
    seg_high = high / total * 100
    seg_medium = medium / total * 100
    seg_low = low / total * 100
    st.markdown(
        f"""
        <div style="margin:0.2rem 0 0.9rem;">
          <div class="risk-mix-bar" style="display:flex;height:9px;border-radius:999px;overflow:hidden;background:{TOKENS['surface_alt']};">
            <div style="width:{seg_high:.2f}%;background:{TOKENS['risk_high']}"></div>
            <div style="width:{seg_medium:.2f}%;background:{TOKENS['risk_medium']}"></div>
            <div style="width:{seg_low:.2f}%;background:{TOKENS['risk_low']}"></div>
          </div>
          <div style="display:flex;gap:1.1rem;margin-top:0.5rem;font-size:0.78rem;color:{TOKENS['muted']};">
            <span><b style="color:{TOKENS['risk_high']}">●</b> High {high:,}</span>
            <span><b style="color:{TOKENS['risk_medium']}">●</b> Medium {medium:,}</span>
            <span><b style="color:{TOKENS['risk_low']}">●</b> Low {low:,}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def txn_row(icon: str, name: str, time: str, amount: str, tone: str = "bad") -> None:
    background = {"bad": TOKENS["risk_high_bg"], "good": TOKENS["risk_low_bg"]}.get(tone, TOKENS["surface_alt"])
    foreground = {"bad": TOKENS["risk_high"], "good": TOKENS["risk_low"]}.get(tone, TOKENS["text"])
    st.markdown(
        f"""
        <div class="txn-row" style="display:flex;align-items:center;gap:0.8rem;padding:0.55rem 0;">
          <div class="kpi-chip" style="width:2.1rem;height:2.1rem">{icon}</div>
          <div style="flex:1"><div style="font-weight:700;color:{TOKENS['text']}">{name}</div>
               <div style="color:{TOKENS['muted']};font-size:.8rem">{time}</div></div>
          <span class="risk-pill" style="background:{background};color:{foreground}">{amount}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
