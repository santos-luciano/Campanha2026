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

from utils.excel_loader import carregar_e_normalizar
from utils.google_sheets import carregar_planilha_google
from utils.metrics import (
    marcar_mencao_projeto,
    contar_duplicados,
    filtrar_comentarios_validos,
    marcar_mencao_pl_no_motivo,
    calcular_percentuais,
    estimar_totais,
)


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
            "Classificador de legendas",
            "🤖 Classificação",
            "🐦 Twitter",
            "📥 Capturar comentários",
        ]
    )

    if pagina == "Classificador de legendas":
        _aba_classificador_legendas()
    elif pagina == "🐦 Twitter":
        _aba_twitter()
    elif pagina == "📥 Capturar comentários":
        _aba_capturar_comentarios()
    else:
        files = st.file_uploader(
            "Carregue arquivos Excel",
            type=["xlsx", "xls"],
            accept_multiple_files=True
        )

        if not files:
            st.stop()

        df = carregar_e_normalizar(files)
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
def _aba_twitter():
    st.subheader("📈 Histórico Twitter/X")
    st.caption(
        "Gráfico de evolução a partir de uma planilha do Google Sheets, "
        "atualizada diariamente."
    )

    link = st.secrets.get("historico_twitter_sheet_url", "")

    if not link.strip():
        st.warning(
            "Nenhuma planilha configurada. Cadastre 'historico_twitter_sheet_url' "
            "em Manage app → Settings → Secrets."
        )
        return

    try:
        df = carregar_planilha_google(link)
    except ValueError as err:
        st.error(f"⚠️ {err}")
        return

    if df.empty:
        st.warning("A planilha está vazia.")
        return

    colunas = df.columns.tolist()

    col1, col2 = st.columns(2)
    with col1:
        coluna_data = st.selectbox("Coluna de data", colunas, index=0)
    with col2:
        colunas_restantes = [c for c in colunas if c != coluna_data]
        coluna_valor = st.selectbox("Coluna de valor", colunas_restantes)

    df_plot = df[[coluna_data, coluna_valor]].copy()
    df_plot[coluna_data] = pd.to_datetime(df_plot[coluna_data], errors="coerce", dayfirst=True)
    df_plot[coluna_valor] = pd.to_numeric(df_plot[coluna_valor], errors="coerce")
    df_plot = df_plot.dropna(subset=[coluna_data, coluna_valor]).sort_values(coluna_data)

    if df_plot.empty:
        st.warning(
            "Não consegui converter as colunas escolhidas em data/número. "
            "Verifique se selecionou as colunas certas."
        )
        return

    st.line_chart(df_plot.set_index(coluna_data)[coluna_valor])

    with st.expander("Ver dados da planilha"):
        st.dataframe(df, use_container_width=True)


# =================================================
# PÁGINA — CAPTURAR COMENTÁRIOS (ExportComments)
# =================================================
def _aba_capturar_comentarios():
    st.subheader("📥 Capturar comentários")
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
    st.subheader("Classificação dos Comentários")

    contexto = st.text_area(
        "Contexto da classificação",
        placeholder="Ex: Comentários sobre investimentos em saúde na Bahia feitos por políticos"
    )

    opcao = st.radio(
        "Escolha a classificação:",
        ["Jaques Wagner", "Camaçari"]
    )

    duplicados = 0

    if opcao == "Jaques Wagner":
        df = marcar_mencao_projeto(df)
        duplicados = contar_duplicados(df)
        comentarios_df = filtrar_comentarios_validos(df)
    else:
        comentarios_df = df

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

    n_projetos = 0

    if st.button("Classificar comentários"):
        classifier = CommentClassifier(
            api_key=os.getenv("OPENAI_API_KEY"),
            schema=schema_classifier,
            contexto=contexto
        )

        with st.spinner("Classificando comentários..."):
            resultado = classifier.classify(comentarios1)

        df_classificado_1 = pd.DataFrame(resultado["respostas"])

        mask_projeto = marcar_mencao_pl_no_motivo(df_classificado_1)
        n_projetos = mask_projeto.sum()

        st.session_state.df_classificado = df_classificado_1[~mask_projeto]

        st.success("Classificação concluída!")

    if st.session_state.df_classificado is not None:
        _exibir_resultados(
            df, total_comentarios, opcao, duplicados, n_projetos,
            comentarios, contexto
        )


def _exibir_resultados(df, total_comentarios, opcao, duplicados, n_projetos,
                        comentarios, contexto):
    st.dataframe(
        st.session_state.df_classificado,
        use_container_width=True
    )

    top5 = (
        df
        .dropna(subset=["Likes", "Comment"])
        .sort_values(by="Likes", ascending=False)
        .head(3)
    )

    df_base = st.session_state.df_classificado

    pipeline = SentimentAnalysisPipeline(
        api_key=os.getenv("OPENAI_API_KEY"),
        schema=schema_classifier_consolidado,
        contexto=contexto
    )

    if "df_resultado" not in st.session_state:
        st.session_state.df_resultado = pipeline.run(df_base)

    df_resultado = pipeline.run(df_base)
    resultado = df_resultado.iloc[0]

    percentuais = calcular_percentuais(df_base)
    est_pos, est_neu, est_neg = estimar_totais(percentuais, len(comentarios))
    total_validos = est_pos + est_neu + est_neg

    st.subheader("📊 Análise Geral")
    st.markdown("---")

    if opcao == "Jaques Wagner":
        mencoes_pl = df['menciona_projeto'].sum() + n_projetos

        st.markdown(f"**💬 Total de comentários:** {total_comentarios}")
        st.markdown(
            f"**📌 Menções a PLs/PECs:** {mencoes_pl} "
            f"({mencoes_pl/total_comentarios:.2%})"
        )
        st.markdown(
            f"**🔁 Comentários repetidos (mesmo autor):** {duplicados} "
            f"({duplicados/total_comentarios:.2%})"
        )
        st.markdown(
            f"**✅ Comentários válidos:** {total_validos} "
            f"({total_validos/total_comentarios:.2%})"
        )
        st.markdown("---")

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