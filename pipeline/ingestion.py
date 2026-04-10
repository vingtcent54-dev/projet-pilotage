"""
ingestion.py — Lecture et agrégation de tous les fichiers Saxo Bank xlsx.
Produit trois DataFrames bruts : Transactions, Opérations, Bookings.

Source des fichiers : Google Drive (via pipeline.gdrive).
"""

import unicodedata
from io import BytesIO

import pandas as pd

from pipeline.gdrive import lister_fichiers_saxo, telecharger_fichier


def _trouver_onglet(noms_onglets: list[str], mot_cle: str) -> str | None:
    """Trouve un onglet par mot-clé, insensible aux accents et à la casse."""
    for nom in noms_onglets:
        normalise = unicodedata.normalize("NFD", nom)
        normalise = "".join(c for c in normalise if unicodedata.category(c) != "Mn").lower()
        if mot_cle in normalise:
            return nom
    return None


def valider_fichier_saxo(contenu: bytes, nom: str) -> list[str]:
    """
    Valide un fichier xlsx Saxo Bank avant upload.
    Retourne une liste d'erreurs (vide = fichier valide).
    """
    erreurs = []

    # Vérifier le pattern du nom
    if not nom.startswith("Transactions_") or not nom.endswith(".xlsx"):
        erreurs.append("Le nom doit suivre le format `Transactions_*.xlsx`.")

    # Vérifier que le fichier est un xlsx lisible
    try:
        xl = pd.ExcelFile(BytesIO(contenu))
    except Exception:
        erreurs.append("Fichier illisible — ce n'est pas un fichier Excel valide.")
        return erreurs

    noms_onglets = xl.sheet_names

    # Vérifier la présence des 3 onglets requis
    onglet_t = _trouver_onglet(noms_onglets, "transaction")
    onglet_o = _trouver_onglet(noms_onglets, "op")
    onglet_b = _trouver_onglet(noms_onglets, "booking")

    manquants = []
    if not onglet_t:
        manquants.append("Transactions")
    if not onglet_o:
        manquants.append("Opérations")
    if not onglet_b:
        manquants.append("Bookings")

    if manquants:
        erreurs.append(f"Onglet(s) manquant(s) : {', '.join(manquants)}.")

    # Vérifier que les onglets présents ne sont pas vides
    for label, onglet in [("Transactions", onglet_t), ("Opérations", onglet_o), ("Bookings", onglet_b)]:
        if onglet:
            df = xl.parse(onglet)
            if df.empty:
                erreurs.append(f"L'onglet « {label} » est vide.")

    return erreurs


def charger_tous_les_fichiers() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Charge et concatène tous les fichiers Transactions_*.xlsx depuis Google Drive.

    Retourne :
        (df_transactions, df_operations, df_bookings)
    """
    fichiers_drive = lister_fichiers_saxo()
    if not fichiers_drive:
        raise FileNotFoundError("Aucun fichier Saxo trouvé dans le dossier Google Drive.")

    print(f"  {len(fichiers_drive)} fichier(s) trouvé(s) sur Drive.")

    transactions, operations, bookings = [], [], []

    for fichier in fichiers_drive:
        nom = fichier["name"]
        contenu: BytesIO = telecharger_fichier(fichier["id"])
        xl = pd.ExcelFile(contenu)
        noms_onglets = xl.sheet_names

        onglet_t = _trouver_onglet(noms_onglets, "transaction")
        onglet_o = _trouver_onglet(noms_onglets, "op")
        onglet_b = _trouver_onglet(noms_onglets, "booking")

        if onglet_t:
            transactions.append(xl.parse(onglet_t))
        if onglet_o:
            operations.append(xl.parse(onglet_o))
        if onglet_b:
            bookings.append(xl.parse(onglet_b))

        print(f"    ✓ {nom}")

    df_t = pd.concat(transactions, ignore_index=True) if transactions else pd.DataFrame()
    df_o = pd.concat(operations, ignore_index=True) if operations else pd.DataFrame()
    df_b = pd.concat(bookings, ignore_index=True) if bookings else pd.DataFrame()

    # Dédoublonnage sur bk_record_id (sécurité en cas de chevauchement de fichiers)
    # NB : les lignes sans bk_record_id (NaN) sont conservées — ce sont des
    # transferts entrants ou opérations spéciales sans identifiant Saxo.
    df_t, df_o, df_b = (
        _dedup_safe(df, label)
        for df, label in [(df_t, "Transactions"), (df_o, "Opérations"), (df_b, "Bookings")]
    )

    print(
        f"\n  Lignes agrégées — Transactions : {len(df_t)} | "
        f"Opérations : {len(df_o)} | Bookings : {len(df_b)}"
    )
    return df_t, df_o, df_b


def _dedup_safe(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Dédoublonne sur bk_record_id en préservant les lignes sans identifiant (NaN)."""
    if df.empty:
        return df

    col_id = next(
        (c for c in df.columns if "bk" in c.lower() and "record" in c.lower()),
        None,
    )
    if not col_id:
        return df

    avant = len(df)
    mask_nan = df[col_id].isna()
    df_avec_id = df[~mask_nan].drop_duplicates(subset=[col_id], keep="first")
    df_result = pd.concat([df_avec_id, df[mask_nan]], ignore_index=True)
    apres = len(df_result)

    if avant != apres:
        print(f"    ⚠ {label} : {avant - apres} doublon(s) supprimé(s).")
    if mask_nan.sum() > 0:
        print(f"    ℹ {label} : {mask_nan.sum()} ligne(s) sans bk_record_id conservée(s).")

    return df_result
