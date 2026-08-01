import os
import time

import requests
import streamlit as st

BASE_URL = "https://exportcomments.com"


class ExportCommentsError(Exception):
    """Erro amigável para problemas com a API do ExportComments."""
    pass


def _get_api_token():
    token = st.secrets.get("exportcomments_api_key")
    if not token:
        token = os.getenv("exportcomments_api_key")

    if not token:
        raise ExportCommentsError(
            "exportcomments_api_key não encontrado. Cadastre em "
            "Manage app → Settings → Secrets (Streamlit Cloud) ou no seu .env local."
        )

    return token


def _headers():
    return {
        "X-AUTH-TOKEN": _get_api_token(),
        "Content-Type": "application/json",
    }


def _checar_resposta(resp, descricao):
    if resp.status_code == 401:
        raise ExportCommentsError(f"Token inválido/expirado ao {descricao} (401).")
    if resp.status_code == 403:
        raise ExportCommentsError(f"Acesso negado ao {descricao} (403) — verifique a chave/plano.")
    try:
        resp.raise_for_status()
    except requests.HTTPError as err:
        raise ExportCommentsError(f"Erro ao {descricao}: {err}") from err


def listar_jobs() -> list:
    """Retorna a lista completa de jobs da conta."""
    resp = requests.get(f"{BASE_URL}/api/v3/jobs", headers={"X-AUTH-TOKEN": _get_api_token()})
    _checar_resposta(resp, "listar jobs")
    return resp.json()["items"]


def parar_job(guid: str) -> bool:
    """Tenta parar um job específico. Retorna True se conseguiu."""
    resp = requests.patch(
        f"{BASE_URL}/api/v3/job/{guid}/stop",
        headers={"X-AUTH-TOKEN": _get_api_token()},
    )
    return resp.status_code == 200


def liberar_slot(timeout: int = 120, intervalo: int = 10, on_status=None) -> None:
    """
    Verifica se há jobs travados (queueing/progress) ocupando o slot de
    concorrência. Tenta parar cada um; se não conseguir, aguarda até
    liberar ou até estourar o timeout.
    """
    inicio = time.time()
    while True:
        jobs = listar_jobs()
        travados = [j for j in jobs if j["status"] in ("queueing", "progress")]
        if not travados:
            return

        for job in travados:
            guid = job["guid"]
            if on_status:
                on_status(f"Job travado encontrado: {guid} ({job['status']}). Tentando parar...")
            parou = parar_job(guid)
            if on_status:
                on_status("  → parado com sucesso" if parou else "  → não foi possível parar agora")

        if time.time() - inicio > timeout:
            raise ExportCommentsError(
                f"Não foi possível liberar o slot em {timeout}s. "
                f"Jobs ainda travados: {[j['guid'] for j in travados]}"
            )
        time.sleep(intervalo)


def criar_job(url_post: str, limite: int = 500, incluir_respostas: bool = True, on_status=None) -> str:
    """
    Cria um job de exportação. Libera o slot automaticamente se houver
    algo travado antes de tentar.
    """
    if on_status:
        on_status("Verificando slots disponíveis...")
    liberar_slot(on_status=on_status)

    if on_status:
        on_status("Criando job de exportação...")

    resp = requests.post(
        f"{BASE_URL}/api/v3/job",
        headers=_headers(),
        json={
            "url": url_post,
            "options": {
                "limit": limite,
                "replies": incluir_respostas,
            },
        },
    )

    if resp.status_code == 429:
        retry_after = int(resp.headers.get("Retry-After", 30))
        raise ExportCommentsError(
            f"Rate limit atingido mesmo após liberar o slot. Aguarde {retry_after}s e tente novamente."
        )

    _checar_resposta(resp, "criar job")
    return resp.json()["guid"]


def aguardar_job(guid: str, intervalo: int = 8, timeout: int = 600, on_status=None) -> dict:
    """Faz polling do status do job até ficar 'done' ou falhar."""
    inicio = time.time()
    while True:
        resp = requests.get(f"{BASE_URL}/api/v3/job/{guid}", headers={"X-AUTH-TOKEN": _get_api_token()})
        _checar_resposta(resp, "consultar status do job")
        job = resp.json()
        status = job["status"]

        if on_status:
            on_status(f"Status do job: {status}")

        if status == "done":
            return job
        if status in ("error", "stopped"):
            raise ExportCommentsError(f"Job falhou com status '{status}'.")
        if time.time() - inicio > timeout:
            raise ExportCommentsError(f"Job não concluiu em {timeout}s (status atual: {status}).")

        time.sleep(intervalo)


def extrair_comentarios(url_post: str, limite: int = 500, incluir_respostas: bool = True, on_status=None) -> list:
    """
    Fluxo completo: libera slot se necessário, cria o job, aguarda
    conclusão e baixa os comentários em JSON.
    """
    guid = criar_job(url_post, limite=limite, incluir_respostas=incluir_respostas, on_status=on_status)
    job = aguardar_job(guid, on_status=on_status)

    if on_status:
        on_status("Baixando comentários...")

    json_url = job["json_url"]
    dados = requests.get(json_url)
    dados.raise_for_status()
    return dados.json()
