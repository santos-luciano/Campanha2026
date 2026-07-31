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
from core.twitter_search import buscar_periodo, TwitterAPIError
from core.wordcloud_builder import gerar_nuvem_palavras

from utils.excel_loader import carregar_e_normalizar
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
        ["Classificador de legendas", "🤖 Classificação", "🐦 Twitter"]
    )

    if pagina == "Classificador de legendas":
        _aba_classificador_legendas()
    elif pagina == "🐦 Twitter":
        _aba_twitter()
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
# PÁGINA — TWITTER / X
# =================================================
def _aba_twitter():
    st.subheader("Busca no Twitter/X")

    col1, col2 = st.columns(2)
    with col1:
        termo = st.text_input("Termo de busca", placeholder="ex: jaques wagner")
    with col2:
        dias = st.number_input(
            "Dias a buscar (a partir de ontem)",
            min_value=1, max_value=30, value=1
        )

    max_results = st.slider(
        "Máximo de tweets por dia", min_value=10, max_value=100, value=100, step=10
    )

    palavras_chave = st.text_input(
        "Palavras-chave para monitorar (separadas por vírgula, opcional)",
        placeholder="ex: master, traidor"
    )

    if st.button("Buscar tweets"):
        if not termo.strip():
            st.warning("Informe um termo de busca.")
        else:
            try:
                with st.spinner(f"Buscando tweets sobre \"{termo}\"..."):
                    df_twitter, contagens = buscar_periodo(
                        termo, int(dias), max_results=int(max_results)
                    )
                st.session_state.df_twitter = df_twitter
                st.session_state.termo_twitter = termo
                st.session_state.contagens_twitter = contagens
            except TwitterAPIError as err:
                st.error(f"⚠️ {err}")

    df_twitter = st.session_state.get("df_twitter")

    if df_twitter is not None and not df_twitter.empty:
        termo_buscado = st.session_state.get("termo_twitter", termo)

        st.markdown(f"**💬 Total de tweets coletados:** {len(df_twitter)}")

        contagens = st.session_state.get("contagens_twitter", [])
        if contagens:
            st.markdown("**📅 Menções por dia (contagem total da API):**")
            for item in contagens:
                st.markdown(f"- {item['data']}: {item['contagem']}")

        if palavras_chave.strip():
            st.markdown("**📊 Menções por palavra-chave:**")
            for termo_chave in [t.strip() for t in palavras_chave.split(",") if t.strip()]:
                qtd = df_twitter["Comment"].str.contains(
                    termo_chave, case=False, na=False
                ).sum()
                st.markdown(f"- **{termo_chave}:** {qtd}")

        st.dataframe(df_twitter, use_container_width=True)

        csv = df_twitter.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Baixar tweets (CSV)",
            data=csv,
            file_name=f"tweets_{termo_buscado.replace(' ', '_')}.csv",
            mime="text/csv"
        )

        st.subheader("☁️ Nuvem de Palavras")

        stopwords_extra = ["https", "nao"] + termo_buscado.lower().split()
        wc = gerar_nuvem_palavras(df_twitter["Comment"], palavras_ignoradas=stopwords_extra)

        if wc is None:
            st.info("Não há palavras suficientes para gerar a nuvem (tente reduzir a frequência mínima ou buscar mais dias).")
        else:
            st.image(wc.to_array(), use_container_width=True)

            buffer = io.BytesIO()
            wc.to_image().save(buffer, format="PNG")
            st.download_button(
                "⬇️ Baixar nuvem de palavras (PNG)",
                data=buffer.getvalue(),
                file_name=f"nuvem_{termo_buscado.replace(' ', '_')}.png",
                mime="image/png"
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