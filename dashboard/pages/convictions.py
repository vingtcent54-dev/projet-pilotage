"""
Page Convictions — Thèses d'investissement et watchlist.
Question clé : « Pourquoi je suis positionné ainsi ? »
"""
import pandas as pd
import streamlit as st
from dashboard.shared import placeholder


def render(pos: pd.DataFrame, positions_all: pd.DataFrame, df_enr: pd.DataFrame):
    """Rendu de la page Convictions."""
    st.markdown(
        '<div class="page-title">Convictions</div>'
        '<div class="page-subtitle">Pourquoi je suis positionné ainsi ?</div>',
        unsafe_allow_html=True,
    )
    placeholder(
        "🎯",
        "Convictions à venir",
        "Thèses d'investissement · Liens vers analyses Blue Team / Red Team "
        "· Watchlist · Suivi des points d'entrée",
    )
