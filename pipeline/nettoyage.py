"""
nettoyage.py — Normalisation des colonnes, typage, identification des types
d'opération, jointure des frais (commissions, TTF, conversion) sur les transactions.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

# ── Mappings de colonnes par onglet ───────────────────────────────────────────

COLS_TRANSACTIONS = {
    "date_d_operation":              "date_operation",
    "date_de_valeur":                "date_valeur",
    "compte_id":                     "compte_id",
    "bk_record_id":                  "bk_record_id",
    "type_de_transaction":           "type_transaction",
    "evenement":                     "evenement",
    "montant_comptabilise":          "montant_eur",
    "quantite":                      "quantite_transaction",
    "taux_de_change":                "taux_change",
    "couts_de_conversion":           "couts_conversion",
    "cout_total":                    "cout_total_frais",
    "b_p_realises":                  "bp_realises",
    "instrument":                    "instrument",
    "symbole":                       "symbole",
    "code_isin_de_l_instrument":     "isin",
    "devise_de_l_instrument":        "devise_instrument",
    "type":                          "type_instrument",
    "description_de_la_place_boursiere": "place_bourse",
}

COLS_OPERATIONS = {
    "compte_id":       "compte_id",
    "bk_record_id":    "bk_record_id",
    "evenement":       "evenement",
    "traded_quantity": "quantite",
    "cours":           "cours",
    "valeur_negociee": "valeur_negociee",
    "instrument":      "instrument",
    "symbole":         "symbole",
    "isin":            "isin",
    "ouv_cloture":     "ouv_cloture",
}

COLS_BOOKINGS = {
    "compte_id":             "compte_id",
    "bk_record_id":          "bk_record_id",
    "amount_type":           "type_montant",
    "montant_comptabilise":  "montant",       # "Montant comptabilisé"
    "couts_de_conversion":   "couts_conversion",  # "Coûts de conversion"
}


# ── Normalisation des noms de colonnes ────────────────────────────────────────

def normaliser_colonne(col: str) -> str:
    """
    Transforme un nom de colonne brut Saxo en identifiant Python propre.
    Ex: 'Bk\xa0Record\xa0Id'  → 'bk_record_id'
        'Montant comptabilisé'  → 'montant_comptabilise'
        "Date d'opération"      → 'date_d_operation'
    """
    # Remplacer espaces insécables, apostrophes (ASCII et typographique), espaces
    col = re.sub(r"[\s\xa0\u2019']+", "_", col)
    # Supprimer les accents
    col = unicodedata.normalize("NFD", col)
    col = "".join(c for c in col if unicodedata.category(c) != "Mn")
    # Minuscules, garder uniquement alphanum + _
    col = col.lower()
    col = re.sub(r"[^a-z0-9_]", "", col)
    col = re.sub(r"_+", "_", col).strip("_")
    return col


def renommer_colonnes(df: pd.DataFrame) -> pd.DataFrame:
    """Renomme toutes les colonnes d'un DataFrame via normaliser_colonne."""
    return df.rename(columns={c: normaliser_colonne(c) for c in df.columns})


def _selectionner_colonnes(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Sélectionne et renomme les colonnes selon le mapping fourni."""
    df = renommer_colonnes(df)
    cols = {k: v for k, v in mapping.items() if k in df.columns}
    df = df[[c for c in cols]].rename(columns=cols)
    return df


# ── Identification du type d'opération ───────────────────────────────────────

def _identifier_type_operation(evenement: str) -> str:
    """Déduit le type d'opération depuis le champ événement Saxo."""
    if not isinstance(evenement, str):
        return "AUTRE"
    evt_lower = unicodedata.normalize("NFD", evenement.lower())
    evt_lower = "".join(c for c in evt_lower if unicodedata.category(c) != "Mn")
    if any(k in evt_lower for k in ("division", "split")):
        return "SPLIT"
    if any(k in evt_lower for k in ("acheter", "achat")):
        return "ACHAT"
    if any(k in evt_lower for k in ("vendre", "vente", "ceder")):
        return "VENTE"
    if any(k in evt_lower for k in ("depot", "depots", "dep")):
        return "DEPOT"
    if "retrait" in evt_lower:
        return "RETRAIT"
    if any(k in evt_lower for k in ("dividende", "dividend")):
        return "DIVIDENDE"
    if any(k in evt_lower for k in ("interet", "coupon")):
        return "INTERET"
    return "AUTRE"


# ── Préparation des trois onglets ─────────────────────────────────────────────

def preparer_transactions(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Nettoie l'onglet Transactions."""
    df = _selectionner_colonnes(df_raw, COLS_TRANSACTIONS)
    if "date_operation" in df.columns:
        df["date_operation"] = pd.to_datetime(df["date_operation"], errors="coerce")
    if "date_valeur" in df.columns:
        df["date_valeur"] = pd.to_datetime(df["date_valeur"], errors="coerce")
    if "montant_eur" in df.columns:
        df["montant_eur"] = pd.to_numeric(df["montant_eur"], errors="coerce")
    if "couts_conversion" in df.columns:
        df["couts_conversion"] = pd.to_numeric(df["couts_conversion"], errors="coerce").fillna(0.0)
    if "evenement" in df.columns:
        df["type_operation"] = df["evenement"].apply(_identifier_type_operation)
    return df


def preparer_operations(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Nettoie l'onglet Opérations."""
    df = _selectionner_colonnes(df_raw, COLS_OPERATIONS)
    if "quantite" in df.columns:
        df["quantite"] = pd.to_numeric(df["quantite"], errors="coerce")
    if "cours" in df.columns:
        df["cours"] = pd.to_numeric(df["cours"], errors="coerce")
    if "valeur_negociee" in df.columns:
        df["valeur_negociee"] = pd.to_numeric(df["valeur_negociee"], errors="coerce")
    if "bk_record_id" in df.columns:
        df["bk_record_id"] = pd.to_numeric(df["bk_record_id"], errors="coerce")
    return df


def preparer_bookings(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Nettoie l'onglet Bookings."""
    df = _selectionner_colonnes(df_raw, COLS_BOOKINGS)
    if "montant" in df.columns:
        df["montant"] = pd.to_numeric(df["montant"], errors="coerce")
    return df


# ── Extraction et agrégation des frais depuis Bookings ───────────────────────

def _extraire_frais(df_b: pd.DataFrame) -> pd.DataFrame:
    """
    Agrège les frais par bk_record_id depuis l'onglet Bookings :
      - commission_brute  : montant brut des commissions (Amount Type = "Commission")
      - commission_credit : crédit de commission Saxo (Amount Type = "Crédit de commission client")
      - commission_nette  : nette = brute + crédit (souvent = 0 dans les exports Saxo)
      - ttf               : Taxe sur Transactions Financières (actions françaises)
      - conversion        : coûts de conversion de devise
    """
    if df_b.empty or "type_montant" not in df_b.columns:
        return pd.DataFrame(columns=["bk_record_id", "commission_brute", "commission_credit",
                                     "commission_nette", "ttf", "conversion_bookings"])

    df = df_b.copy()

    # Normaliser type_montant pour comparaison
    def _norm(x: str) -> str:
        if not isinstance(x, str):
            return ""
        n = unicodedata.normalize("NFD", x.lower())
        return "".join(c for c in n if unicodedata.category(c) != "Mn")

    df["_type_norm"] = df["type_montant"].apply(_norm)

    mask_commission = df["_type_norm"].str.contains("commission", na=False)
    mask_credit = df["_type_norm"].str.contains("credit|crédit", na=False)
    mask_ttf = df["_type_norm"].str.contains("taxe", na=False)

    # La conversion est dans une colonne séparée ou ligne amount_type
    mask_conv = df["_type_norm"].str.contains("conversion", na=False)

    def _agg(mask, fillna=0.0):
        return (
            df[mask]
            .groupby("bk_record_id")["montant"]
            .apply(lambda x: x.dropna().sum())
        )

    comm_brute = _agg(mask_commission & ~mask_credit)
    comm_credit = _agg(mask_credit)
    ttf = _agg(mask_ttf)
    conversion = _agg(mask_conv)

    frais = pd.DataFrame({"bk_record_id": df["bk_record_id"].dropna().unique()})
    frais = frais.set_index("bk_record_id")
    frais["commission_brute"] = comm_brute
    frais["commission_credit"] = comm_credit
    frais["ttf"] = ttf
    frais["conversion_bookings"] = conversion
    frais = frais.fillna(0.0)
    frais["commission_nette"] = frais["commission_brute"] + frais["commission_credit"]
    return frais.reset_index()


# ── Enrichissement des splits ─────────────────────────────────────────────────

def _enrichir_splits(df: pd.DataFrame, df_o_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pour chaque transaction SPLIT, retrouve le ratio dans les Opérations brutes.

    Saxo enregistre un split via 2 opérations (sans bk_record_id) :
    - Traded Quantity < 0 → ancienne quantité (retirée)
    - Traded Quantity > 0 → nouvelle quantité (ajoutée)
    Ratio = nouvelle / ancienne.
    """
    if df_o_raw is None or df_o_raw.empty:
        return df

    df_o = renommer_colonnes(df_o_raw.copy())
    if "traded_quantity" not in df_o.columns:
        return df

    df_o["traded_quantity"] = pd.to_numeric(df_o["traded_quantity"], errors="coerce")

    splits = df[df["type_operation"] == "SPLIT"].copy()
    if splits.empty:
        return df

    df = df.copy()
    df["split_ratio"] = 1.0

    isin_col = next((c for c in ["isin", "code_isin_de_l_instrument"] if c in df_o.columns), None)
    evt_col = next((c for c in ["evenement", "event"] if c in df_o.columns), None)

    for _, row in splits.iterrows():
        isin = row.get("isin")
        if not isin or not isin_col:
            continue

        ops_split = df_o[df_o[isin_col] == isin].copy()
        if evt_col:
            ops_split = ops_split[
                ops_split[evt_col].str.lower().str.contains("split|division", na=False)
            ]

        qty_vendue = ops_split[ops_split["traded_quantity"] < 0]["traded_quantity"]
        qty_achetee = ops_split[ops_split["traded_quantity"] > 0]["traded_quantity"]

        if qty_vendue.empty or qty_achetee.empty:
            continue

        ratio = abs(qty_achetee.sum()) / abs(qty_vendue.sum())
        df.loc[
            (df["type_operation"] == "SPLIT") & (df["isin"] == isin),
            "split_ratio",
        ] = ratio

    return df


# ── Assemblage final ──────────────────────────────────────────────────────────

def assembler_transactions_enrichies(
    df_t: pd.DataFrame,
    df_o: pd.DataFrame,
    df_b: pd.DataFrame,
    df_o_raw: pd.DataFrame,
) -> pd.DataFrame:
    """
    Joint les trois onglets pour produire un DataFrame unifié avec :
      - quantite   : nombre de titres échangés (depuis Opérations)
      - cours      : cours d'exécution (depuis Opérations)
      - frais ventilés : commission, TTF, conversion (depuis Bookings)
      - cout_total_eur : coût EUR complet pour le calcul du CUMP
    """
    # Joindre Opérations → Transactions sur bk_record_id
    # On exclut les bk_record_id NaN côté df_o pour éviter le produit cartésien
    # (les OST/splits n'ont pas de bk_record_id et sont traités séparément)
    cols_ops = ["bk_record_id", "quantite", "cours", "valeur_negociee", "isin"]
    cols_ops = [c for c in cols_ops if c in df_o.columns]
    df_o_avec_id = df_o[cols_ops][df_o["bk_record_id"].notna()]
    df = df_t.merge(df_o_avec_id, on="bk_record_id", how="left", suffixes=("", "_ops"))

    # Compléter isin depuis opérations si absent
    if "isin" not in df.columns and "isin_ops" in df.columns:
        df["isin"] = df["isin_ops"]
    elif "isin_ops" in df.columns:
        df["isin"] = df["isin"].fillna(df["isin_ops"])
        df.drop(columns=["isin_ops"], inplace=True, errors="ignore")

    # Joindre les frais depuis Bookings
    frais = _extraire_frais(df_b)
    if not frais.empty:
        df = df.merge(frais, on="bk_record_id", how="left")
        for col in ["commission_brute", "commission_credit", "commission_nette", "ttf", "conversion_bookings"]:
            if col in df.columns:
                df[col] = df[col].fillna(0.0)

    # Essai de récupération quantité / cours depuis l'événement si manquant
    if "quantite" in df.columns and df["quantite"].isna().any():
        pattern = r"(?:Acheter|Vendre|acheter|vendre)\s+(\d+(?:[.,]\d+)?)\s+@\s+(\d+(?:[.,]\d+)?)"
        parsed = df.loc[df["quantite"].isna(), "evenement"].str.extract(pattern)
        if not parsed.empty:
            qty_parsed = pd.to_numeric(
                parsed[0].str.replace(",", "."), errors="coerce"
            )
            cours_parsed = pd.to_numeric(
                parsed[1].str.replace(",", "."), errors="coerce"
            )
            df.loc[df["quantite"].isna(), "quantite"] = qty_parsed.values
            if "cours" in df.columns:
                df.loc[df["cours"].isna(), "cours"] = cours_parsed.values

    # Coût total EUR pour CUMP : montant_eur + couts_conversion
    df["montant_eur"] = pd.to_numeric(df.get("montant_eur"), errors="coerce").fillna(0.0)
    df["couts_conversion"] = pd.to_numeric(df.get("couts_conversion"), errors="coerce").fillna(0.0)

    # Saxo quirk : pour les DEPÔTs/RETRAITs Cash, le montant est parfois dans
    # quantite_transaction (colonne "Quantité" de l'export) au lieu de montant_eur
    if "quantite_transaction" in df.columns and "type_instrument" in df.columns:
        qt = pd.to_numeric(df["quantite_transaction"], errors="coerce").fillna(0.0)
        fix_mask = (df["montant_eur"] == 0) & (df["type_instrument"] == "Cash") & (qt != 0)
        df.loc[fix_mask, "montant_eur"] = qt[fix_mask]

    df["cout_total_eur"] = df["montant_eur"] + df["couts_conversion"]

    # Enrichissement splits
    df = _enrichir_splits(df, df_o_raw)

    # Détection type de compte
    def _detecter_compte(compte_id: str) -> str:
        if not isinstance(compte_id, str):
            compte_id = str(compte_id) if compte_id else ""
        if "PME" in compte_id:
            return "PEA-PME"
        if "PEA" in compte_id:
            return "PEA"
        return "CTO"

    if "compte_id" in df.columns:
        df["type_compte"] = df["compte_id"].apply(_detecter_compte)

    return df
