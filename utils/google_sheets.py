import re
import pandas as pd


def extrair_sheet_id(url: str) -> str:
    """
    Extrai o ID de uma URL do Google Sheets.
    """
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)

    if not match:
        raise ValueError("Link do Google Sheets inválido.")

    return match.group(1)


def carregar_planilha_google(url: str, gid: str | None = None) -> pd.DataFrame:
    """
    Carrega uma aba pública do Google Sheets em um DataFrame.

    Parameters
    ----------
    url : str
        Link da planilha.
    gid : str, optional
        ID da aba (caso não informado usa a primeira).

    Returns
    -------
    pandas.DataFrame
    """

    sheet_id = extrair_sheet_id(url)

    if gid is None:
        gid = "0"

    csv_url = (
        f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        f"/export?format=csv&gid={gid}"
    )

    try:
        df = pd.read_csv(csv_url)
    except Exception as e:
        raise ValueError(
            "Não foi possível carregar a planilha. "
            "Verifique se ela está pública e se o link está correto."
        ) from e

    return df
