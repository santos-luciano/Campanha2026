import pandas as pd

import io
import zipfile

# Formato "bruto" de comentários do Instagram
COLUNAS_FORMATO_MENSAGEM = {'username', 'profile_id', 'message', 'time'}

# Formato "bruto" de comentários do Facebook (name/nick_name em vez de
# username, e presença de post_id/comment_id que não existem no formato IG)
COLUNAS_FORMATO_FACEBOOK = {'name', 'nick_name', 'message', 'profile_id', 'time', 'post_id'}


def carregar_e_normalizar(files):
    dfs = []

    for f in files:
        try:
            print(f"Processando arquivo: {f.name}")

            df = _carregar_arquivo(f)

            dfs.append(df)

        except Exception as e:
            print(f"ERRO NO ARQUIVO: {f.name}")
            print(f"TIPO DO ERRO: {type(e).__name__}")
            print(f"ERRO: {e}")

            raise

    df = pd.concat(dfs, ignore_index=True)

    df['Comment'] = df['Comment'].str.replace(
        '\n',
        '',
        regex=False
    )

    if 'Likes' not in df.columns:
        df['Likes'] = None

    return df

def _ler_excel(f, **kwargs):
    """
    Lê o Excel normalmente.

    Se houver algum problema no XML interno relacionado ao atributo
    'showZeroes', remove esse atributo e tenta ler novamente.
    """

    f.seek(0)

    try:
        # Primeira tentativa: arquivo original
        return pd.read_excel(f, **kwargs)

    except Exception as erro_original:

        # Volta ao início do arquivo
        f.seek(0)

        arquivo = io.BytesIO(f.read())
        arquivo_corrigido = io.BytesIO()

        try:
            with zipfile.ZipFile(arquivo, 'r') as zin:
                with zipfile.ZipFile(
                    arquivo_corrigido,
                    'w',
                    zipfile.ZIP_DEFLATED
                ) as zout:

                    for item in zin.infolist():
                        conteudo = zin.read(item.filename)

                        if (
                            item.filename.startswith('xl/worksheets/')
                            and item.filename.endswith('.xml')
                        ):
                            conteudo = conteudo.replace(
                                b' showZeroes="1"',
                                b''
                            )
                            conteudo = conteudo.replace(
                                b' showZeroes="0"',
                                b''
                            )

                        zout.writestr(item, conteudo)

            arquivo_corrigido.seek(0)

            # Segunda tentativa: arquivo corrigido
            return pd.read_excel(arquivo_corrigido, **kwargs)

        except Exception:
            # Se não conseguir corrigir, mantém o erro original
            raise erro_original


def _carregar_arquivo(f):
    """
    Lê um único arquivo Excel. A detecção por ASSINATURA DE COLUNAS tem
    prioridade sobre a heurística de nome de arquivo (que é ambígua).
    Ordem de checagem: formato Instagram -> formato Facebook -> nome de
    arquivo (fallback para formatos antigos).
    """
    df_bruto = _ler_excel(f)

    if COLUNAS_FORMATO_MENSAGEM.issubset(df_bruto.columns):
        return _normalizar_formato_mensagem(df_bruto)

    if COLUNAS_FORMATO_FACEBOOK.issubset(df_bruto.columns):
        return _normalizar_formato_facebook(df_bruto)

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
        df = _ler_excel(f, skiprows=6)
        df = df.dropna(subset=['Unnamed: 0'])
        df = df.rename(columns={
            'Username': 'ProfileId',
            "Tweet Text": "Comment",
        })
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    else:
        f.seek(0)
        df = _ler_excel(f, skiprows=6)
        df = df.dropna(subset=['Unnamed: 0'])
        df = df.rename(columns={'Profile ID': 'ProfileId'})
        df = _garantir_likes(df)
        df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    return df


def _normalizar_formato_mensagem(df):
    df = df.rename(columns={
        'username': 'Name',
        'profile_id': 'ProfileId',
        'message': 'Comment',
        'time': 'Date',
        'likes': 'Likes',
    })
    df['Date'] = pd.to_datetime(df['Date'], unit='s', errors='coerce')
    df = _garantir_likes(df)
    df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]
    return df


def _normalizar_formato_facebook(df):
    """
    Normaliza o export "bruto" de comentários do Facebook (colunas: name,
    nick_name, time, likes, message, profile_id, profile_id (duplicada),
    post_id, comment_id, parent_comment_id, ...).
    """
    df = df.rename(columns={
        'name': 'Name',
        'profile_id': 'ProfileId',
        'message': 'Comment',
        'time': 'Date',
        'likes': 'Likes',
    })

    # 'time' vem como timestamp Unix em segundos
    df['Date'] = pd.to_datetime(df['Date'], unit='s', errors='coerce')

    df = _garantir_likes(df)
    df = df[['Name', 'ProfileId', "Comment", "Date", "Likes"]]

    return df


def _garantir_likes(df):
    if 'Likes' not in df.columns:
        df['Likes'] = None
    return df