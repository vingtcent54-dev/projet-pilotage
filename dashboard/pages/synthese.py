"""
Page Synthèse — Vue d'ensemble du portefeuille.
Question clé : « Où en est mon portefeuille aujourd'hui ? »
"""
import pandas as pd
import streamlit as st
from dashboard.shared import (
    BLEU_DARK, CORAIL, COULEURS_COMPTES, COULEURS_TYPES,
    FONT_COLOR, JAUNE_DARK, LABELS_TYPES, TURQUOISE_DK, VERT_DARK,
    bar_positions, donut, fmt_devise, fmt_eur, kpi,
)


def render(pos: pd.DataFrame, positions_all: pd.DataFrame, df_enr: pd.DataFrame):
    """Rendu de la page Synthèse."""
    st.markdown(
        '<div class="page-title">Synthèse</div>'
        '<div class="page-subtitle">Où en est mon portefeuille aujourd\'hui ?</div>',
        unsafe_allow_html=True,
    )

    # ── Indicateurs disponibles ───────────────────────────────────────────────
    a_cours = (
        "valeur_marche_eur" in pos.columns and pos["valeur_marche_eur"].notna().any()
    )
    if not a_cours:
        st.info("Données issues des exports Saxo Bank · Cours de marché indisponibles")

    pos_ouvertes = pos[~pos["position_soldee"]]

    # ── Calcul des totaux ─────────────────────────────────────────────────────
    t_investi  = pos_ouvertes["cout_investi_eur"].sum()
    t_pv_real  = pos["pv_realisee_eur"].sum() if "pv_realisee_eur" in pos.columns else 0.0

    # Cash disponible = solde net de tous les montants comptabilisés (dépôts, retraits,
    # achats, ventes, dividendes) — filtré sur les mêmes comptes que pos
    cash_total = 0.0
    if "montant_eur" in df_enr.columns and "type_compte" in df_enr.columns:
        comptes_actifs = pos["type_compte"].unique() if not pos.empty else positions_all["type_compte"].unique()
        cash_total = float(df_enr[df_enr["type_compte"].isin(comptes_actifs)]["montant_eur"].sum())

    if a_cours:
        t_valeur   = pos_ouvertes["valeur_marche_eur"].sum() + cash_total
        t_pv_lat   = pos_ouvertes["pv_latente_eur"].sum() if "pv_latente_eur" in pos_ouvertes.columns else 0.0
        pv_lat_pct = round(t_pv_lat / t_investi * 100, 1) if t_investi else 0.0
    else:
        t_valeur   = t_investi + cash_total
        t_pv_lat   = 0.0
        pv_lat_pct = 0.0

    cash_pct = round(cash_total / t_valeur * 100, 1) if t_valeur else 0.0

    nb_ouvertes  = int((~pos["position_soldee"]).sum())
    nb_lignes_tot = len(pos)

    pv_cls     = "pos" if t_pv_lat >= 0 else "neg"
    lat_cls    = "pos" if t_pv_lat >= 0 else "neg"

    # ── KPI cards ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    kpi(c1, "Valeur du compte", fmt_eur(t_valeur),
        f"Capital investi : {fmt_eur(t_investi)}", CORAIL)
    kpi(c2, "Cash disponible", fmt_eur(cash_total),
        f"{cash_pct:.1f} % du compte", TURQUOISE_DK)
    kpi(c3, "PV latente", fmt_eur(t_pv_lat, signed=True),
        f"{pv_lat_pct:+.1f} % sur le capital investi", VERT_DARK, cls=pv_cls)
    kpi(c4, "PV réalisées", fmt_eur(t_pv_real, signed=True),
        f"{nb_ouvertes} positions ouvertes · {nb_lignes_tot - nb_ouvertes} soldées",
        JAUNE_DARK, cls=("pos" if t_pv_real >= 0 else "neg"))

    st.divider()

    # ── Graphiques répartition ────────────────────────────────────────────────
    col_d1, col_d2, col_valeur = st.columns([1, 1, 2])

    # Répartition par compte
    with col_d1:
        rpt_cpt = (
            pos_ouvertes.groupby("type_compte")[
                "valeur_marche_eur" if a_cours else "cout_investi_eur"
            ].sum()
        )
        label_grp = f"Répartition par compte ({fmt_eur(rpt_cpt.sum())})"
        st.markdown(f'<div class="sec-title">{label_grp}</div>', unsafe_allow_html=True)
        if not rpt_cpt.empty:
            fig1 = donut(
                labels=rpt_cpt.index.tolist(),
                values=rpt_cpt.values.tolist(),
                colors=[COULEURS_COMPTES.get(c, BLEU_DARK) for c in rpt_cpt.index],
                annotation=fmt_eur(rpt_cpt.sum()),
            )
            st.plotly_chart(fig1, width="stretch",
                            config={"displayModeBar": False})

    # Répartition par type d'actif
    with col_d2:
        st.markdown('<div class="sec-title">Répartition par type d\'actif</div>',
                    unsafe_allow_html=True)
        rpt_type = (
            pos_ouvertes.groupby("type_instrument")[
                "valeur_marche_eur" if a_cours else "cout_investi_eur"
            ].sum()
        )
        if not rpt_type.empty:
            labels = [LABELS_TYPES.get(t, t) for t in rpt_type.index]
            fig2 = donut(
                labels=labels,
                values=rpt_type.values.tolist(),
                colors=[COULEURS_TYPES.get(t, BLEU_DARK) for t in rpt_type.index],
            )
            st.plotly_chart(fig2, width="stretch",
                            config={"displayModeBar": False})

    # Pondération des positions
    with col_valeur:
        st.markdown('<div class="sec-title">Pondération des positions</div>',
                    unsafe_allow_html=True)
        if not pos_ouvertes.empty:
            st.plotly_chart(bar_positions(pos_ouvertes), width="stretch",
                            config={"displayModeBar": False})

    st.divider()

    # ── Table des positions ───────────────────────────────────────────────────
    st.markdown('<div class="sec-title">Détail des positions</div>', unsafe_allow_html=True)

    filtre_compte   = st.session_state.get("filtre_compte", "Tous")
    inclure_soldees = st.session_state.get("inclure_soldees", False)

    df_disp = pos.copy()

    # Badge compte
    df_disp["Compte"] = df_disp["type_compte"].apply(
        lambda t: f'<span class="badge badge-{t}">{t}</span>'
    )

    # Colonnes à afficher
    cols_disp = {
        "symbole":         "Symbole",
        "instrument":      "Instrument",
        "quantite":        "Quantité",
        "pru_eur":         "PRU (€)",
        "cout_investi_eur": "Investi (€)",
    }
    if a_cours:
        cols_disp["valeur_marche_eur"] = "Valeur (€)"
        cols_disp["pv_latente_eur"]    = "PV latente (€)"
        cols_disp["pv_latente_pct"]    = "PV latente (%)"
    cols_disp["pv_realisee_eur"]   = "PV réalisée (€)"
    cols_disp["nb_achats"]         = "Achats"
    cols_disp["nb_ventes"]         = "Ventes"
    cols_disp["derniere_operation"] = "Dernière op."

    df_final = df_disp[[c for c in cols_disp if c in df_disp.columns]].rename(columns=cols_disp)
    df_final["Statut"] = df_disp["position_soldee"].map({True: "soldée", False: "ouverte"})
    df_final["Compte"] = df_disp["type_compte"]

    # Coloration PV% — 3 zones : positif / neutre / négatif (pastels charte MH)
    SEUIL_NEUTRE = 5.0  # % : entre -5% et +5% → zone neutre
    def _color_pv_pct(val):
        if pd.isna(val):
            return ""
        if val >= SEUIL_NEUTRE:
            return f"background-color: #E1FBF6; color: {VERT_DARK}"   # Vert pastel / Vert dark
        if val > -SEUIL_NEUTRE:
            return "background-color: #FED7AA; color: #C2410C"         # Orange pastel / Orange foncé
        return f"background-color: #FFF2F0; color: {CORAIL}"           # Corail pastel / Corail MH

    styled = df_final.style
    if "PV latente (%)" in df_final.columns:
        styled = styled.map(_color_pv_pct, subset=["PV latente (%)"])

    # Formatage numérique
    col_config = {}
    if "Quantité" in df_final.columns:
        col_config["Quantité"] = st.column_config.NumberColumn("Quantité", format="%d")
    for c in ["Investi (€)", "Valeur (€)", "PV latente (€)", "PV réalisée (€)", "PRU (€)"]:
        if c in df_final.columns:
            col_config[c] = st.column_config.NumberColumn(c, format="%.2f €")
    if "PV latente (%)" in df_final.columns:
        col_config["PV latente (%)"] = st.column_config.NumberColumn("PV latente (%)", format="%+.1f %%")
    if "Dernière op." in df_final.columns:
        col_config["Dernière op."] = st.column_config.DateColumn("Dernière op.", format="DD/MM/YYYY")

    st.dataframe(
        styled,
        width="stretch",
        hide_index=True,
        column_config=col_config,
    )

    # ── Footer ────────────────────────────────────────────────────────────────
    lbl_total = f"Total {filtre_compte}"

    t_val    = pos_ouvertes["valeur_marche_eur"].sum() if a_cours else None
    t_inv    = pos_ouvertes["cout_investi_eur"].sum()
    t_pv_l   = pos_ouvertes["pv_latente_eur"].sum() if a_cours and "pv_latente_eur" in pos_ouvertes.columns else None
    t_pv_r   = pos["pv_realisee_eur"].sum() if "pv_realisee_eur" in pos.columns else 0.0

    pv_cls2 = "pos" if (t_pv_l or 0) >= 0 else "neg"

    if a_cours and t_val is not None and t_pv_l is not None:
        st.markdown(
            f'<div class="tbl-footer">{lbl_total}'
            f' · Valeur : <b style="color:{BLEU_DARK}">{fmt_eur(t_val)}</b>'
            f' &nbsp;·&nbsp; PV latente : <b class="{pv_cls2}">{fmt_eur(t_pv_l, signed=True)}</b>'
            f' &nbsp;·&nbsp; PV réalisée : <b class="{"pos" if t_pv_r >= 0 else "neg"}">'
            f'{fmt_eur(t_pv_r, signed=True)}</b></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="tbl-footer">{lbl_total}'
            f' · Investi : <b style="color:{BLEU_DARK}">{fmt_eur(t_inv)}</b>'
            f' &nbsp;·&nbsp; PV réalisées : <b class="{"pos" if t_pv_r >= 0 else "neg"}">'
            f'{fmt_eur(t_pv_r, signed=True)}</b></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="footnote">PRU calculé par méthode CUMP incluant commissions, TTF et coûts de conversion. '
        'Cours de marché via yfinance (cache 5 min). Données en EUR.</div>',
        unsafe_allow_html=True,
    )
