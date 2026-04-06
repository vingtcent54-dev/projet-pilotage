"""
app.py — Point d'entrée du dashboard de pilotage du portefeuille boursier.

Lancement :
    streamlit run dashboard/app.py
"""

import base64
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dashboard.shared import (
    CSS, init_donnees, sidebar_filtres, appliquer_filtres,
)
from dashboard.pages.synthese import render as render_synthese
from dashboard.pages.performance import render as render_performance
from dashboard.pages.convictions import render as render_convictions

# ── Configuration (une seule fois) ─────────────────────────────────────────────
st.set_page_config(
    page_title="ClaudeAlpha",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── Définition des pages ───────────────────────────────────────────────────────
PAGES = [
    {"key": "synthese",    "label": "Synthèse",    "icon": "📊", "renderer": render_synthese},
    {"key": "performance", "label": "Performance", "icon": "📈", "renderer": render_performance},
    {"key": "convictions", "label": "Convictions", "icon": "🎯", "renderer": render_convictions},
]

if "page_active" not in st.session_state:
    st.session_state["page_active"] = "synthese"

# ── Données ────────────────────────────────────────────────────────────────────
positions_all, historique, df_enr = init_donnees()

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    logo_path = Path(__file__).parent / "assets" / "logo.png"
    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
        st.markdown(
            f'<div class="sidebar-logo">'
            f'<img src="data:image/png;base64,{logo_b64}" class="sidebar-logo-img" alt="ClaudeAlpha">'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="sidebar-logo">'
            '<span class="app-name">Claude<span class="app-accent">Alpha</span></span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # Navigation verticale
    st.markdown('<div class="sidebar-nav">', unsafe_allow_html=True)
    for page in PAGES:
        is_active = st.session_state["page_active"] == page["key"]
        cls = "nav-item-active" if is_active else "nav-item"
        clicked = st.button(
            f"{page['icon']}  {page['label']}",
            key=f"nav_{page['key']}",
            use_container_width=True,
        )
        if clicked:
            st.session_state["page_active"] = page["key"]
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Filtres — panneau fenêtre
    filtre_compte, inclure_soldees = sidebar_filtres(positions_all)

# ── Filtrage des positions ─────────────────────────────────────────────────────
pos = appliquer_filtres(positions_all, filtre_compte, inclure_soldees)

# ── Rendu de la page active ────────────────────────────────────────────────────
active_page = next(p for p in PAGES if p["key"] == st.session_state["page_active"])

if pos.empty:
    st.warning("Aucune position à afficher avec ces filtres.")
else:
    active_page["renderer"](pos, positions_all, df_enr)
