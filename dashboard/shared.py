"""
shared.py — Constantes visuelles, CSS et fonctions utilitaires partagées entre pages.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Constantes visuelles — Design System Analyse Business ─────────────────────
# Palette principale — Indigo
PRIMARY       = "#4f46e5"
PRIMARY_LIGHT = "#eef2ff"
PRIMARY_MUTED = "#818cf8"

# Header & texte foncé
HEADER_BG     = "#1e1b4b"

# Couleurs sémantiques
GREEN         = "#059669"
GREEN_LIGHT   = "#ecfdf5"
RED           = "#dc2626"
RED_LIGHT     = "#fef2f2"
AMBER         = "#d97706"
AMBER_LIGHT   = "#fffbeb"
BLUE          = "#2563eb"
BLUE_LIGHT    = "#eff6ff"

# Fond & surfaces
BG_PAGE       = "#f8f9fc"
SURFACE       = "#ffffff"
SURFACE_ALT   = "#f1f4f9"

# Texte
TEXT_COLOR     = "#1e293b"
TEXT_SECONDARY = "#475569"
TEXT_MUTED     = "#94a3b8"

# Bordures & ombres
BORDER        = "#e2e8f0"

# Graphiques
BG_CHART      = "rgba(0,0,0,0)"
FONT_COLOR    = TEXT_COLOR

# Aliases rétrocompatibles (utilisés dans les pages)
CORAIL       = PRIMARY
BLEU_DARK    = HEADER_BG
VIOLET_DARK  = PRIMARY_MUTED
TURQUOISE_DK = BLUE
ROSE_DARK    = RED
JAUNE_DARK   = AMBER
VERT_DARK    = GREEN

COULEURS_COMPTES = {"CTO": BLUE, "PEA": GREEN, "PEA-PME": AMBER}
COULEURS_TYPES   = {"Stock": PRIMARY, "Etf": HEADER_BG, "Etn": BLUE,
                    "Etc": AMBER, "Cash": GREEN}
LABELS_TYPES     = {"Stock": "Actions", "Etf": "ETF", "Etn": "ETN", "Etc": "ETC", "Cash": "Cash"}

SEUIL_ORANGE = 8.0   # % pondération — point d'attention
SEUIL_ROUGE  = 10.0  # % pondération — surpondération

DEVISES_SYMBOLES = {"EUR": "\u202f\u20ac", "USD": "\u202f$", "GBP": "\u202f\u00a3", "HKD": "\u202fHK$"}


# ── CSS ────────────────────────────────────────────────────────────────────────
CSS = """
<style>
/* ── Masquer la navigation automatique Streamlit (pages/) ── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Design System Analyse Business — Indigo / Poppins+Lato+JetBrains Mono ── */
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Lato:wght@400;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Logo sidebar ── */
.sidebar-logo {
    display: flex; justify-content: center; align-items: center;
    padding: 12px 0 8px;
}
.sidebar-logo-img {
    width: 100%; max-width: 160px; height: auto;
    object-fit: contain;
}
.app-name {
    font-family: 'Poppins', sans-serif;
    font-size: 1.4rem; font-weight: 700;
    color: #1e293b; letter-spacing: -.02em;
}
.app-accent { color: #4f46e5; }

/* Fond général */
[data-testid="stAppViewContainer"] { background: #f8f9fc; }
[data-testid="stSidebar"]          { background: #eef2ff; border-right: 1px solid #e2e8f0; }
[data-testid="stHeader"]           { background: transparent; }

/* Typographie globale */
html, body, [class*="css"] {
    font-family: 'Lato', sans-serif !important;
}

/* ── Navigation verticale sidebar ── */
.sidebar-nav { margin: 4px 0 12px; display: flex; flex-direction: column; gap: 4px; }

/* ── Sidebar ── */
[data-testid="stSidebar"] { width: 230px !important; min-width: 230px !important; }
[data-testid="stSidebar"] > div:first-child { padding-top: 0.5rem; }

/* Boutons nav sidebar — état normal */
[data-testid="stSidebar"] [data-testid="stButton"] > button {
    background: transparent !important;
    color: #1e293b !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Poppins', sans-serif !important;
    font-size: .85rem !important; font-weight: 500 !important;
    padding: 9px 12px !important;
    text-align: left !important;
    transition: background 0.15s ease !important;
    width: 100% !important;
    justify-content: flex-start !important;
}
[data-testid="stSidebar"] [data-testid="stButton"] > button:hover {
    background: #eef2ff !important;
    color: #4f46e5 !important;
}

/* Panneau filtres — style "fenêtre" */
.filter-panel {
    background: #ffffff;
    border: 1.5px solid #e2e8f0;
    border-radius: 12px;
    padding: 12px 14px 14px;
    margin-top: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
}
.filter-panel-title {
    font-family: 'Poppins', sans-serif; font-size: .65rem; font-weight: 700;
    color: #4f46e5; text-transform: uppercase; letter-spacing: .1em;
    margin-bottom: 10px; padding-bottom: 6px;
    border-bottom: 1.5px solid #e2e8f0;
}
.sidebar-meta {
    font-family: 'Lato', sans-serif; font-size: .65rem;
    color: #94a3b8; line-height: 1.5; margin-top: 8px;
}

/* KPI cards */
.kpi-wrap  { display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 4px; }
.kpi-card  {
    flex: 1 1 auto; min-width: 0; background: #ffffff; border-radius: 12px;
    padding: 14px 16px; border-top: 3px solid;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
    border-left: none;
    overflow: hidden;
    height: 100%; display: flex; flex-direction: column; justify-content: center;
}

/* Forcer les colonnes Streamlit KPI à même hauteur */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div {
    height: 100%;
}
.kpi-lbl   { font-size:.68rem; color:#94a3b8; font-weight:600;
             text-transform:uppercase; letter-spacing:.08em;
             font-family: 'Poppins', sans-serif;
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
             display: flex; align-items: center; gap: 4px; }
.kpi-lbl .kpi-info {
    display: inline-flex; align-items: center; justify-content: center;
    width: 14px; height: 14px; border-radius: 50%; background: #f1f4f9;
    color: #94a3b8; font-size: .55rem; font-weight: 700; cursor: help;
    flex-shrink: 0; position: relative; text-transform: none; letter-spacing: 0;
}
.kpi-lbl .kpi-info:hover::after {
    content: attr(data-tooltip);
    position: absolute; bottom: 120%; left: 50%; transform: translateX(-50%);
    background: #1e1b4b; color: #fff; font-size: .65rem; font-weight: 400;
    padding: 6px 10px; border-radius: 8px; white-space: normal;
    width: max-content; max-width: 240px; z-index: 999;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06); line-height: 1.4;
    text-transform: none; letter-spacing: 0;
}
.kpi-val   { font-size:1.45rem; font-weight:700; color:#1e293b; margin-top:4px; line-height:1.1;
             font-family: 'JetBrains Mono', monospace;
             white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kpi-sub   { font-size:.68rem; color:#475569; margin-top:4px;
             font-family: 'Lato', sans-serif;
             word-break: break-word; line-height: 1.3; }
.pos       { color:#059669 !important; }
.neg       { color:#dc2626 !important; }

/* Section titles */
.sec-title {
    font-size:.7rem; font-weight:700; color:#4f46e5;
    text-transform:uppercase; letter-spacing:.1em;
    margin: 18px 0 10px; padding-bottom:6px;
    border-bottom: 2px solid #4f46e5;
    font-family: 'Poppins', sans-serif;
}

/* Badge compte */
.badge { display:inline-block; border-radius:5px; padding:2px 10px;
         font-size:.72rem; font-weight:700; margin-bottom:6px;
         font-family: 'Poppins', sans-serif; }
.badge-CTO     { background:#eff6ff; color:#2563eb; }
.badge-PEA     { background:#ecfdf5; color:#059669; }
.badge-PEA-PME { background:#fffbeb; color:#d97706; }

/* Table footer */
.tbl-footer { text-align:right; font-size:.78rem; color:#475569;
              margin:-12px 0 20px; padding-right: 4px;
              font-family: 'Lato', sans-serif;
              word-break: break-word; }

/* Note de bas de page */
.footnote  { font-size:.7rem; color:#94a3b8; margin-top:10px;
             font-family: 'Lato', sans-serif; }

/* Sidebar text — minimaliste */
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stMarkdown span {
    color: #1e293b; font-size: .78rem;
}
[data-testid="stSidebar"] .stSelectbox label {
    font-size: .72rem !important;
}
[data-testid="stSidebar"] .stCheckbox label span {
    font-size: .75rem !important;
}
[data-testid="stSidebar"] hr {
    margin: 10px 0; border-color: #e2e8f040;
}

/* Main title */
.main h2 { color: #1e293b !important;
    font-family: 'Poppins', sans-serif !important; font-weight: 700 !important; }

/* Page title with icon */
.page-title {
    font-family: 'Poppins', sans-serif;
    font-weight: 700; font-size: 1.5rem;
    color: #1e293b; margin-bottom: 4px;
    display: flex; align-items: center; gap: 10px;
}
.page-subtitle {
    font-family: 'Lato', sans-serif;
    font-size: .8rem; color: #475569;
    margin-bottom: 16px;
}

/* Bouton Recharger — dans le panneau filtres */
.filter-panel [data-testid="stButton"] > button,
[data-testid="stSidebar"] .filter-reload button {
    background-color: #1e1b4b !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
    font-size: .75rem !important;
    padding: 7px 12px !important;
    margin-top: 6px !important;
    width: 100% !important;
}
[data-testid="stSidebar"] .filter-reload button:hover {
    background-color: #4f46e5 !important;
}

/* Selectbox / inputs */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stCheckbox label {
    color: #1e293b !important;
    font-family: 'Poppins', sans-serif !important;
    font-weight: 500 !important;
}

/* Streamlit columns — empêcher la troncature */
[data-testid="stHorizontalBlock"] { flex-wrap: wrap; gap: 8px; }
[data-testid="stHorizontalBlock"] > div { min-width: 0; }

/* Dataframe — pleine largeur sans scroll horizontal caché */
[data-testid="stDataFrame"] { width: 100% !important; }
[data-testid="stDataFrame"] > div { width: 100% !important; }

/* Placeholder (pages en construction) */
.placeholder-box {
    background: #eef2ff; border: 2px dashed #818cf8; border-radius: 12px;
    padding: 40px; text-align: center; margin: 20px 0;
    font-family: 'Lato', sans-serif;
}
.placeholder-box .icon { font-size: 2.5rem; margin-bottom: 12px; }
.placeholder-box .title { font-size: 1.1rem; font-weight: 600; color: #1e293b;
                           font-family: 'Poppins', sans-serif; }
.placeholder-box .desc  { font-size: .85rem; color: #475569; margin-top: 6px; }

/* ── Responsive — petits écrans ── */
@media (max-width: 900px) {
    .kpi-val  { font-size: 1.2rem; }
    .kpi-lbl  { font-size: .62rem; }
    .kpi-sub  { font-size: .62rem; }
    .kpi-card { padding: 10px 12px; }

    /* Empiler les colonnes Streamlit */
    [data-testid="stHorizontalBlock"] { flex-direction: column; }
    [data-testid="stHorizontalBlock"] > div { flex: 1 1 100% !important; width: 100% !important; }

    .tbl-footer { font-size: .7rem; text-align: left; }
}

@media (max-width: 600px) {
    .kpi-val  { font-size: 1rem; }
    .kpi-card { padding: 8px 10px; }
    .sec-title { font-size: .6rem; }

    [data-testid="stHorizontalBlock"]:first-of-type { gap: 6px !important; }
    [data-testid="stHorizontalBlock"]:first-of-type button {
        font-size: .78rem !important; padding: 10px 6px !important;
    }
}
</style>
"""


# ── Helpers ────────────────────────────────────────────────────────────────────
def fmt_eur(v: float, signed=False) -> str:
    """Formate un montant en EUR avec séparateur d'espace (style français)."""
    fmt = f"{v:+,.0f} €" if signed else f"{v:,.0f} €"
    return fmt.replace(",", "\u202f")   # espace fine insécable


def kpi(col, label: str, value: str, sub: str, color: str, cls: str = "",
        tooltip: str = ""):
    info = (f'<span class="kpi-info" data-tooltip="{tooltip}">i</span>'
            if tooltip else "")
    with col:
        st.markdown(
            f'<div class="kpi-card" style="border-top-color:{color}">'
            f'<div class="kpi-lbl">{label}{info}</div>'
            f'<div class="kpi-val {cls}">{value}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def donut(labels, values, colors, annotation="", height=240):
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.60,
        marker=dict(colors=colors, line=dict(color="#FFFFFF", width=2)),
        textinfo="label+percent",
        textfont_size=11,
        hovertemplate="<b>%{label}</b><br>%{value:,.0f} €<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        showlegend=False,
        margin=dict(t=8, b=8, l=8, r=8),
        height=height,
        paper_bgcolor=BG_CHART, plot_bgcolor=BG_CHART,
        font=dict(color=FONT_COLOR, family="Poppins, sans-serif"),
        annotations=[dict(
            text=annotation, x=0.5, y=0.5, showarrow=False,
            font=dict(size=13, color=BLEU_DARK, weight="bold"),
        )] if annotation else [],
    )
    return fig


def bar_positions(pos: pd.DataFrame, height=310):
    # Utiliser la valeur de marché si disponible
    a_vm = "valeur_marche_eur" in pos.columns and pos["valeur_marche_eur"].notna().any()
    col_val = "valeur_marche_eur" if a_vm else "cout_investi_eur"

    df = pos[pos["cout_investi_eur"] > 0].copy()
    # Fallback sur cout_investi si valeur marché absente pour certaines lignes
    if a_vm:
        df[col_val] = df[col_val].fillna(df["cout_investi_eur"])

    # Pondération en % du portefeuille total
    total_ptf = df[col_val].sum()
    df["poids_pct"] = (df[col_val] / total_ptf * 100) if total_ptf > 0 else 0.0
    df = df.sort_values("poids_pct")

    # Tronquer les noms d'instruments trop longs
    df["label"] = df["instrument"].str.strip().str.slice(0, 22)

    # Couleurs selon la pondération
    couleurs = []
    for pct in df["poids_pct"]:
        if pct >= SEUIL_ROUGE:
            couleurs.append(RED)
        elif pct >= SEUIL_ORANGE:
            couleurs.append(AMBER)
        else:
            couleurs.append(GREEN)

    fig = go.Figure(go.Bar(
        x=df["poids_pct"],
        y=df["label"],
        orientation="h",
        marker=dict(color=couleurs, opacity=0.88),
        text=[f"{p:.1f} %" for p in df["poids_pct"]],
        textposition="outside",
        textfont=dict(size=10, color=BLEU_DARK),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Poids : %{x:.1f} %<br>"
            "Valeur : %{customdata[1]:,.0f} €<br>"
            "%{customdata[2]}<extra></extra>"
        ),
        customdata=list(zip(
            df["instrument"],
            df[col_val],
            df["type_compte"],
        )),
    ))
    fig.update_layout(
        height=height,
        margin=dict(t=8, b=8, l=8, r=60),
        paper_bgcolor=BG_CHART, plot_bgcolor=BG_CHART,
        font=dict(color=FONT_COLOR, family="Poppins, sans-serif"),
        xaxis=dict(showgrid=True, gridcolor="#e2e8f0", tickfont_size=10,
                   zeroline=False, showticklabels=False,
                   range=[0, df["poids_pct"].max() * 1.25]),
        yaxis=dict(tickfont_size=10, automargin=True),
        bargap=0.30,
    )
    return fig


def fmt_devise(row, col):
    """Formate une valeur en devise locale selon l'instrument."""
    dev = row["devise_instrument"]
    suf = DEVISES_SYMBOLES.get(dev, f"\u202f{dev}")
    return f"{row[col]:.2f}{suf}"


def placeholder(icon: str, title: str, description: str):
    """Affiche un bloc placeholder pour les pages en construction."""
    st.markdown(
        f'<div class="placeholder-box">'
        f'<div class="icon">{icon}</div>'
        f'<div class="title">{title}</div>'
        f'<div class="desc">{description}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Chargement des données (mis en cache) ──────────────────────────────────────
@st.cache_data(show_spinner="Chargement des exports Saxo Bank…")
def charger_donnees():
    from pipeline.ingestion import charger_tous_les_fichiers
    from pipeline.nettoyage import (
        assembler_transactions_enrichies,
        preparer_bookings,
        preparer_operations,
        preparer_transactions,
    )
    from pipeline.positions import calculer_cump

    import io, contextlib
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        df_t_raw, df_o_raw, df_b_raw = charger_tous_les_fichiers()
        df_t     = preparer_transactions(df_t_raw)
        df_o     = preparer_operations(df_o_raw)
        df_b     = preparer_bookings(df_b_raw)
        df_enr   = assembler_transactions_enrichies(df_t, df_o, df_b, df_o_raw=df_o_raw)
        pos, histo = calculer_cump(df_enr)
    return pos, histo, df_enr


@st.cache_data(show_spinner="Récupération des cours de marché…", ttl=300)
def charger_cotations(positions: pd.DataFrame) -> pd.DataFrame:
    """Récupère les cours actuels et valorise les positions (cache 5 min)."""
    from pipeline.cotations import valoriser_positions
    return valoriser_positions(positions)


def init_donnees():
    """Charge et valorise les données, les stocke dans session_state."""
    if "positions_all" not in st.session_state:
        pos, histo, df_enr = charger_donnees()
        pos = charger_cotations(pos)
        st.session_state["positions_all"] = pos
        st.session_state["historique"] = histo
        st.session_state["df_enr"] = df_enr

    return (
        st.session_state["positions_all"],
        st.session_state["historique"],
        st.session_state["df_enr"],
    )


def sidebar_filtres(positions_all: pd.DataFrame):
    """Affiche les filtres dans la sidebar — panneau fenêtre."""
    st.markdown('<div class="filter-panel">', unsafe_allow_html=True)
    st.markdown('<div class="filter-panel-title">Filtres</div>', unsafe_allow_html=True)

    comptes_dispo   = ["Tous"] + sorted(positions_all["type_compte"].unique())
    filtre_compte   = st.selectbox("Compte", comptes_dispo, key="filtre_compte")
    inclure_soldees = st.checkbox("Positions soldées", value=False, key="inclure_soldees")

    st.markdown('<div class="filter-reload">', unsafe_allow_html=True)
    if st.button("↺ Recharger", use_container_width=True,
                 help="Efface le cache et relit les fichiers + cours"):
        st.cache_data.clear()
        for k in ["positions_all", "historique", "df_enr"]:
            st.session_state.pop(k, None)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Upload d'un nouvel extrait ──
    # Clé dynamique : on incrémente un compteur après chaque upload réussi
    # pour réinitialiser le widget (purger le fichier affiché).
    upload_gen = st.session_state.get("_upload_gen", 0)
    uploaded = st.file_uploader(
        "Charger un extrait Saxo",
        type=["xlsx"],
        key=f"upload_extrait_{upload_gen}",
        help="Fichier Transactions_*.xlsx exporté depuis Saxo Bank",
    )
    if uploaded is not None:
        from pipeline.ingestion import valider_fichier_saxo
        from pipeline.gdrive import uploader_fichier_xlsx

        contenu = uploaded.getvalue()
        erreurs = valider_fichier_saxo(contenu, uploaded.name)

        if erreurs:
            for e in erreurs:
                st.error(e)
        else:
            try:
                uploader_fichier_xlsx(uploaded.name, contenu)
                # Incrémenter la clé pour purger le widget au prochain rerun
                st.session_state["_upload_gen"] = upload_gen + 1
                st.toast(f"« {uploaded.name} » chargé sur Drive.")
                # Rafraîchir les données automatiquement
                st.cache_data.clear()
                for k in ["positions_all", "historique", "df_enr"]:
                    st.session_state.pop(k, None)
                st.rerun()
            except Exception as exc:
                st.error(f"Erreur lors de l'upload : {exc}")

    # Méta-infos compactes
    from pipeline.gdrive import lister_fichiers_saxo
    fichiers_saxo = lister_fichiers_saxo()
    dates_debut, dates_fin = [], []
    for f in fichiers_saxo:
        stem = f["name"].replace(".xlsx", "")
        parts = stem.split("_")
        if len(parts) >= 4:
            dates_debut.append(parts[2])
            dates_fin.append(parts[3])

    periode = f"{min(dates_debut)} — {max(dates_fin)}" if dates_debut else "—"
    a_cours = "valeur_marche_eur" in positions_all.columns and positions_all["valeur_marche_eur"].notna().any()
    source_cours = "yfinance 5 min" if a_cours else "exports uniquement"

    st.markdown(
        f'<div class="sidebar-meta">'
        f'{len(fichiers_saxo)} fichiers Saxo<br>'
        f'{periode}<br>'
        f'CUMP · EUR · {source_cours}'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    return filtre_compte, inclure_soldees


def appliquer_filtres(positions_all, filtre_compte, inclure_soldees):
    """Applique les filtres compte et positions soldées."""
    pos = positions_all.copy()
    if not inclure_soldees:
        pos = pos[~pos["position_soldee"]]
    if filtre_compte != "Tous":
        pos = pos[pos["type_compte"] == filtre_compte]
    return pos
