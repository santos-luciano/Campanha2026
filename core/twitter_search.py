import os
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from xdk import Client


class TwitterAPIError(Exception):
    """Erro amigável para problemas de autenticação/permissão/limite na API do X."""
    pass


def _get_bearer_token():
    # 1) tenta o secrets.toml / painel de Secrets do Streamlit Cloud
    token = st.secrets.get("bearer_token")
    # 2) fallback para variável de ambiente (ex: rodando fora do Streamlit)
    if not token:
        token = os.getenv("bearer_token")

    if not token:
        raise TwitterAPIError(
            "bearer_token não encontrado. Cadastre 'bearer_token' em "
            "Manage app → Settings → Secrets (Streamlit Cloud) ou no seu .env local."
        )

    return token


def _get_client():
    return Client(bearer_token=_get_bearer_token())


def _chamar_api(descricao, chamada):
    """Executa uma chamada à API do X convertendo erros técnicos (auth,
    permissão, formato de resposta) em uma mensagem clara para o usuário."""
    try:
        return list(chamada())
    except Exception as err:
        nome_erro = type(err).__name__
        mensagem = str(err)

        if "ValidationError" in nome_erro:
            raise TwitterAPIError(
                f"A API do X não retornou o resultado esperado ao {descricao}. "
                "Isso normalmente indica token inválido/expirado, ou que sua "
                "chave não tem acesso a este endpoint (ex: contagem de tweets "
                "recentes exige plano pago da API do X). Confira em "
                "'Manage app → Logs' o corpo real da resposta."
            ) from err

        if "401" in mensagem or "Unauthorized" in mensagem:
            raise TwitterAPIError(
                f"Falha de autenticação ao {descricao}: o bearer_token foi "
                "rejeitado pela API do X. Confira se o valor cadastrado nos "
                "Secrets está correto e não expirou."
            ) from err

        if "403" in mensagem or "Forbidden" in mensagem:
            raise TwitterAPIError(
                f"Acesso negado ao {descricao}: sua chave da API do X não tem "
                "permissão para este endpoint (verifique o plano contratado)."
            ) from err

        if "429" in mensagem or "Too Many Requests" in mensagem:
            raise TwitterAPIError(
                f"Limite de requisições da API do X atingido ao {descricao}. "
                "Aguarde alguns minutos e tente novamente."
            ) from err

        raise TwitterAPIError(f"Erro inesperado ao {descricao}: {mensagem}") from err


def buscar_tweet(termo, data, max_results=100):
    """
    Busca tweets em português contendo `termo` (sem retweets) no dia `data`
    (formato "YYYY-MM-DD").

    Retorna (contagem_termo, DataFrame) onde:
    - contagem_termo: total de tweets com o termo no dia (via API de contagem)
    - DataFrame: colunas Comment, mes_ano, id, com até `max_results` tweets

    Lança TwitterAPIError com mensagem amigável em caso de falha na API.
    """
    client = _get_client()

    inicio = datetime.strptime(data, "%Y-%m-%d")
    fim = inicio + timedelta(days=1)

    start_time = inicio.strftime("%Y-%m-%d") + "T03:00:00Z"
    end_time = fim.strftime("%Y-%m-%d") + "T03:00:00Z"

    query = f'"{termo}" lang:pt -is:retweet'

    paginas_contagem = _chamar_api(
        "contar tweets recentes",
        lambda: client.posts.get_counts_recent(
            query=query,
            start_time=start_time,
            end_time=end_time,
            granularity="day"
        )
    )

    contagem_termo = 0
    for page in paginas_contagem:
        if page.data:
            for item in page.data:
                contagem_termo += item["tweet_count"]

    paginas_busca = _chamar_api(
        "buscar tweets recentes",
        lambda: client.posts.search_recent(
            query=query,
            start_time=start_time,
            end_time=end_time,
            max_results=max_results
        )
    )

    comentarios = []
    coletados = 0
    for page in paginas_busca:
        if page.data:
            for post in page.data:
                if coletados >= max_results:
                    break
                comentarios.append({
                    "Comment": post["text"],
                    "mes_ano": data,
                    "id": post["id"]
                })
                coletados += 1
        if coletados >= max_results:
            break

    resultados = pd.DataFrame(comentarios)

    return contagem_termo, resultados


def buscar_periodo(termo, dias, max_results=100):
    """
    Busca tweets contendo `termo` para cada um dos últimos `dias` dias
    (a partir de ontem).

    Retorna (DataFrame concatenado, lista de dicts {"data", "contagem"}).
    Lança TwitterAPIError com mensagem amigável em caso de falha na API.
    """
    twitter = pd.DataFrame()
    contagens = []

    for i in range(1, dias + 1):
        data_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        contagem, df_dia = buscar_tweet(termo, data_str, max_results=max_results)
        contagens.append({"data": data_str, "contagem": contagem})
        twitter = pd.concat([twitter, df_dia], ignore_index=True)

    return twitter, contagens