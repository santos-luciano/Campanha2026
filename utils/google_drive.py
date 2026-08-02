import io
import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


@st.cache_resource
def autenticar_drive():
    info_credenciais = dict(st.secrets["gcp_service_account"])  # força conversão pra dict puro
    creds = service_account.Credentials.from_service_account_info(
        info_credenciais,
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def listar_arquivos_pasta(folder_id, service):
    query = f"'{folder_id}' in parents and trashed = false"
    resultados = []
    page_token = None
    while True:
        response = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            pageToken=page_token
        ).execute()
        resultados.extend(response.get("files", []))
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return resultados


def baixar_arquivo_como_df(file_id, service):
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    buffer.seek(0)
    return pd.read_excel(buffer)


def ler_todos_arquivos_pasta(folder_id, service):
    arquivos = listar_arquivos_pasta(folder_id, service)
    dfs = []
    for arq in arquivos:
        if arq["name"].endswith((".xlsx", ".xls")):
            df = baixar_arquivo_como_df(arq["id"], service)
            df["arquivo_origem"] = arq["name"]
            dfs.append(df)
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()