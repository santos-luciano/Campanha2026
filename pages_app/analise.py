import io
import os
import random


import pandas as pd
import streamlit as st

from config.schema import schema_classifier
from config.schema_classifier import schema_classifier_consolidado
from core.classificar_sentimentos import SentimentAnalysisPipeline
from core.classifier_legend import CaptionClassifier
from core.comment_classifier import CommentClassifier
from core.exportcomments_client import extrair_comentarios, ExportCommentsError
from core.wordcloud_builder import exibir_nuvem_palavras

from utils.excel_loader import carregar_e_normalizar
from utils.google_sheets import carregar_aba_por_nome
from utils.metrics import (
    marcar_mencao_projeto,
    contar_duplicados,
    filtrar_comentarios_validos,
    marcar_mencao_pl_no_motivo,
    calcular_percentuais,
    estimar_totais,
)

MESES_PT = {
    1: "jan", 2: "fev", 3: "mar", 4: "abr",
    5: "mai", 6: "jun", 7: "jul", 8: "ago",
    9: "set", 10: "out", 11: "nov", 12: "dez",
}


def tela_principal():
    st.sidebar.write(f"👤 Logado como: **{st.session_state.usuario}**")
    if st.sidebar.button("Sair"):
        st.session_state.autenticado = False
        st.session_state.usuario = None
        st.rerun()

    st.title("Análise de Comentários - LabCaos")

    st.sidebar.markdown("---")
    pagina = st.sidebar.radio(
        "Menu",
        [
            "Classificação de comentários",
            "Twitter/X",
            "Extração de comentários",
            "Classificador de legendas",

        ]
    )

    if pagina == "Classificador de legendas":
        _aba_classificador_legendas()
    elif pagina == "Twitter/X":
        _aba_twitter()
    elif pagina == "Extração de comentários":
        _aba_capturar_comentarios()
    else:
        files = st.file_uploader(
            "Carregue arquivos Excel",
            type=["xlsx", "xls"],
            accept_multiple_files=True,
            key="uploader_comentarios",
        )

        if files:
            fingerprint = tuple((f.name, f.size) for f in files)
            if fingerprint != st.session_state.get("upload_fingerprint"):
                # Arquivo novo: recarrega os dados e descarta a classificação anterior
                st.session_state.df_upload = carregar_e_normalizar(files)
                st.session_state.upload_fingerprint = fingerprint
                st.session_state.df_classificado = None
                st.session_state.pop("df_resultado", None)
                st.session_state.pop("df_resultado_hash", None)

        df = st.session_state.get("df_upload")

        if df is None:
            st.info("Carregue um arquivo Excel para continuar.")
            st.stop()

        total_comentarios = df["Comment"].dropna().shape[0]

        _aba_classificacao_comentarios(df, total_comentarios)


# =================================================
# PÁGINA — CLASSIFICADOR DE LEGENDAS
# =================================================
def _aba_classificador_legendas():
    st.subheader("Classificador de Legendas")

    legenda = st.text_area("Cole a legenda", height=200)

    classifier = CaptionClassifier(api_key=os.getenv("OPENAI_API_KEY"))

    if st.button("Classificar"):
        if legenda.strip():
            resultado = classifier.classify(legenda)
            st.success(f"**Categoria:** {resultado['categoria']}")


# =================================================
# PÁGINA — HISTÓRICO TWITTER / X
# =================================================
NOME_ABA_GRAFICO = "Gráfico"
NOME_ABA_COMENTARIOS = "Comentários"
COLUNA_DATA = "Data"
COLUNA_VALOR = "Menções a Jaques Wagner"


def _aba_twitter():
    st.subheader("Histórico Twitter/X")
    st.caption(
        f"Evolução de {COLUNA_VALOR.lower()} ao longo do tempo, "
        f"a partir da aba '{NOME_ABA_GRAFICO}' da planilha (atualizada diariamente)."
    )

    link = st.secrets.get("historico_twitter_sheet_url", "")

    if not link.strip():
        st.warning(
            "Nenhuma planilha configurada. Cadastre 'historico_twitter_sheet_url' "
            "em Manage app → Settings → Secrets."
        )
        return

    try:
        df = carregar_aba_por_nome(link, NOME_ABA_GRAFICO)
    except ValueError as err:
        st.error(f"⚠️ {err}")
        return

    if COLUNA_DATA not in df.columns or COLUNA_VALOR not in df.columns:
        st.error(
            f"⚠️ Não encontrei as colunas '{COLUNA_DATA}' e/ou '{COLUNA_VALOR}' "
            f"na aba '{NOME_ABA_GRAFICO}'. Colunas encontradas: {', '.join(df.columns)}"
        )
        return

    df_plot = df[[COLUNA_DATA, COLUNA_VALOR]].copy()
    df_plot[COLUNA_DATA] = pd.to_datetime(df_plot[COLUNA_DATA], errors="coerce", dayfirst=True)
    df_plot[COLUNA_VALOR] = pd.to_numeric(df_plot[COLUNA_VALOR], errors="coerce")
    df_plot = df_plot.dropna(subset=[COLUNA_DATA, COLUNA_VALOR]).sort_values(COLUNA_DATA)

    


    if df_plot.empty:
        st.warning(
            f"Não consegui converter as colunas '{COLUNA_DATA}'/'{COLUNA_VALOR}' "
            "em data/número. Confira os valores na planilha."
        )
        return
    else:
        df_plot[COLUNA_DATA] = df_plot[COLUNA_DATA].apply(
        lambda d: f"{d.day:02d} {MESES_PT[d.month]}")

    st.line_chart(df_plot.set_index(COLUNA_DATA)[COLUNA_VALOR])

    with st.expander("Ver dados da planilha"):
        aba_escolhida = st.radio(
            "Aba", [NOME_ABA_GRAFICO, NOME_ABA_COMENTARIOS], horizontal=True
        )

        try:
            df_aba = (
                df if aba_escolhida == NOME_ABA_GRAFICO
                else carregar_aba_por_nome(link, NOME_ABA_COMENTARIOS)
            )
        except ValueError as err:
            st.error(f"⚠️ {err}")
        else:
            st.dataframe(df_aba, use_container_width=True)


# =================================================
# PÁGINA — CAPTURAR COMENTÁRIOS (ExportComments)
# =================================================
def _aba_capturar_comentarios():
    st.subheader("Extração de comentários")
    st.caption(
        "Extrai comentários de um post (Instagram/Facebook/etc.) via "
        "ExportComments.com, sem precisar exportar manualmente."
    )

    url_post = st.text_input("Link do post", placeholder="https://www.instagram.com/p/...")

    col1, col2 = st.columns(2)
    with col1:
        limite = st.number_input(
            "Limite de comentários", min_value=10, max_value=5000, value=500, step=50
        )
    with col2:
        incluir_respostas = st.checkbox("Incluir respostas", value=True)

    if st.button("Capturar comentários"):
        if not url_post.strip():
            st.warning("Cole o link do post.")
        else:
            status_box = st.empty()

            def atualizar_status(msg):
                status_box.info(f"⏳ {msg}")

            try:
                dados = extrair_comentarios(
                    url_post,
                    limite=int(limite),
                    incluir_respostas=incluir_respostas,
                    on_status=atualizar_status,
                )
                status_box.empty()
                st.session_state.df_capturado = pd.DataFrame(dados)
                st.success(f"✅ {len(dados)} comentários capturados.")
            except ExportCommentsError as err:
                status_box.empty()
                st.error(f"⚠️ {err}")

    df_capturado = st.session_state.get("df_capturado")

    if df_capturado is not None and not df_capturado.empty:
        st.dataframe(df_capturado, use_container_width=True)

        buffer = io.BytesIO()
        df_capturado.to_excel(buffer, index=False)
        st.download_button(
            "⬇️ Baixar comentários (Excel)",
            data=buffer.getvalue(),
            file_name="comentarios_exportcomments.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.caption(
            "O nome do arquivo já contém 'exportcomments', então a aba 🤖 "
            "Classificação vai tentar aplicar a mesma normalização de colunas "
            "usada para arquivos exportados manualmente. Confira se os nomes "
            "de coluna batem (Name, ProfileId, Comment, Date, Likes) antes de "
            "carregar lá — a API pode retornar nomes diferentes."
        )


# =================================================
# PÁGINA — CLASSIFICAÇÃO DE COMENTÁRIOS
# =================================================
def _aba_classificacao_comentarios(df, total_comentarios):

#    opcao = st.radio(
#        "Escolha a classificação:",
#        ["Jaques Wagner", "Camaçari"]
#    )

#    duplicados = 0

#    if opcao == "Jaques Wagner":
#        df = marcar_mencao_projeto(df)
#        duplicados = contar_duplicados(df)
#        comentarios_df = filtrar_comentarios_validos(df)
#    else:
#        comentarios_df = df

    comentarios_df = filtrar_comentarios_validos(df)

    comentarios = (
        comentarios_df["Comment"]
        .dropna()
        .astype(str)
        .tolist()
    )

    comentarios1 = (
        random.sample(comentarios, 1000)
        if len(comentarios) > 1000
        else comentarios
    )

    exibir_nuvem_palavras(
    comentarios_df["Comment"],
    titulo="☁️ Nuvem de Palavras — Comentários",
    nome_arquivo="nuvem_comentarios",
    )

    st.subheader("Classificação dos Comentários")

    contexto = st.text_area(
        "Contexto da classificação",
        placeholder="Ex: Comentários sobre investimentos em saúde na Bahia feitos por políticos"
    )

#    n_projetos = 0

    if st.button("Classificar comentários"):
        classifier = CommentClassifier(
            api_key=os.getenv("OPENAI_API_KEY"),
            schema=schema_classifier,
            contexto=contexto
        )

        barra_progresso = st.progress(0.0)
        texto_status = st.empty()

        def _atualizar_progresso(lote_atual, total_lotes, mensagem):
            barra_progresso.progress(lote_atual / total_lotes)
            texto_status.info(f"⏳ {mensagem}")


#        with st.spinner("Classificando comentários..."):
#        resultado = classifier.classify(comentarios1)
 
        resultado = classifier.classify(comentarios1, on_progress=_atualizar_progresso)
 
        barra_progresso.empty()
        texto_status.empty()

        df_classificado_1 = pd.DataFrame(resultado["respostas"])

        mask_projeto = marcar_mencao_pl_no_motivo(df_classificado_1)
        n_projetos = mask_projeto.sum()

        st.session_state.df_classificado = df_classificado_1[~mask_projeto]

        st.success("Classificação concluída!")

    if st.session_state.df_classificado is not None:
        _exibir_resultados(
            df,
            comentarios, contexto
        )


#def _exibir_resultados(df, total_comentarios, opcao, duplicados, n_projetos,
#                        comentarios, contexto):
def _exibir_resultados(df,
                        comentarios, contexto):

    st.markdown("**✏️ Classificação dos comentários** — clique em uma célula da coluna "
                "*classificacao* para corrigir manualmente, se necessário.")

    df_editado = st.data_editor(
        st.session_state.df_classificado,
        column_config={
            "classificacao": st.column_config.SelectboxColumn(
                "classificacao",
                options=["positivo", "negativo", "neutro"],
                required=True,
            )
        },
        disabled=[c for c in st.session_state.df_classificado.columns if c != "classificacao"],
        use_container_width=True,
        key="editor_classificacao",
    )

    if not df_editado.equals(st.session_state.df_classificado):
        st.session_state.df_classificado = df_editado

    top5 = (
        df
        .dropna(subset=["Likes", "Comment"])
        .sort_values(by="Likes", ascending=False)
        .head(3)
    )

    df_base = st.session_state.df_classificado

    percentuais = calcular_percentuais(df_base)
    est_pos, est_neu, est_neg = estimar_totais(percentuais, len(comentarios))
    total_validos = est_pos + est_neu + est_neg

    hash_atual = hash(tuple(df_base["classificacao"]))
    analise_desatualizada = st.session_state.get("df_resultado_hash") != hash_atual

    if analise_desatualizada and "df_resultado" in st.session_state:
        st.caption("⚠️ Você alterou classificações desde a última análise de sentimento.")

    if st.button("📊 Analisar sentimentos"):
        pipeline = SentimentAnalysisPipeline(
            api_key=os.getenv("OPENAI_API_KEY"),
            schema=schema_classifier_consolidado,
            contexto=contexto
        )
        with st.spinner("Analisando sentimentos..."):
            st.session_state.df_resultado = pipeline.run(df_base)
        st.session_state.df_resultado_hash = hash_atual
        analise_desatualizada = False

    if "df_resultado" in st.session_state:
        st.subheader("📊 Análise Geral")
        st.markdown("---")

#        if opcao == "Jaques Wagner":
#            mencoes_pl = df['menciona_projeto'].sum() + n_projetos
#
#            st.markdown(f"**💬 Total de comentários:** {total_comentarios}")
#            st.markdown(
#                f"**📌 Menções a PLs/PECs:** {mencoes_pl} "
#                f"({mencoes_pl/total_comentarios:.2%})"
#            )
#            st.markdown(
#                f"**🔁 Comentários repetidos (mesmo autor):** {duplicados} "
#                f"({duplicados/total_comentarios:.2%})"
#            )
#            st.markdown(
#                f"**✅ Comentários válidos:** {total_validos} "
#                f"({total_validos/total_comentarios:.2%})"
#            )
#            st.markdown("---")

        resultado = st.session_state.df_resultado.iloc[0]
        topicos = resultado["main_topics"]

        st.markdown(
            f"🧠 **Temas principais:** {' | '.join(t.capitalize() for t in topicos)}"
        )

        st.markdown(f"🟢 **Comentários Positivos:** {est_pos} ({percentuais['p_pos']:.2%})")
        st.markdown(resultado["review_comments_positives"] or "_Sem comentários positivos_")

        st.markdown(f"🟡 **Comentários Neutros:** {est_neu} ({percentuais['p_neu']:.2%})")
        st.markdown(resultado["review_comments_neutral"] or "_Sem comentários neutros_")

        st.markdown(f"🔴 **Comentários Negativos:** {est_neg} ({percentuais['p_neg']:.2%})")
        st.markdown(resultado["review_comments_negative"] or "_Sem comentários negativos_")

        st.subheader("👍 Comentários mais curtidos")

        if top5.empty:
            st.write("_Sem comentários curtidos_")
        else:
            for i, row in enumerate(top5.itertuples(), start=1):
                comentario = getattr(row, "Comment")
                likes = int(row.Likes)

                if len(comentario) > 200:
                    comentario = comentario[:200] + "..."

                st.write(f"{i}. \"{comentario}\" – {likes} curtidas")