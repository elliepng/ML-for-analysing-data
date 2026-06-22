from __future__ import annotations

import streamlit as st


# Direction: light fintech (Peymen-inspired) — lavender canvas, white rounded cards,
# soft shadows, indigo/periwinkle accent. Colour reserved for risk semantics.
TOKENS = {
    "bg": "#e9eaf0",
    "content": "#f1f3ff",
    "surface": "#ffffff",
    "surface_alt": "#f6f7fe",
    "border": "#eceef6",
    "text": "#16204e",
    "muted": "#8b91ad",
    "primary": "#5468f0",
    "primary_soft": "#eef0fe",
    "periwinkle": "#9196f2",
    "navy": "#0a2375",
    "grad_from": "#9196f2",
    "grad_to": "#7d87e9",
    "risk_high": "#ef5b5b",
    "risk_high_bg": "#fdeaea",
    "risk_medium": "#f5a623",
    "risk_medium_bg": "#fdf1dd",
    "risk_low": "#2bbf78",
    "risk_low_bg": "#e3f7ed",
    "accent": "#5468f0",
    "danger": "#ef5b5b",
    "warning": "#f5a623",
    "success": "#2bbf78",
    "radius": "18px",
    "radius_sm": "12px",
    "shadow": "0 14px 34px rgba(31, 41, 120, 0.08)",
    "shadow_sm": "0 6px 18px rgba(31, 41, 120, 0.06)",
    "space_1": "0.25rem",
    "space_2": "0.5rem",
    "space_3": "0.75rem",
    "space_4": "1rem",
    "space_6": "1.5rem",
    "space_8": "2rem",
    "font_heading": "'Sora', 'Poppins', sans-serif",
    "font_body": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    "font_mono": "'Space Grotesk', ui-monospace, monospace",
    "type_h1": "2rem",
    "type_h2": "1.35rem",
    "type_h3": "1.05rem",
    "type_body": "0.98rem",
    "type_caption": "0.84rem",
}


def configure_page(title: str) -> None:
    st.set_page_config(
        page_title=title,
        page_icon="🛡️",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def inject_global_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@600;700;800&display=swap');
        :root {{
            --bg:{TOKENS["bg"]}; --content:{TOKENS["content"]}; --surface:{TOKENS["surface"]};
            --surface-alt:{TOKENS["surface_alt"]}; --border:{TOKENS["border"]};
            --text:{TOKENS["text"]}; --muted:{TOKENS["muted"]};
            --primary:{TOKENS["primary"]}; --primary-soft:{TOKENS["primary_soft"]};
            --periwinkle:{TOKENS["periwinkle"]}; --navy:{TOKENS["navy"]};
            --risk-high:{TOKENS["risk_high"]}; --risk-medium:{TOKENS["risk_medium"]}; --risk-low:{TOKENS["risk_low"]};
            --risk-high-bg:{TOKENS["risk_high_bg"]}; --risk-medium-bg:{TOKENS["risk_medium_bg"]}; --risk-low-bg:{TOKENS["risk_low_bg"]};
            --radius:{TOKENS["radius"]}; --radius-sm:{TOKENS["radius_sm"]};
            --shadow:{TOKENS["shadow"]}; --shadow-sm:{TOKENS["shadow_sm"]};
            --font-heading:{TOKENS["font_heading"]}; --font-body:{TOKENS["font_body"]};
        }}
        .stApp {{ background: var(--content); color: var(--text); font-family: var(--font-body); }}
        .block-container {{ padding-top:1.3rem; padding-bottom:2.5rem; max-width:1380px; }}
        @media (prefers-reduced-motion: reduce) {{ * {{ transition:none !important; }} }}

        h1,h2,h3 {{ font-family:var(--font-heading); color:var(--text); letter-spacing:-0.01em; }}
        h1 {{ font-size:{TOKENS["type_h1"]}; }} h2 {{ font-size:{TOKENS["type_h2"]}; }} h3 {{ font-size:{TOKENS["type_h3"]}; }}

        [data-testid="stSidebar"] {{ background:var(--surface); border-right:1px solid var(--border); }}
        [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{ padding-top:0.4rem; }}
        [data-testid="stSidebarNav"] {{ padding-top:0.4rem; }}
        [data-testid="stSidebarNav"] ul {{ gap:0.1rem; }}
        [data-testid="stSidebarNavLink"] {{ border-radius:10px; padding:0.3rem 0.7rem !important;
            margin:0.05rem 0; transition:background 140ms ease; }}
        [data-testid="stSidebarNavLink"] span {{ color:var(--muted); font-weight:500; }}
        [data-testid="stSidebarNavLink"]:hover {{ background:var(--primary-soft); }}
        [data-testid="stSidebarNavLink"]:hover span {{ color:var(--text); }}
        [data-testid="stSidebarNavLink"][aria-current] {{ background:var(--primary-soft);
            box-shadow:inset 3px 0 0 var(--primary); }}
        [data-testid="stSidebarNavLink"][aria-current] span {{ color:var(--primary); font-weight:700; }}
        [data-testid="stSidebar"] label {{ color:var(--muted); font-weight:600; font-size:0.8rem; }}
        [data-testid="stSidebar"] [data-baseweb="select"] > div {{ border-radius:10px; border-color:var(--border); }}
        [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {{ font-size:0.78rem; line-height:1.5; }}
        [data-testid="stSidebar"] hr {{ border-color:var(--border); margin:1rem 0; }}

        .app-hero {{ margin:0.1rem 0 1.3rem; }}
        .app-hero-eyebrow {{ color:var(--primary); font-size:0.92rem; font-weight:600; letter-spacing:0.01em; }}
        .app-hero-title {{ margin:0.15rem 0 0; font-family:var(--font-heading); font-size:2rem; font-weight:800; color:var(--text); }}
        .app-hero-sub {{ margin:0.35rem 0 0; color:var(--muted); font-size:0.95rem; }}

        .status-chip {{ display:inline-flex; align-items:center; gap:0.4rem; font-size:0.78rem; font-weight:600;
            padding:0.28rem 0.7rem; border-radius:999px; background:var(--surface); box-shadow:var(--shadow-sm); color:var(--muted); }}
        .status-chip .dot {{ width:7px; height:7px; border-radius:999px; }}
        .status-chip.live {{ color:var(--risk-low); }}
        .status-chip.demo {{ color:var(--risk-medium); }}

        [data-testid="stVerticalBlockBorderWrapper"] {{
            background:var(--surface); border:0 !important; border-radius:var(--radius);
            box-shadow:var(--shadow); padding:1.1rem 1.25rem 1.2rem;
            transition:box-shadow 180ms ease, transform 180ms ease;
            height:100%;
        }}
        [data-testid="stVerticalBlockBorderWrapper"]:hover {{
            transform:translateY(-2px); box-shadow:0 20px 44px rgba(31,41,120,0.12);
        }}
        /* Equal-height cards across a row (harmony) */
        [data-testid="stHorizontalBlock"] {{ align-items:stretch; }}
        [data-testid="stColumn"] > div, [data-testid="column"] > div {{ height:100%; }}

        .section-title {{ margin:0; font-family:var(--font-heading); font-size:1.05rem; font-weight:700; color:var(--text); }}
        .section-subtitle {{ margin:0.2rem 0 0.8rem; color:var(--muted); font-size:{TOKENS["type_caption"]}; }}
        .caption {{ color:var(--muted); font-size:{TOKENS["type_caption"]}; }}

        .metric-strip {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:0.8rem; margin:0 0 1rem; }}
        .metric-mini {{ background:var(--surface); border-radius:var(--radius-sm); box-shadow:var(--shadow-sm); padding:0.9rem 1rem; }}
        .metric-mini-label {{ color:var(--muted); font-size:0.74rem; font-weight:700; letter-spacing:0.04em; text-transform:uppercase; }}
        .metric-mini-value {{ margin-top:0.28rem; color:var(--text); font-family:var(--font-heading); font-size:1.04rem; font-weight:800; }}
        .metric-mini-note {{ margin-top:0.18rem; color:var(--muted); font-size:0.8rem; }}

        .callout-card {{ display:flex; gap:0.85rem; background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow);
            padding:1rem 1.05rem; margin:0 0 1rem; align-items:flex-start; }}
        .callout-icon {{ width:2.2rem; height:2.2rem; border-radius:999px; display:grid; place-items:center; font-size:0.96rem; font-weight:800; flex:0 0 auto; }}
        .callout-title {{ margin:0; color:var(--text); font-family:var(--font-heading); font-size:1rem; font-weight:700; }}
        .callout-text {{ margin:0.22rem 0 0; color:var(--muted); font-size:0.88rem; line-height:1.5; }}

        .checklist-card {{ background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow); padding:1.05rem 1.15rem; height:100%; }}
        .checklist-card ul {{ margin:0.5rem 0 0; padding-left:1.05rem; color:var(--muted); }}
        .checklist-card li {{ margin:0.35rem 0; line-height:1.45; }}

        .kpi-card {{ background:var(--surface); border-radius:var(--radius); box-shadow:var(--shadow);
            padding:1rem 1.1rem; min-height:112px; height:100%;
            display:flex; flex-direction:column;
            transition:transform 160ms ease, box-shadow 160ms ease; }}
        .kpi-card:hover {{ transform:translateY(-2px); box-shadow:0 20px 44px rgba(31,41,120,0.12); }}
        .kpi-chip {{ width:2.4rem; height:2.4rem; display:grid; place-items:center; border-radius:var(--radius-sm);
            background:var(--primary-soft); color:var(--primary); font-size:1.05rem; }}
        .kpi-card.good .kpi-chip {{ background:var(--risk-low-bg); color:var(--risk-low); }}
        .kpi-card.warn .kpi-chip {{ background:var(--risk-medium-bg); color:var(--risk-medium); }}
        .kpi-card.bad  .kpi-chip {{ background:var(--risk-high-bg); color:var(--risk-high); }}
        .kpi-label {{ margin-top:0.55rem; color:var(--muted); font-size:0.82rem; font-weight:500; }}
        .kpi-value {{ margin-top:0.25rem; color:var(--text); font-family:var(--font-heading);
            font-size:1.85rem; font-weight:800; line-height:1.05; white-space:nowrap; }}
        .kpi-delta {{ margin-top:0.4rem; font-size:0.82rem; font-weight:600; }}

        .risk-pill {{ display:inline-flex; align-items:center; gap:0.35rem; border-radius:999px;
            padding:0.25rem 0.7rem; font-size:0.78rem; font-weight:700; }}

        .empty-state {{ display:flex; flex-direction:column; align-items:center; justify-content:center;
            text-align:center; gap:0.55rem; padding:1.7rem 1rem; min-height:190px; }}
        .empty-state-icon {{ width:3rem; height:3rem; border-radius:var(--radius-sm); display:grid;
            place-items:center; background:var(--primary-soft); color:var(--primary); font-size:1.3rem; }}
        .empty-state-title {{ font-family:var(--font-heading); font-weight:700; color:var(--text); font-size:1rem; }}
        .empty-state-hint {{ color:var(--muted); font-size:0.85rem; max-width:36ch; line-height:1.5; margin:0; }}

        .stButton > button, [data-testid="stDownloadButton"] > button {{
            border-radius:999px; border:0; background:var(--primary); color:#fff; font-weight:700;
            padding:0.5rem 1.3rem; box-shadow:0 8px 20px rgba(84,104,240,0.28);
            transition:transform 150ms ease, filter 150ms ease; }}
        .stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {{
            transform:translateY(-1px); filter:brightness(1.06); }}

        div[data-testid="stDataFrame"] {{ border:1px solid var(--border); border-radius:var(--radius-sm); overflow:hidden; }}
        div[data-testid="stDataFrame"] thead tr th {{ position:sticky; top:0; z-index:1; background:var(--surface-alt); }}

        .sidebar-brand {{ display:flex; gap:0.7rem; align-items:center; padding:0.75rem 0.8rem; margin-bottom:1rem;
            border-radius:var(--radius-sm); background:var(--primary-soft); border:1px solid #e3e6fb; }}
        .sidebar-brand-icon {{ width:2.1rem; height:2.1rem; display:grid; place-items:center; border-radius:9px;
            background:linear-gradient(150deg, {TOKENS["grad_from"]}, {TOKENS["primary"]}); color:#fff;
            font-family:var(--font-heading); font-weight:800; font-size:0.8rem; letter-spacing:0.02em;
            box-shadow:0 6px 14px rgba(84,104,240,0.32); }}
        .sidebar-brand-title {{ font-family:var(--font-heading); color:var(--text); font-weight:800; line-height:1.1; font-size:0.98rem; }}
        .sidebar-brand-subtitle {{ color:var(--muted); font-size:0.74rem; margin-top:0.14rem; letter-spacing:0.01em; }}

        .cta-card {{ margin-top:1rem; padding:1.1rem 1.15rem; border-radius:var(--radius);
            background:linear-gradient(150deg, {TOKENS["grad_from"]}, {TOKENS["grad_to"]}); color:#fff;
            box-shadow:0 16px 32px rgba(124,135,233,0.36); }}
        .cta-icon {{ width:2.1rem; height:2.1rem; border-radius:10px; display:grid; place-items:center;
            background:rgba(255,255,255,0.22); font-size:1rem; margin-bottom:0.6rem; }}
        .cta-title {{ font-family:var(--font-heading); font-weight:700; font-size:0.96rem; line-height:1.32; }}
        .cta-tag {{ display:inline-flex; align-items:center; gap:0.3rem; margin-top:0.8rem;
            background:rgba(255,255,255,0.18); padding:0.32rem 0.75rem; border-radius:999px;
            font-size:0.76rem; font-weight:600; }}

        /* ---------------- Power BI report styling ---------------- */
        .pbi-header {{ display:flex; align-items:center; justify-content:space-between; gap:1rem;
            background:linear-gradient(100deg, var(--navy), #1c3aa0); color:#fff; border-radius:14px;
            padding:1.05rem 1.25rem; box-shadow:0 14px 30px rgba(10,35,117,0.22);
            margin-top:1.8rem; margin-bottom:0.2rem; }}
        .pbi-header-l {{ display:flex; align-items:center; gap:0.85rem; }}
        .pbi-monogram {{ width:2.4rem; height:2.4rem; border-radius:11px; display:grid; place-items:center;
            background:rgba(255,255,255,0.16); font-family:var(--font-heading); font-weight:800; font-size:0.92rem; }}
        .pbi-header-title {{ font-family:var(--font-heading); font-weight:800; font-size:1.18rem; line-height:1.1; color:#fff; }}
        .pbi-header-sub {{ font-size:0.74rem; opacity:0.76; margin-top:0.18rem; letter-spacing:0.01em; }}
        .pbi-slicers {{ display:flex; flex-wrap:wrap; gap:0.5rem; justify-content:flex-end; }}
        .pbi-chip {{ display:flex; flex-direction:column; gap:0.04rem; background:rgba(255,255,255,0.1);
            border:1px solid rgba(255,255,255,0.18); border-radius:9px; padding:0.3rem 0.7rem; min-width:72px;
            transition:background 160ms ease, transform 160ms ease; }}
        .pbi-chip:hover {{ background:rgba(255,255,255,0.18); transform:translateY(-1px); }}
        .pbi-chip-k {{ font-size:0.58rem; text-transform:uppercase; letter-spacing:0.06em; opacity:0.68; font-weight:700; }}
        .pbi-chip-v {{ font-size:0.82rem; font-weight:700; font-family:var(--font-heading); }}

        .pbi-kpi {{ background:var(--surface); border:1px solid var(--border); border-radius:13px;
            box-shadow:var(--shadow-sm); padding:0.9rem 1.05rem; height:100%; border-top:3px solid var(--primary); }}
        .pbi-kpi.bad {{ border-top-color:var(--risk-high); }}
        .pbi-kpi.warn {{ border-top-color:var(--risk-medium); }}
        .pbi-kpi.good {{ border-top-color:var(--risk-low); }}
        .pbi-kpi-lab {{ color:var(--muted); font-size:0.72rem; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; }}
        .pbi-kpi-val {{ font-family:var(--font-heading); font-weight:800; font-size:1.75rem; margin-top:0.35rem; line-height:1; white-space:nowrap; }}
        .pbi-kpi-foot {{ display:flex; align-items:flex-end; justify-content:space-between; gap:0.5rem; margin-top:0.55rem; }}
        .pbi-kpi-delta {{ font-size:0.74rem; font-weight:700; color:var(--muted); }}
        .pbi-spark {{ display:block; }}

        /* ---------------- Motion system ---------------- */
        @keyframes eccFadeIn {{ from {{ opacity:0; }} to {{ opacity:1; }} }}
        @keyframes eccFadeUp {{ from {{ opacity:0; transform:translateY(9px); }} to {{ opacity:1; transform:translateY(0); }} }}
        @keyframes eccPulse {{ 0%,100% {{ opacity:1; transform:scale(1); }} 50% {{ opacity:0.4; transform:scale(0.65); }} }}
        @keyframes eccSheen {{ from {{ background-position:-150% 0; }} to {{ background-position:250% 0; }} }}
        @keyframes eccGradient {{ from {{ background-position:0% 50%; }} to {{ background-position:200% 50%; }} }}
        @keyframes eccDraw {{ to {{ stroke-dashoffset:0; }} }}
        @keyframes eccSlideDown {{ from {{ opacity:0; transform:translateY(-10px); }} to {{ opacity:1; transform:translateY(0); }} }}

        .block-container {{ animation:eccFadeIn 380ms ease both; }}

        /* Power BI report motion */
        .pbi-header {{ animation:eccSlideDown 440ms cubic-bezier(0.16,1,0.3,1) both; }}
        .pbi-kpi {{ animation:eccFadeUp 400ms cubic-bezier(0.16,1,0.3,1) both;
            transition:box-shadow 180ms ease, transform 180ms ease; }}
        .pbi-kpi:hover {{ transform:translateY(-2px); box-shadow:0 16px 32px rgba(31,41,120,0.12); }}
        [data-testid="stColumn"]:nth-child(2) .pbi-kpi {{ animation-delay:70ms; }}
        [data-testid="stColumn"]:nth-child(3) .pbi-kpi {{ animation-delay:140ms; }}
        [data-testid="stColumn"]:nth-child(4) .pbi-kpi {{ animation-delay:210ms; }}
        .pbi-spark polyline {{ stroke-dasharray:260; stroke-dashoffset:260; animation:eccDraw 950ms ease forwards 220ms; }}

        /* Cards rise in gently (opacity-led so reruns settle, not flicker) */
        [data-testid="stVerticalBlockBorderWrapper"],
        .kpi-card, .callout-card, .checklist-card {{
            animation:eccFadeUp 380ms cubic-bezier(0.16,1,0.3,1) both; }}
        /* Soft stagger across columns in a row */
        [data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlockBorderWrapper"],
        [data-testid="stColumn"]:nth-child(2) .kpi-card {{ animation-delay:70ms; }}
        [data-testid="stColumn"]:nth-child(3) .kpi-card {{ animation-delay:140ms; }}
        [data-testid="stColumn"]:nth-child(4) .kpi-card {{ animation-delay:210ms; }}

        /* KPI chip micro-interaction */
        .kpi-card .kpi-chip {{ transition:transform 200ms cubic-bezier(0.16,1,0.3,1); }}
        .kpi-card:hover .kpi-chip {{ transform:scale(1.1) rotate(-5deg); }}

        /* Transaction rows highlight on hover */
        .txn-row {{ border-radius:12px; padding-left:0.5rem; padding-right:0.5rem;
            transition:background 160ms ease, transform 160ms ease; }}
        .txn-row:hover {{ background:var(--surface-alt); transform:translateX(3px); }}

        /* Button shine sweep on hover */
        .stButton > button, [data-testid="stDownloadButton"] > button {{ position:relative; overflow:hidden; }}
        .stButton > button::after, [data-testid="stDownloadButton"] > button::after {{
            content:""; position:absolute; inset:0; pointer-events:none;
            background:linear-gradient(120deg, transparent 35%, rgba(255,255,255,0.45) 50%, transparent 65%);
            background-size:250% 100%; background-position:-150% 0; }}
        .stButton > button:hover::after, [data-testid="stDownloadButton"] > button:hover::after {{
            animation:eccSheen 720ms ease; }}

        /* Ambient living gradient on promo surfaces */
        .cta-card, .promo-grad {{ background-size:200% 200%; animation:eccGradient 7s linear infinite alternate; }}
        .cta-card {{ animation:eccFadeUp 380ms cubic-bezier(0.16,1,0.3,1) both, eccGradient 7s linear infinite alternate; }}

        /* Shimmer sweep across the risk-mix bar */
        .risk-mix-bar {{ position:relative; overflow:hidden; }}
        .risk-mix-bar::after {{ content:""; position:absolute; inset:0;
            background:linear-gradient(110deg, transparent 30%, rgba(255,255,255,0.55) 50%, transparent 70%);
            background-size:220% 100%; animation:eccSheen 3.2s ease-in-out infinite; }}

        /* Live status dot pulse */
        .status-chip.live .dot {{ animation:eccPulse 1.9s ease-in-out infinite; }}

        /* Nav link nudges right on hover */
        [data-testid="stSidebarNavLink"] {{ transition:background 140ms ease, padding-left 160ms ease; }}
        [data-testid="stSidebarNavLink"]:hover {{ padding-left:0.95rem !important; }}

        @media (prefers-reduced-motion: reduce) {{
            *, *::before, *::after {{ animation:none !important; }}
            .pbi-spark polyline {{ stroke-dashoffset:0 !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_intro(title: str, caption: str, eyebrow: str = "Hi Phạm Ngọc Ánh,") -> None:
    st.markdown(
        f"""
        <div class="app-hero">
            <div class="app-hero-eyebrow">{eyebrow}</div>
            <h1 class="app-hero-title">{title}</h1>
            <p class="app-hero-sub">{caption}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_pill(label: str, color: str) -> str:
    return f"<span class='risk-pill' style='background:{color}'>{label}</span>"


def status_chip(label: str, state: str = "live") -> str:
    return (
        f"<span class='status-chip {state}'><span class='dot' "
        f"style='background:currentColor'></span>{label}</span>"
    )
