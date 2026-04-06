"""
cotations.py — Récupération des cours de marché en temps réel via yfinance.

Convertit les symboles Saxo Bank (ex. MSFT:xnas) en tickers yfinance (MSFT)
et récupère les prix actuels pour valoriser le portefeuille.
"""
from __future__ import annotations

import pandas as pd
import yfinance as yf

SUFFIXES_YFINANCE: dict[str, str] = {
    "xnas": "",    # NASDAQ
    "xnys": "",    # NYSE
    "xpar": ".PA", # Euronext Paris
    "xetr": ".DE", # Xetra (Frankfurt)
    "xams": ".AS", # Euronext Amsterdam
    "xbru": ".BR", # Euronext Brussels
    "xlon": "",    # London Stock Exchange
    "xmil": ".MI", # Borsa Italiana
}


def symbole_vers_ticker(symbole_saxo: str) -> str | None:
    """Convertit un symbole Saxo (ex. 'MSFT:xnas') en ticker yfinance ('MSFT')."""
    if not isinstance(symbole_saxo, str) or ":" not in symbole_saxo:
        return symbole_saxo if isinstance(symbole_saxo, str) else None
    parts = symbole_saxo.split(":")
    sym = parts[0]
    place = parts[1].lower() if len(parts) > 1 else ""
    suffixe = SUFFIXES_YFINANCE.get(place, "")
    return sym + suffixe


def recuperer_cours(positions: pd.DataFrame) -> pd.DataFrame:
    """
    Récupère les cours actuels pour toutes les positions ouvertes.

    Paramètres
    ----------
    positions : DataFrame avec colonnes 'symbole', 'devise_instrument', 'position_soldee'

    Retourne
    --------
    DataFrame avec colonnes :
        symbole            — symbole Saxo original
        ticker_yf          — ticker yfinance utilisé
        prix_actuel        — dernier prix dans la devise de l'instrument
        devise_prix        — devise du prix (EUR ou USD)
        prix_actuel_eur    — prix converti en EUR
        taux_change_eur    — taux de change utilisé (1.0 si déjà EUR)
    """
    ouvertes = positions[~positions["position_soldee"]].copy()
    if ouvertes.empty:
        return pd.DataFrame(columns=["symbole", "ticker_yf", "prix_actuel",
                                     "devise_prix", "prix_actuel_eur", "taux_change_eur"])

    # Construire le mapping symbole → ticker
    tickers: dict[str, str] = {}
    for _, row in ouvertes.iterrows():
        t = symbole_vers_ticker(row["symbole"])
        if t:
            tickers[row["symbole"]] = t

    # Paires FX pour conversion USD → EUR
    devises_etrangeres = set(
        ouvertes[ouvertes["devise_instrument"] != "EUR"]["devise_instrument"].unique()
    )
    paires_fx: dict[str, str] = {d: f"{d}EUR=X" for d in devises_etrangeres if d}

    tous_tickers = list(set(tickers.values()) | set(paires_fx.values()))
    if not tous_tickers:
        return pd.DataFrame(columns=["symbole", "ticker_yf", "prix_actuel",
                                     "devise_prix", "prix_actuel_eur", "taux_change_eur"])

    # Téléchargement
    data = yf.download(tous_tickers, period="2d", auto_adjust=True, progress=False,
                       group_by="ticker")

    cours_map: dict[str, float] = {}
    if not data.empty:
        if len(tous_tickers) == 1:
            t = tous_tickers[0]
            close = data["Close"] if "Close" in data.columns else data
            serie = close.dropna()
            if not serie.empty:
                cours_map[t] = float(serie.iloc[-1])
        else:
            for t in tous_tickers:
                try:
                    if t in data.columns.get_level_values(0):
                        serie = data[t]["Close"].dropna()
                    elif "Close" in data.columns and t in data["Close"].columns:
                        serie = data["Close"][t].dropna()
                    else:
                        continue
                    if not serie.empty:
                        cours_map[t] = float(serie.iloc[-1])
                except Exception:
                    continue

    taux_fx: dict[str, float] = {"EUR": 1.0}
    for devise, paire in paires_fx.items():
        taux_fx[devise] = cours_map.get(paire, 1.0) or 1.0

    lignes = []
    for _, row in ouvertes.iterrows():
        sym = row["symbole"]
        ticker = tickers.get(sym)
        if not ticker:
            continue
        prix = cours_map.get(ticker)
        if prix is None:
            continue
        devise = row.get("devise_instrument", "EUR")
        taux = taux_fx.get(devise, 1.0) or 1.0
        prix_eur = round(float(prix) * taux, 4)
        lignes.append({
            "symbole":         sym,
            "ticker_yf":       ticker,
            "prix_actuel":     round(float(prix), 4),
            "devise_prix":     devise,
            "prix_actuel_eur": prix_eur,
            "taux_change_eur": taux,
        })

    return pd.DataFrame(lignes)


def valoriser_positions(positions: pd.DataFrame) -> pd.DataFrame:
    """
    Enrichit les positions avec les cours actuels et calcule la valorisation.

    Colonnes ajoutées :
        prix_actuel_eur    — cours actuel en EUR
        valeur_marche_eur  — quantité × prix actuel en EUR
        pv_latente_eur     — plus-value latente (valeur marché - coût investi)
        pv_latente_pct     — plus-value latente en %
        taux_change_eur    — taux de change utilisé
    """
    pos = positions.copy()
    cours = recuperer_cours(pos)

    cours_map: dict[str, dict] = {}
    for _, row in cours.iterrows():
        cours_map[row["symbole"]] = row.to_dict()

    for idx, row in pos.iterrows():
        if row.get("position_soldee", False):
            continue
        c = cours_map.get(row["symbole"])
        if c is None:
            continue
        prix_eur = c["prix_actuel_eur"]
        val_marche = round(float(row["quantite"]) * prix_eur, 2)
        cout = float(row.get("cout_investi_eur", 0) or 0)
        pv_latente = round(val_marche - cout, 2)
        pv_pct = round(pv_latente / cout * 100, 2) if cout else 0.0

        pos.at[idx, "prix_actuel"]     = c["prix_actuel"]
        pos.at[idx, "prix_actuel_eur"] = prix_eur
        pos.at[idx, "valeur_marche_eur"] = val_marche
        pos.at[idx, "pv_latente_eur"]  = pv_latente
        pos.at[idx, "pv_latente_pct"]  = pv_pct
        pos.at[idx, "taux_change_eur"] = c["taux_change_eur"]

    return pos
