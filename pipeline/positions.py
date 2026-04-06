"""
positions.py — Calcul des positions et du PRU par méthode CUMP
(Coût Unitaire Moyen Pondéré), standard fiscal français.

Logique CUMP :
  - ACHAT  : PRU_nouveau = (qtité_avant × PRU_avant + coût_EUR_achat) / (qtité_avant + qtité_achetée)
  - VENTE  : PRU inchangé, quantité réduite, plus-value réalisée calculée
  - Coût EUR achat = abs(montant_eur) + abs(couts_conversion)
    (la commission nette Saxo est souvent = 0 grâce au crédit automatique ;
     la TTF est déjà incluse dans montant_eur)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DOSSIER_DATA = Path(__file__).parent.parent / "data"


def calculer_cump(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Parcourt les transactions enrichies dans l'ordre chronologique et
    reconstitue les positions par (compte_id, isin).

    Paramètres
    ----------
    df : DataFrame issu de nettoyage.assembler_transactions_enrichies()

    Retourne
    --------
    positions    : état courant du portefeuille (une ligne par position)
    historique   : toutes les transactions avec snapshot de position après chaque trade
    """
    # Trier : d'abord par date, puis SPLIT/ACHAT avant VENTE (ordre stable)
    def _tri_op(t: str) -> int:
        return {"SPLIT": 0, "ACHAT": 1, "VENTE": 2}.get(t, 3)

    df = df.copy()
    df["_tri_op"] = df.get("type_operation", pd.Series(dtype=str)).map(_tri_op).fillna(3)
    df = df.sort_values(["date_operation", "_tri_op"]).reset_index(drop=True)

    # État courant par (compte_id, isin)
    etat: dict[tuple, dict] = {}
    lignes_historique: list[dict] = []

    for _, row in df.iterrows():
        type_op = row.get("type_operation", "AUTRE")
        isin = row.get("isin")
        compte_id = row.get("compte_id")

        if type_op not in ("ACHAT", "VENTE", "SPLIT"):
            lignes_historique.append(row.to_dict())
            continue

        if not isin or pd.isna(isin):
            lignes_historique.append(row.to_dict())
            continue

        cle = (compte_id, isin)

        if cle not in etat:
            etat[cle] = {
                "quantite": 0.0,
                "pru_eur": 0.0,
                "cout_investi_eur": 0.0,
                "pru_devise": 0.0,
                "cout_investi_devise": 0.0,
                "pv_realisee_eur": 0.0,
                "nb_achats": 0,
                "nb_ventes": 0,
                "premiere_operation": row.get("date_operation"),
                "derniere_operation": row.get("date_operation"),
                # métadonnées
                "type_compte": row.get("type_compte", "CTO"),
                "instrument": row.get("instrument", ""),
                "symbole": row.get("symbole", ""),
                "devise_instrument": row.get("devise_instrument", "EUR"),
                "type_instrument": row.get("type_instrument", ""),
                "place_bourse": row.get("place_bourse", ""),
            }

        pos = etat[cle]
        pos["derniere_operation"] = row.get("date_operation")

        if type_op == "SPLIT":
            ratio = float(row.get("split_ratio", 1.0) or 1.0)
            if ratio and ratio != 1.0:
                pos["quantite"] = round(pos["quantite"] * ratio, 6)
                if ratio != 0:
                    pos["pru_eur"] = round(pos["pru_eur"] / ratio, 6)
                    pos["pru_devise"] = round(pos["pru_devise"] / ratio, 6)
                    pos["cout_investi_eur"] = round(pos["quantite"] * pos["pru_eur"], 4)

        elif type_op == "ACHAT":
            quantite = abs(float(row.get("quantite") or 0))
            cout_eur = abs(float(row.get("cout_total_eur") or 0))
            cours = float(row.get("cours") or 0)
            qty_achetee = quantite

            if qty_achetee > 0 and cout_eur > 0:
                nouveau_cout = pos["cout_investi_eur"] + cout_eur
                nouvelle_qty = pos["quantite"] + qty_achetee
                pos["pru_eur"] = round(nouveau_cout / nouvelle_qty, 6) if nouvelle_qty else 0.0
                pos["cout_investi_eur"] = round(nouveau_cout, 4)
                pos["quantite"] = round(nouvelle_qty, 6)
                # PRU en devise (approximatif)
                if cours:
                    nouveau_cout_devise = pos["cout_investi_devise"] + qty_achetee * cours
                    pos["pru_devise"] = round(nouveau_cout_devise / nouvelle_qty, 6)
                    pos["cout_investi_devise"] = round(nouveau_cout_devise, 4)
                pos["nb_achats"] += 1

        elif type_op == "VENTE":
            quantite = abs(float(row.get("quantite") or 0))
            montant_eur = float(row.get("montant_eur") or 0)
            qty_vendue = quantite

            if qty_vendue > 0:
                produit_net = abs(montant_eur)
                pv = produit_net - qty_vendue * pos["pru_eur"]
                pos["pv_realisee_eur"] = round(pos["pv_realisee_eur"] + pv, 4)
                pos["quantite"] = round(pos["quantite"] - qty_vendue, 6)
                # Le PRU ne change pas à la vente (CUMP)
                if pos["quantite"] > 0:
                    pos["cout_investi_eur"] = round(pos["quantite"] * pos["pru_eur"], 4)
                    pos["cout_investi_devise"] = round(pos["quantite"] * pos["pru_devise"], 4)
                else:
                    pos["cout_investi_eur"] = 0.0
                    pos["cout_investi_devise"] = 0.0
                pos["nb_ventes"] += 1

        # Snapshot de l'état pour l'historique
        snap = row.to_dict()
        snap.update({
            "quantite_apres_operation": round(pos["quantite"], 6),
            "pru_apres_operation": round(pos["pru_eur"], 6),
            "cout_investi_apres": round(pos["cout_investi_eur"], 4),
        })
        lignes_historique.append(snap)

    # Construction du DataFrame positions
    lignes_pos = []
    for (compte_id, isin), pos in etat.items():
        solde = abs(pos["quantite"]) < 1e-6
        lignes_pos.append({
            "compte_id":           compte_id,
            "isin":                isin,
            "type_compte":         pos["type_compte"],
            "instrument":          pos["instrument"],
            "symbole":             pos["symbole"],
            "devise_instrument":   pos["devise_instrument"],
            "type_instrument":     pos["type_instrument"],
            "place_bourse":        pos["place_bourse"],
            "quantite":            round(pos["quantite"], 6),
            "pru_eur":             round(pos["pru_eur"], 4),
            "cout_investi_eur":    round(pos["cout_investi_eur"], 2),
            "pru_devise":          round(pos["pru_devise"], 4),
            "cout_investi_devise": round(pos["cout_investi_devise"], 2),
            "pv_realisee_eur":     round(pos["pv_realisee_eur"], 2),
            "nb_achats":           pos["nb_achats"],
            "nb_ventes":           pos["nb_ventes"],
            "premiere_operation":  pos["premiere_operation"],
            "derniere_operation":  pos["derniere_operation"],
            "position_soldee":     solde,
        })

    positions = pd.DataFrame(lignes_pos)
    historique = pd.DataFrame(lignes_historique)

    return positions, historique


def exporter(positions: pd.DataFrame, historique: pd.DataFrame, inclure_soldees: bool) -> None:
    """
    Exporte les DataFrames :
      - positions.csv          : état courant (local, dans data/)
      - transactions_enrichies.csv : historique complet (Google Drive)
    """
    import streamlit as st
    from pipeline.gdrive import uploader_csv

    DOSSIER_DATA.mkdir(parents=True, exist_ok=True)

    pos_export = positions if inclure_soldees else positions[~positions["position_soldee"]]
    chemin_pos = DOSSIER_DATA / "positions.csv"
    pos_export.to_csv(chemin_pos, index=False, encoding="utf-8-sig")
    print(f"  ✓ positions.csv           → {chemin_pos}")

    file_id = st.secrets["gdrive"]["transactions_enrichies_file_id"]
    uploader_csv(file_id, historique)
    print(f"  ✓ transactions_enrichies  → Google Drive ({file_id})")


def afficher_resume(positions: pd.DataFrame, inclure_soldees: bool) -> None:
    """Affiche un résumé lisible du portefeuille dans le terminal."""
    pos = positions if inclure_soldees else positions[~positions["position_soldee"]]

    if pos.empty:
        print("\n  Aucune position à afficher.")
        return

    titre = "TOUTES POSITIONS (soldées incluses)" if inclure_soldees else "POSITIONS OUVERTES"
    print(f"\n  PORTEFEUILLE — {titre}")
    print("  " + "─" * 88)

    for compte in sorted(pos["type_compte"].unique()):
        sous = pos[pos["type_compte"] == compte]
        print(f"\n  ▶  Compte {compte}")
        print(f"  {'Instrument':<30} {'Symb.':<12} {'Qté':>8} {'PRU (€)':>12} {'Investi (€)':>13} {'PV réalisée (€)':>16}")
        print("  " + "─" * 88)
        for _, r in sous.iterrows():
            suffix = " [soldée]" if r["position_soldee"] else ""
            print(
                f"  {r['instrument']:<30} {r['symbole']:<12} {r['quantite']:>8.4g} "
                f"{r['pru_eur']:>12.2f} {r['cout_investi_eur']:>13.2f} "
                f"{r['pv_realisee_eur']:>+16.2f}{suffix}"
            )

    total_investi = pos["cout_investi_eur"].sum()
    pv_global = pos["pv_realisee_eur"].sum()
    print("\n  " + "═" * 88)
    print(
        f"  TOTAL PORTEFEUILLE — Investi : {total_investi:>10.2f} € | "
        f"PV réalisées : {pv_global:>+10.2f} €"
    )
