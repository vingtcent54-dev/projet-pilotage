"""
Page Performance — Suivi de la performance dans le temps.
Question clé : « Comment ça performe dans le temps ? »
"""
from datetime import date, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dashboard.shared import (
    BG_CHART, BLEU_DARK, CORAIL, COULEURS_COMPTES, FONT_COLOR,
    JAUNE_DARK, ROSE_DARK, TURQUOISE_DK, VERT_DARK, VIOLET_DARK,
    fmt_eur, kpi,
)

COULEURS_BENCH: dict[str, str] = {
    "S&P 500":    "#FF6B35",
    "MSCI World": "#8B5CF6",
    "CAC 40":     "#059669",
    "Nasdaq-100": "#0891B2",
    "STOXX 600":  "#D97706",
}
COULEUR_PTF = BLEU_DARK


@st.cache_data(show_spinner="Calcul de la performance (cours historiques + TWR)…")
def _calc_perf(
    _df_enr_hash,        # non-haché — utilisé uniquement pour invalider le cache
    d_debut: date,
    d_fin: date,
    compte: str | None,
    filtre_isin: str | None,
) -> dict:
    from pipeline.performance import calculer_performance
    return calculer_performance(_df_enr_hash, d_debut, d_fin, compte, filtre_isin)


def render(pos: pd.DataFrame, positions_all: pd.DataFrame, df_enr: pd.DataFrame):
    """Rendu de la page Performance."""
    st.markdown(
        '<div class="page-title">Performance</div>'
        '<div class="page-subtitle">Comment ça performe dans le temps ?</div>',
        unsafe_allow_html=True,
    )

    # ── Filtres ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])

    today = date.today()
    date_min = date(2020, 1, 1)
    date_max = today

    if "date_operation" in df_enr.columns:
        dates = pd.to_datetime(df_enr["date_operation"], errors="coerce").dropna()
        if not dates.empty:
            date_min = dates.min().date()

    with col_f1:
        d_debut = st.date_input("Début", value=date_min, min_value=date_min,
                                max_value=date_max, key="perf_date_debut")
    with col_f2:
        d_fin = st.date_input("Fin", value=today, min_value=date_min,
                              max_value=date_max, key="perf_date_fin")

    # Filtre compte
    filtre_compte = st.session_state.get("filtre_compte", "Tous")
    compte = None if filtre_compte == "Tous" else filtre_compte

    # Sélecteur instrument
    from pipeline.performance import lister_instruments
    instruments = lister_instruments(df_enr)
    options_instru = ["Portefeuille global"] + [
        f"{i.get('symbole', '')} — {i.get('instrument', '')}"
        for i in instruments
    ]

    with col_f3:
        choix_instru = st.selectbox("Instrument", options_instru, key="perf_instrument")

    filtre_isin = None
    if choix_instru != "Portefeuille global":
        idx = options_instru.index(choix_instru) - 1
        if 0 <= idx < len(instruments):
            filtre_isin = instruments[idx].get("isin")

    # ── Calcul ────────────────────────────────────────────────────────────────
    # Utiliser histo (avec quantite_apres_operation) plutôt que df_enr
    histo = st.session_state.get("historique", df_enr)
    result = _calc_perf(histo, d_debut, d_fin, compte, filtre_isin)

    twr_cumule       = result.get("twr_cumule", pd.Series(dtype=float))
    twr_total        = result.get("twr_total", 0.0)
    valeur_quotidienne = result.get("valeur_quotidienne", pd.Series(dtype=float))
    benchmarks       = result.get("benchmarks", {})
    flux_net         = result.get("flux_net", 0.0)

    if twr_cumule.empty:
        st.warning("Pas assez de données pour calculer la performance sur cette période.")
        return

    nb_jours = (d_fin - d_debut).days
    val_debut = float(valeur_quotidienne.iloc[0]) if not valeur_quotidienne.empty else 0.0
    val_fin = float(valeur_quotidienne.iloc[-1]) if not valeur_quotidienne.empty else 0.0

    # Changement valeur du compte = V_fin - V_debut
    changement_valeur = val_fin - val_debut
    # Gains/Pertes = Changement valeur - Flux nets (dépôts/retraits/transferts)
    gains_pertes = changement_valeur - flux_net

    # ── KPI cards ─────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)

    kpi(c1, "% Rendement", f"{twr_total:+.1f} %",
        f"Du {d_debut.strftime('%d/%m/%Y')} au {d_fin.strftime('%d/%m/%Y')}",
        CORAIL,
        cls="pos" if twr_total >= 0 else "neg",
        tooltip="Pourcentage de rendement pondéré en fonction du temps, "
                "prenant en compte les dépôts, retraits et transferts de titres.")
    kpi(c2, "Gains / Pertes", fmt_eur(gains_pertes),
        f"Du {d_debut.strftime('%d/%m/%Y')} au {d_fin.strftime('%d/%m/%Y')}",
        VERT_DARK,
        cls="pos" if gains_pertes >= 0 else "neg",
        tooltip="Variation totale de la valeur du compte durant la période, "
                "corrigée des transferts d&#39;espèces et de titres.")
    kpi(c3, "Chg. valeur compte", fmt_eur(changement_valeur),
        f"Du {d_debut.strftime('%d/%m/%Y')} au {d_fin.strftime('%d/%m/%Y')}",
        BLEU_DARK,
        cls="pos" if changement_valeur >= 0 else "neg",
        tooltip="Variation totale de la valeur du compte entre le début "
                "et la fin de la période sélectionnée.")

    st.divider()

    # ── Graphique TWR vs benchmarks ───────────────────────────────────────────
    label_ptf = "Portefeuille" if not filtre_isin else choix_instru.split(" — ")[0]
    titre_twr = f'<div class="sec-title">Performance TWR · {label_ptf} vs indices</div>'
    st.markdown(titre_twr, unsafe_allow_html=True)

    fig_twr = go.Figure()

    # Courbe portefeuille
    fig_twr.add_trace(go.Scatter(
        x=twr_cumule.index,
        y=twr_cumule.values,
        mode="lines",
        name=label_ptf,
        line=dict(color=COULEUR_PTF, width=2.5),
        hovertemplate="<b>%{x}</b><br>" + label_ptf + " : %{y:+.1f} %<extra></extra>",
    ))

    # Courbes benchmarks
    for nom, serie in benchmarks.items():
        if serie.empty:
            continue
        # Aligner sur la période
        dates_communes = twr_cumule.index.intersection(serie.index)
        if dates_communes.empty:
            continue
        serie_rebasee = serie.reindex(dates_communes)
        couleur = COULEURS_BENCH.get(nom, "#D1D5DB")
        fig_twr.add_trace(go.Scatter(
            x=serie_rebasee.index,
            y=serie_rebasee.values,
            mode="lines",
            name=nom,
            line=dict(color=couleur, width=1.5, dash="dot"),
            hovertemplate="<b>%{x}</b><br>" + nom + " : %{y:+.1f} %<extra></extra>",
        ))

    # Ligne zéro
    fig_twr.add_hline(y=0, line_dash="dash", line_color="#D1D5DB", line_width=1)

    fig_twr.update_layout(
        height=340,
        margin=dict(t=8, b=8, l=8, r=8),
        paper_bgcolor=BG_CHART, plot_bgcolor=BG_CHART,
        font=dict(color=FONT_COLOR, family="Poppins, sans-serif"),
        xaxis=dict(
            showgrid=True, gridcolor="#F3F4F6",
            tickformat="%b %Y", tickfont_size=10,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#F3F4F6",
            ticksuffix=" %", tickfont_size=10,
            zeroline=False,
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="center", x=0.5,
            font_size=10,
        ),
        hovermode="x unified",
    )

    st.plotly_chart(fig_twr, width="stretch", config={"displayModeBar": False})

    # ── Graphique valeur ──────────────────────────────────────────────────────
    label_val = "portefeuille" if not filtre_isin else "position"
    st.markdown(
        f'<div class="sec-title">Valeur du {label_val} (EUR)</div>',
        unsafe_allow_html=True,
    )

    fig_val = go.Figure()
    fig_val.add_trace(go.Scatter(
        x=valeur_quotidienne.index,
        y=valeur_quotidienne.values,
        mode="lines",
        fill="tozeroy",
        name="Valeur EUR",
        line=dict(color=BLEU_DARK, width=2),
        fillcolor="rgba(26, 40, 62, 0.08)",
        hovertemplate="<b>%{x}</b><br>%{y:,.0f} €<extra></extra>",
    ))
    fig_val.update_layout(
        height=240,
        margin=dict(t=8, b=8, l=8, r=8),
        paper_bgcolor=BG_CHART, plot_bgcolor=BG_CHART,
        font=dict(color=FONT_COLOR, family="Poppins, sans-serif"),
        xaxis=dict(
            showgrid=True, gridcolor="#F3F4F6",
            tickformat="%b %Y", tickfont_size=10,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="#F3F4F6",
            ticksuffix=" €", tickfont_size=10,
        ),
        showlegend=False,
        hovermode="x unified",
    )
    st.plotly_chart(fig_val, width="stretch", config={"displayModeBar": False})

    st.markdown(
        '<div class="footnote">Performance calculée en TWR (Time-Weighted Return) · '
        "neutralise l'effet des apports/retraits. Cours historiques via yfinance. "
        "Benchmarks normalisés base 100 à la date de début. Tous les montants en EUR.</div>",
        unsafe_allow_html=True,
    )
