# utils/local_data_loader.py
from pathlib import Path
import pandas as pd


def carregar_planilha_local(caminho: str = "data/arquivo.xlsx") -> pd.DataFrame:
    """
    Carrega uma planilha local (xlsx) do próprio repositório.
    """
    caminho = Path(caminho)

    if not caminho.exists():
        raise FileNotFoundError(
            f"Arquivo não encontrado em '{caminho}'. "
            "Verifique se o arquivo está no diretório 'data/' do repositório."
        )

    return pd.read_excel(caminho)
