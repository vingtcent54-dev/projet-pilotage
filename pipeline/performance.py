"""
performance.py — Calcul de la performance TWR (Time-Weighted Return).

Neutralise l'effet des apports/retraits de cash pour mesurer la performance
pure de la gestion. Benchmark contre S&P 500, MSCI World, CAC 40, Nasdaq-100, STOXX 600.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import yfinance as yf

# Tickers yfinance des benchmarks
TICKERS_BENCHMARKS: dict[str, str] = {
    "S&P 500":   "^GSPC",
    "MSCI World": "URTH",
    "CAC 40":    "^FCHI",
    "Nasdaq-100": "^NDX",
    "STOXX 600": "^STOXX",
}


def lister_instruments(df_enr: pd.DataFrame) -> list[dict]:
    """
    Retourne la liste des instruments disponibles dans l'historique.

    Retourne
    --------
    Liste de dicts {"isin": ..., "symbole": ..., "instrument": ...}
    """
    if df_enr is None or df_enr.empty:
        return []

    cols_needed = [c for c in ["isin", "symbole", "instrument"] if c in df_enr.columns]
    if not cols_needed:
        return []

    return (
        df_enr[cols_needed]
        .drop_duplicates()
        .dropna(subset=["isin"])
        .to_dict(orient="records")
    )


def calculer_performance(
    df_enr: pd.DataFrame,
    d_debut: date,
    d_fin: date,
    compte: str | None = None,
    filtre_isin: str | None = None,
) -> dict:
    """
    Calcule la performance TWR sur la période [d_debut, d_fin].

    Paramètres
    ----------
    df_enr      : historique des transactions enrichies (depuis positions.calculer_cump)
    d_debut     : date de début (inclusive)
    d_fin       : date de fin (inclusive)
    compte      : filtre sur type_compte ("CTO", "PEA", "PEA-PME" ou None = tous)
    filtre_isin : ISIN d'un instrument spécifique (ou None = portefeuille global)

    Retourne
    --------
    dict avec clés :
        twr_cumule       : pd.Series (date → TWR cumulé en %, base 0)
        twr_total        : float (TWR total en %)
        twr_annualise    : float (TWR annualisé en %)
        valeur_quotidienne : pd.Series (date → valeur EUR)
        benchmarks       : dict {nom → pd.Series (date → perf cumulée en %)}
    """
    resultat_vide = {
        "twr_cumule": pd.Series(dtype=float),
        "twr_total": 0.0,
        "twr_annualise": 0.0,
        "valeur_quotidienne": pd.Series(dtype=float),
        "benchmarks": {},
        "flux_net": 0.0,
    }

    if df_enr is None or df_enr.empty:
        return resultat_vide

    df = df_enr.copy()

    # Convertir les dates
    if "date_operation" in df.columns:
        df["date_operation"] = pd.to_datetime(df["date_operation"], errors="coerce")

    d_debut_ts = pd.Timestamp(d_debut)
    d_fin_ts = pd.Timestamp(d_fin)

    # Filtres compte / instrument (sans filtre date)
    if compte and "type_compte" in df.columns:
        df = df[df["type_compte"] == compte]
    if filtre_isin and "isin" in df.columns:
        df = df[df["isin"] == filtre_isin]

    # df_all = tout l'historique (pour quantités détenues à chaque date)
    # df     = restreint à la période (pour les flux TWR)
    df_all = df.copy()
    df = df[
        (df["date_operation"] >= d_debut_ts) &
        (df["date_operation"] <= d_fin_ts)
    ]

    if df_all.empty:
        return resultat_vide

    # ── Valeur quotidienne via cours historiques yfinance ─────────────────────
    # Symboles : tous ceux qui apparaissent dans l'historique complet
    symboles = df_all["symbole"].dropna().unique().tolist() if "symbole" in df_all.columns else []

    from pipeline.cotations import symbole_vers_ticker

    ticker_map: dict[str, str] = {}
    devise_map: dict[str, str] = {}  # symbole → devise_instrument
    for sym in symboles:
        t = symbole_vers_ticker(sym)
        if t:
            ticker_map[sym] = t
        # Devise de chaque instrument
        if "devise_instrument" in df_all.columns:
            dev = df_all.loc[df_all["symbole"] == sym, "devise_instrument"].dropna()
            if not dev.empty:
                devise_map[sym] = str(dev.iloc[0])

    # Récupérer les cours historiques
    tickers_list = list(set(ticker_map.values()))
    prix_histo: pd.DataFrame = pd.DataFrame()

    # Taux de change quotidiens pour devises étrangères → EUR
    devises_etrangeres = {d for d in devise_map.values() if d and d != "EUR"}
    paires_fx = {d: f"{d}EUR=X" for d in devises_etrangeres}
    fx_histo: dict[str, pd.Series] = {}  # devise → série de taux quotidiens

    tickers_a_telecharger = tickers_list + list(paires_fx.values())

    if tickers_a_telecharger:
        raw = yf.download(
            tickers_a_telecharger,
            start=d_debut_ts - timedelta(days=5),
            end=d_fin_ts + timedelta(days=1),
            auto_adjust=True,
            progress=False,
        )
        if not raw.empty:
            if len(tickers_a_telecharger) == 1:
                t = tickers_a_telecharger[0]
                close_col = raw[["Close"]].rename(columns={"Close": t})
                if t in tickers_list:
                    prix_histo = close_col
                else:
                    for devise, paire in paires_fx.items():
                        if t == paire:
                            fx_histo[devise] = close_col[t].dropna()
            elif "Close" in raw.columns:
                close_all = raw["Close"]
                # Séparer prix et FX
                cols_prix = [c for c in tickers_list if c in close_all.columns]
                if cols_prix:
                    prix_histo = close_all[cols_prix].dropna(axis=1, how="all")
                for devise, paire in paires_fx.items():
                    if paire in close_all.columns:
                        fx_histo[devise] = close_all[paire].dropna()

    # ── Pré-calcul des facteurs de split futurs par symbole ─────────────────
    # yfinance retourne des prix post-split, mais Saxo peut appliquer les splits
    # avec retard → les quantités pré-split doivent être ajustées.
    # Pour chaque symbole, on collecte les splits (date, ratio) pour pouvoir
    # multiplier la quantité par le produit des splits postérieurs à la date d.
    splits_par_sym: dict[str, list[tuple[pd.Timestamp, float]]] = {}
    if "type_operation" in df_all.columns and "split_ratio" in df_all.columns:
        splits_df = df_all[df_all["type_operation"] == "SPLIT"].dropna(subset=["split_ratio"])
        for _, row in splits_df.iterrows():
            sym = row.get("symbole")
            if sym:
                splits_par_sym.setdefault(sym, []).append(
                    (pd.Timestamp(row["date_operation"]), float(row["split_ratio"]))
                )

    def _ajustement_split(sym: str, d: pd.Timestamp) -> float:
        """Produit des ratios de split postérieurs à d (pour aligner qty sur prix yfinance)."""
        splits = splits_par_sym.get(sym)
        if not splits:
            return 1.0
        facteur = 1.0
        for split_date, ratio in splits:
            if split_date > d:
                facteur *= ratio
        return facteur

    # ── Construction valeur quotidienne ───────────────────────────────────────
    dates_range = pd.date_range(d_debut_ts, d_fin_ts, freq="B")
    valeur_serie = pd.Series(0.0, index=dates_range)

    if not prix_histo.empty:
        # Pour chaque date, calculer : somme(quantite × cours × taux_change_eur)
        # On utilise df_all (historique complet) pour connaître la quantité détenue
        for d in dates_range:
            # État du portefeuille à la date d : dernière transaction ≤ d
            df_avant = df_all[df_all["date_operation"] <= d]
            if df_avant.empty:
                continue
            valeur_jour = 0.0
            for sym, ticker in ticker_map.items():
                # Quantité détenue à cette date
                df_sym = df_avant[df_avant.get("symbole", pd.Series()) == sym] if "symbole" in df_avant.columns else pd.DataFrame()
                if df_sym.empty:
                    continue
                if "quantite_apres_operation" in df_sym.columns:
                    df_sym_qty = df_sym.dropna(subset=["quantite_apres_operation"])
                    if df_sym_qty.empty:
                        continue
                    qty = float(df_sym_qty.iloc[-1]["quantite_apres_operation"])
                elif "quantite" in df_sym.columns:
                    qty = float(df_sym["quantite"].sum() or 0)
                else:
                    continue
                if pd.isna(qty) or qty <= 0:
                    continue
                # Ajuster la quantité pour les splits futurs (Saxo applique
                # les splits avec retard, yfinance donne des prix post-split)
                qty *= _ajustement_split(sym, d)
                if ticker in prix_histo.columns:
                    prix_d = prix_histo[ticker].asof(d)
                    if pd.notna(prix_d):
                        # Conversion en EUR si devise étrangère
                        devise = devise_map.get(sym, "EUR")
                        taux_eur = 1.0
                        if devise != "EUR" and devise in fx_histo:
                            taux_d = fx_histo[devise].asof(d)
                            if pd.notna(taux_d) and taux_d > 0:
                                taux_eur = float(taux_d)
                        valeur_jour += qty * float(prix_d) * taux_eur
            valeur_serie[d] = valeur_jour

            # Ajouter le cash (somme de tous les montant_eur jusqu'à cette date)
            df_cash = df_all[df_all["date_operation"] <= d]
            if not df_cash.empty and "montant_eur" in df_cash.columns:
                cash = float(df_cash["montant_eur"].sum())
                if cash > 0:
                    valeur_serie[d] += cash

    # Supprimer les zéros initiaux
    valeur_serie = valeur_serie[valeur_serie > 0]
    if valeur_serie.empty:
        return resultat_vide

    # ── Calcul TWR ─────────────────────────────────────────────────────────────
    # Puisque valeur_serie inclut le cash, les flux externes sont :
    # 1) DEPOT/RETRAIT (argent qui entre/sort du compte)
    # 2) ACHAT/VENTE sur instruments non valorisables (actifs non suivis par
    #    yfinance) → traités comme des flux externes car leur impact cash
    #    n'a pas de contrepartie dans la valorisation titres.
    symboles_valorises = {sym for sym, t in ticker_map.items()
                          if not prix_histo.empty and t in prix_histo.columns}
    flux_df = pd.DataFrame()
    if "type_operation" in df.columns:
        mask_dep_ret = df["type_operation"].isin(["DEPOT", "RETRAIT"])
        mask_non_val = (
            df["type_operation"].isin(["ACHAT", "VENTE", "DIVIDENDE"]) &
            ~df["symbole"].isin(symboles_valorises)
        ) if "symbole" in df.columns else pd.Series(False, index=df.index)
        flux_df = df[mask_dep_ret | mask_non_val]
    flux_dates = set(flux_df["date_operation"].dt.normalize().unique()) if not flux_df.empty else set()

    twr_cumule = pd.Series(0.0, index=valeur_serie.index)
    twr_facteur = 1.0
    v_avant = None

    for i, (d, v) in enumerate(valeur_serie.items()):
        if v_avant is None:
            v_avant = v
            continue

        # Flux du jour = DEPOT/RETRAIT (montant_eur : + pour DEPOT, - pour RETRAIT)
        flux_jour = 0.0
        if d in flux_dates:
            flux_du_jour = flux_df[flux_df["date_operation"].dt.normalize() == d]
            if "montant_eur" in flux_du_jour.columns:
                flux_jour = float(flux_du_jour["montant_eur"].sum())

        # Rendement de la sous-période (convention fin de journée)
        # r = (V_fin - Flux) / V_debut - 1  → neutralise les apports/retraits
        denominateur = v_avant
        if denominateur > 0:
            r_sous_periode = (v - flux_jour) / denominateur - 1
            twr_facteur *= (1 + r_sous_periode)

        twr_cumule[d] = round((twr_facteur - 1) * 100, 4)
        v_avant = v

    twr_total = round((twr_facteur - 1) * 100, 2)
    nb_jours = (d_fin - d_debut).days
    if nb_jours > 0 and twr_facteur > 0:
        twr_annualise = round(((twr_facteur ** (365 / nb_jours)) - 1) * 100, 2)
    else:
        twr_annualise = 0.0

    # ── Benchmarks ────────────────────────────────────────────────────────────
    benchmarks: dict[str, pd.Series] = {}
    bench_tickers = list(TICKERS_BENCHMARKS.values())

    try:
        bench_raw = yf.download(
            bench_tickers,
            start=d_debut_ts - timedelta(days=5),
            end=d_fin_ts + timedelta(days=1),
            auto_adjust=True,
            progress=False,
        )
        if not bench_raw.empty:
            if len(bench_tickers) == 1:
                bench_close = bench_raw[["Close"]].rename(columns={"Close": bench_tickers[0]})
            elif "Close" in bench_raw.columns:
                bench_close = bench_raw["Close"]
            else:
                bench_close = pd.DataFrame()

            for nom, ticker in TICKERS_BENCHMARKS.items():
                if ticker not in bench_close.columns:
                    continue
                serie = bench_close[ticker].dropna()
                serie = serie[serie.index >= d_debut_ts]
                if serie.empty:
                    continue
                base = float(serie.iloc[0])
                if base == 0:
                    continue
                # Normaliser base 0 (en %)
                serie_rebasee = ((serie / base) - 1) * 100
                serie_rebasee = serie_rebasee.rename(nom)
                benchmarks[nom] = serie_rebasee.round(4)
    except Exception:
        pass

    # ── Flux nets (dépôts - retraits) sur la période ───────────────────────
    flux_net = 0.0
    if not flux_df.empty and "montant_eur" in flux_df.columns:
        flux_net = float(flux_df["montant_eur"].sum())

    return {
        "twr_cumule": twr_cumule,
        "twr_total": twr_total,
        "twr_annualise": twr_annualise,
        "valeur_quotidienne": valeur_serie,
        "benchmarks": benchmarks,
        "flux_net": flux_net,
    }
