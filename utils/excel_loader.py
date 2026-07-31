import pandas as pd


def carregar_e_normalizar(files):
    """
    Carrega uma lista de arquivos Excel (vindos do st.file_uploader),
    normaliza os nomes de colunas conforme o padrão de cada tipo de
    arquivo, e retorna um único DataFrame concatenado com as colunas:
    Name, ProfileId, Comment, Date, Likes
    """
    dfs = [_carregar_arquivo(f) for f in files]

    df = pd.concat(dfs, ignore_index=True)
    df['Comment'] = df['Comment'].str.replace('\n', '', regex=False)

    if 'Likes' not in df.columns:
        df['Likes'] = None

    return df


def _carregar_arquivo(f):
    """Lê um único arquivo Excel e aplica a normalização de colunas
    de acordo com o padrão de nome do arquivo."""
    if 'exportcomments' in f.name:
        df = pd.read_excel(f)
        df = df.rename(columns={
            'Username': 'Name',
            "Display Name": "ProfileId",
        })
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    elif 'list' in f.name:
        df = pd.read_excel(f)
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    elif 'jaques_wagner' in f.name:
        df = pd.read_excel(f)
        df = _garantir_likes(df)
        df = df.rename(columns={
            'mes_ano': 'Date',
            "id": "ProfileId",
        })
        df['Name'] = df['ProfileId']

    elif 'tweet' in f.name:
        df = pd.read_excel(f, skiprows=6)
        df = df.dropna(subset=['Unnamed: 0'])
        df = df.rename(columns={
            'Username': 'ProfileId',
            "Tweet Text": "Comment",
        })
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    else:
        df = pd.read_excel(f, skiprows=6)
        df = df.dropna(subset=['Unnamed: 0'])
        df = df.rename(columns={'Profile ID': 'ProfileId'})
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    return df


def _garantir_likes(df):
    if 'Likes' not in df.columns:
        df['Likes'] = None
    return df
