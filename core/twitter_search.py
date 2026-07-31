import os
from datetime import datetime, timedelta

import pandas as pd
from xdk import Client


def _get_client():
    bearer_token = os.getenv("bearer_token")
    return Client(bearer_token=bearer_token)


def buscar_tweet(termo, data, max_results=100):
    """
    Busca tweets em português contendo `termo` (sem retweets) no dia `data`
    (formato "YYYY-MM-DD").

    Retorna (contagem_termo, DataFrame) onde:
    - contagem_termo: total de tweets com o termo no dia (via API de contagem)
    - DataFrame: colunas Comment, mes_ano, id, com até `max_results` tweets
    """
    client = _get_client()

    inicio = datetime.strptime(data, "%Y-%m-%d")
    fim = inicio + timedelta(days=1)

    start_time = inicio.strftime("%Y-%m-%d") + "T03:00:00Z"
    end_time = fim.strftime("%Y-%m-%d") + "T03:00:00Z"

    query = f'"{termo}" lang:pt -is:retweet'

    contagem_termo = 0
    for page in client.posts.get_counts_recent(
        query=query,
        start_time=start_time,
        end_time=end_time,
        granularity="day"
    ):
        if page.data:
            for item in page.data:
                contagem_termo += item["tweet_count"]

    comentarios = []
    coletados = 0
    for page in client.posts.search_recent(
        query=query,
        start_time=start_time,
        end_time=end_time,
        max_results=max_results
    ):
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
    """
    twitter = pd.DataFrame()
    contagens = []

    for i in range(1, dias + 1):
        data_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        contagem, df_dia = buscar_tweet(termo, data_str, max_results=max_results)
        contagens.append({"data": data_str, "contagem": contagem})
        twitter = pd.concat([twitter, df_dia], ignore_index=True)

    return twitter, contagens
