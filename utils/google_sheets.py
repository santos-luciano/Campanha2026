import io
import re
import urllib.parse

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


def _montar_csv_url_por_nome(link, nome_aba):
    sheet_id = _extrair_sheet_id(link)
    nome_codificado = urllib.parse.quote(nome_aba)
    return (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/gviz/tq?tqx=out:csv&sheet={nome_codificado}"
    )


def _baixar_e_validar_csv(csv_url):
    """Faz o GET e converte para DataFrame, detectando os erros mais comuns
    (planilha privada, aba inexistente, resposta vazia)."""
    resp = requests.get(csv_url, allow_redirects=True)

    if resp.status_code != 200:
        raise ValueError(
            f"Não consegui acessar a planilha (status {resp.status_code}). "
            f"URL testada: {csv_url}."
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


def carregar_planilha_google(link):
    """
    Carrega a primeira aba (ou a aba indicada pelo gid do link) de uma
    planilha pública do Google Sheets, retornando um DataFrame.
    """
    csv_url = _montar_csv_url(link)

    try:
        return _baixar_e_validar_csv(csv_url)
    except ValueError:
        # Se o gid da URL não existir na planilha, o Google responde 400.
        # Tenta de novo sem o gid, pegando a primeira aba.
        if _eh_link_publicado(link):
            raise
        csv_url = _montar_csv_url_sem_gid(link)
        return _baixar_e_validar_csv(csv_url)


def carregar_aba_por_nome(link, nome_aba):
    """
    Carrega uma aba específica de uma planilha pública do Google Sheets
    pelo NOME da aba (ex: "Gráfico", "Comentários"), sem depender do gid.
    """
    csv_url = _montar_csv_url_por_nome(link, nome_aba)
    return _baixar_e_validar_csv(csv_url)