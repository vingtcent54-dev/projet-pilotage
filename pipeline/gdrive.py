"""
gdrive.py — Connexion Google Drive et téléchargement/upload des fichiers.
Lit les credentials depuis st.secrets (Streamlit Community Cloud) ou
depuis un fichier .streamlit/secrets.toml en local.
"""

import io
from typing import Generator

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

SCOPES = ["https://www.googleapis.com/auth/drive"]


@st.cache_resource(show_spinner=False)
def _service():
    """Construit et met en cache le service Drive (une seule fois par session)."""
    creds_dict = dict(st.secrets["gdrive_credentials"])
    # Streamlit stocke les \n littéraux dans les secrets — on les restaure
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    credentials = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=SCOPES
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def lister_fichiers_saxo() -> list[dict]:
    """
    Retourne la liste des fichiers Transactions_*.xlsx dans le dossier Drive.
    Chaque entrée : {"id": "...", "name": "Transactions_...xlsx"}
    """
    folder_id = st.secrets["gdrive"]["folder_id"]
    service = _service()
    query = (
        f"'{folder_id}' in parents"
        " and name contains 'Transactions_'"
        " and name contains '.xlsx'"
        " and trashed = false"
    )
    result = (
        service.files()
        .list(q=query, fields="files(id, name)", orderBy="name")
        .execute()
    )
    return result.get("files", [])


def telecharger_fichier(file_id: str) -> io.BytesIO:
    """Télécharge un fichier Drive et retourne un objet BytesIO (en mémoire)."""
    service = _service()
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buffer.seek(0)
    return buffer


def uploader_csv(file_id: str, df: pd.DataFrame) -> None:
    """Met à jour le contenu d'un fichier CSV existant sur Drive."""
    service = _service()
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False, encoding="utf-8-sig")
    buffer.seek(0)
    media = MediaIoBaseUpload(buffer, mimetype="text/csv", resumable=False)
    service.files().update(fileId=file_id, media_body=media).execute()
