import io
import re

import pandas as pd
import requests


def _extrair_sheet_id(link):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", link)
    if not match:
        raise ValueError(
            "Link do Google Sheets inválido — não encontrei o ID da planilha na URL."
        )
    return match.group(1)


def _extrair_gid(link):
    match = re.search(r"[?&#]gid=([0-9]+)", link)
    return match.group(1) if match else "0"


def _eh_link_publicado(link):
    return "/d/e/" in link


def _extrair_id_publicado(link):
    match = re.search(r"/d/e/([a-zA-Z0-9-_]+)", link)
    if not match:
        raise ValueError("Não encontrei o ID da planilha publicada na URL.")
    return match.group(1)


def _montar_csv_url(link):
    if _eh_link_publicado(link):
        pub_id = _extrair_id_publicado(link)
        return f"https://docs.google.com/spreadsheets/d/e/{pub_id}/pub?output=csv"

    sheet_id = _extrair_sheet_id(link)
    gid = _extrair_gid(link)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def _montar_csv_url_sem_gid(link):
    sheet_id = _extrair_sheet_id(link)
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"


def carregar_planilha_google(link):
    """
    Carrega uma planilha pública do Google Sheets (compartilhada como
    "Qualquer pessoa com o link pode visualizar", ou publicada via
    Arquivo → Compartilhar → Publicar na web) a partir do link normal
    do navegador, retornando um DataFrame.
    """
    csv_url = _montar_csv_url(link)
    resp = requests.get(csv_url, allow_redirects=True)

    # Se o gid da URL não existir na planilha, o Google responde 400.
    # Tenta de novo sem o gid, pegando a primeira aba.
    if resp.status_code == 400 and not _eh_link_publicado(link):
        csv_url = _montar_csv_url_sem_gid(link)
        resp = requests.get(csv_url, allow_redirects=True)

    if resp.status_code != 200:
        raise ValueError(
            f"Não consegui acessar a planilha (status {resp.status_code}). "
            f"URL testada: {csv_url}. Confira se o link está correto e se a "
            "aba referenciada ainda existe."
        )

    content_type = resp.headers.get("Content-Type", "")
    texto = resp.text

    # Quando a planilha não é pública, o Google devolve uma página de login
    # (HTML) em vez do CSV — isso confunde o pandas se não for detectado antes.
    if "text/html" in content_type or texto.lstrip()[:100].lower().startswith(("<!doctype html", "<html")):
        raise ValueError(
            "A planilha parece estar privada. No Google Sheets, clique em "
            "'Compartilhar' → mude para 'Qualquer pessoa com o link' → papel "
            "'Leitor', e cole o link aqui de novo."
        )

    try:
        df = pd.read_csv(io.StringIO(texto))
    except Exception as err:
        raise ValueError(f"Não consegui interpretar o conteúdo como CSV: {err}") from err

    if df.empty or df.shape[1] == 0:
        raise ValueError("A planilha foi carregada, mas está vazia ou sem colunas reconhecíveis.")

    return df
