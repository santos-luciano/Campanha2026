import pandas as pd

# Colunas que identificam o export "bruto" de comentários do Instagram
# (id, shortcode, username, name, time, likes, comment_id, message,
# sentiment, profile_id, ...). Detectamos pelo conjunto de colunas, não
# pelo nome do arquivo, já que esse nome pode variar.
COLUNAS_FORMATO_MENSAGEM = {'username', 'profile_id', 'message', 'time'}


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
    """
    Lê um único arquivo Excel. Primeiro verifica se é o formato
    "message" (export bruto, ex: Instagram) pela ASSINATURA DAS COLUNAS —
    isso tem prioridade sobre qualquer heurística de nome de arquivo, que
    pode ser ambígua (ex: nomes de arquivo que contêm 'exportcomments'
    sem de fato ter as colunas Username/Display Name esperadas por esse
    formato). Só cai na lógica antiga (baseada em nome de arquivo) se as
    colunas não baterem com o formato "message".
    """
    df_bruto = pd.read_excel(f)

    if COLUNAS_FORMATO_MENSAGEM.issubset(df_bruto.columns):
        return _normalizar_formato_mensagem(df_bruto)

    if 'exportcomments' in f.name:
        df = df_bruto.rename(columns={
            'Username': 'Name',
            "Display Name": "ProfileId",
        })
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    elif 'list' in f.name:
        df = _garantir_likes(df_bruto)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    elif 'jaques_wagner' in f.name:
        df = _garantir_likes(df_bruto)
        df = df.rename(columns={
            'mes_ano': 'Date',
            "id": "ProfileId",
        })
        df['Name'] = df['ProfileId']

    elif 'tweet' in f.name:
        f.seek(0)
        df = pd.read_excel(f, skiprows=6)
        df = df.dropna(subset=['Unnamed: 0'])
        df = df.rename(columns={
            'Username': 'ProfileId',
            "Tweet Text": "Comment",
        })
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    else:
        f.seek(0)
        df = pd.read_excel(f, skiprows=6)
        df = df.dropna(subset=['Unnamed: 0'])
        df = df.rename(columns={'Profile ID': 'ProfileId'})
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    return df


def _normalizar_formato_mensagem(df):
    """
    Normaliza o export "bruto" de comentários (colunas: username,
    profile_id, message, time, likes, ...) — comum em exports diretos
    do Instagram com id, shortcode, sentiment, media_id etc.
    """
    df = df.rename(columns={
        'username': 'Name',
        'profile_id': 'ProfileId',
        'message': 'Comment',
        'time': 'Date',
        'likes': 'Likes',
    })

    # 'time' costuma vir como timestamp Unix (segundos) — converte para
    # data/hora de verdade. Se não vier nesse formato, cai em NaT.
    df['Date'] = pd.to_datetime(df['Date'], unit='s', errors='coerce')

    df = _garantir_likes(df)
    df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    return df


def _garantir_likes(df):
    if 'Likes' not in df.columns:
        df['Likes'] = None
    return df