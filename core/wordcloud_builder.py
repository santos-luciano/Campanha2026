import io

import nltk
import numpy as np
import pandas as pd
import streamlit as st
from wordcloud import WordCloud

from core.text_cleaner import TextCleaner
from core.text_analyzer import TextAnalyzer


def _garantir_stopwords_nltk():
    """O TextCleaner depende do corpus 'stopwords' do NLTK, que não vem
    pré-instalado no Streamlit Cloud — baixa sob demanda, uma vez só."""
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)

# Stopwords genéricas (links, termos institucionais, lixo de URL) que
# atrapalham qualquer nuvem de comentário de rede social. Cada aba pode
# somar palavras específicas do próprio contexto por cima dessa lista.
STOPWORDS_PADRAO = [
    'https', 'jaques', 'pra', 'wagner', 'so', 'oficial', 'nao',
    'oficialcaetano', 'laisa', 'figueiredo', 'prefeito', 'caetano',
    'igsh', 'www', 'mwjjztdootvlmhhwnq', 'instagram', 'facebook',
    'set', 'php', 'type', 'fbid', 'time', 'photo', 'jaqueswagner',
    'co', 'ja', 'vai', 'camacari',
]


def gerar_nuvem_palavras(
    comentarios,
    palavras_ignoradas=None,
    freq_minima=1,
    min_len=2,
    max_palavras_frequencia=100,
    max_palavras_nuvem=150,
    remover_numeros=True,
):
    """
    Gera uma WordCloud (formato oval) a partir de uma série/lista de comentários.

    Parâmetros:
    - palavras_ignoradas: lista extra de stopwords (some com STOPWORDS_PADRAO
      se você passar `palavras_ignoradas=STOPWORDS_PADRAO + [...]`).
    - freq_minima: frequência mínima da palavra para entrar na nuvem.
    - min_len: tamanho mínimo da palavra (usado na limpeza do texto).
    - max_palavras_frequencia: quantas palavras (as mais frequentes) considerar
      antes de desenhar a nuvem.
    - max_palavras_nuvem: limite repassado ao WordCloud (max_words).
    - remover_numeros: descarta tokens que são só dígitos (ex: "2024").

    Retorna o objeto WordCloud pronto (use .to_array() para exibir em Streamlit
    ou .to_image() para salvar/baixar), ou None se não houver palavras
    suficientes após os filtros.
    """
    palavras_ignoradas = [p.lower() for p in (palavras_ignoradas or [])]

    _garantir_stopwords_nltk()
    cleaner = TextCleaner(min_len=min_len)
    analyzer = TextAnalyzer(cleaner)

    # TextAnalyzer.extract_words espera uma Series (usa .dropna()) — aceita
    # tanto uma Series quanto uma lista/tupla aqui, convertendo se preciso.
    comentarios_series = (
        comentarios if isinstance(comentarios, pd.Series) else pd.Series(comentarios)
    )

    df_freq = analyzer.word_frequency(comentarios_series)
    df_freq = df_freq[df_freq['frequencia'] >= freq_minima]

    if remover_numeros:
        df_freq = df_freq[~df_freq['palavra'].str.fullmatch(r'\d+')]

    df_freq = df_freq[~df_freq['palavra'].str.lower().isin(palavras_ignoradas)]
    df_freq = df_freq.head(max_palavras_frequencia)

    freq_dict = dict(zip(df_freq['palavra'], df_freq['frequencia']))

    if not freq_dict:
        return None

    # Máscara oval
    x, y = np.ogrid[:500, :1000]
    mask = (x - 250) ** 2 / 250 ** 2 + (y - 500) ** 2 / 500 ** 2 > 1
    mask = 255 * mask.astype(int)

    wc = WordCloud(
        width=1000,
        height=500,
        background_color=None,
        mode='RGBA',
        max_words=max_palavras_nuvem,
        mask=mask.astype(np.uint8),
        contour_width=0,
    ).generate_from_frequencies(freq_dict)

    return wc


def exibir_nuvem_palavras(
    comentarios,
    titulo="☁️ Nuvem de Palavras",
    nome_arquivo="nuvem_palavras",
    palavras_extra_ignoradas=None,
    largura_exibicao=600,
    **kwargs,
):
    """
    Helper de UI: gera a nuvem (usando STOPWORDS_PADRAO + palavras_extra_ignoradas)
    e já cuida de exibir na tela + botão de download em PNG.

    Chame isso direto de qualquer aba, por exemplo:

        exibir_nuvem_palavras(
            df["Comment"],
            titulo="☁️ Nuvem de Palavras - Comentários",
            nome_arquivo="nuvem_comentarios",
            palavras_extra_ignoradas=["algumapalavra"],
        )

    `largura_exibicao` controla o tamanho (em pixels) mostrado na tela —
    a imagem baixada em PNG mantém a resolução completa, independente disso.
    Qualquer parâmetro extra (freq_minima, min_len, etc.) é repassado
    direto para gerar_nuvem_palavras.
    """
    palavras_ignoradas = STOPWORDS_PADRAO + list(palavras_extra_ignoradas or [])

    st.subheader(titulo)

    # tuple() torna os argumentos hasheáveis, permitindo cachear com
    # st.cache_data — sem isso, a nuvem seria recalculada em TODO rerun
    # do Streamlit (qualquer clique/digitação na página), não só quando
    # os comentários realmente mudam.
    wc = _gerar_nuvem_com_cache(
        tuple(str(c) for c in comentarios),
        tuple(sorted(palavras_ignoradas)),
        kwargs.get("freq_minima", 1),
        kwargs.get("min_len", 2),
        kwargs.get("max_palavras_frequencia", 100),
        kwargs.get("max_palavras_nuvem", 150),
        kwargs.get("remover_numeros", True),
    )

    if wc is None:
        st.info("Não há palavras suficientes para gerar a nuvem com os filtros atuais.")
        return

    col_esquerda, col_centro, col_direita = st.columns([1, 2, 1])
    with col_centro:
        st.image(wc.to_array(), width=largura_exibicao)

    buffer = io.BytesIO()
    wc.to_image().save(buffer, format="PNG")
    st.download_button(
        "⬇️ Baixar nuvem de palavras (PNG)",
        data=buffer.getvalue(),
        file_name=f"{nome_arquivo}.png",
        mime="image/png",
        key=f"download_{nome_arquivo}",
    )


@st.cache_data(show_spinner=False)
def _gerar_nuvem_com_cache(
    comentarios_tupla,
    palavras_ignoradas_tupla,
    freq_minima,
    min_len,
    max_palavras_frequencia,
    max_palavras_nuvem,
    remover_numeros,
):
    """Wrapper cacheado de gerar_nuvem_palavras — os argumentos precisam
    ser hasheáveis (tuplas), por isso não recebe listas/Series direto."""
    return gerar_nuvem_palavras(
        list(comentarios_tupla),
        palavras_ignoradas=list(palavras_ignoradas_tupla),
        freq_minima=freq_minima,
        min_len=min_len,
        max_palavras_frequencia=max_palavras_frequencia,
        max_palavras_nuvem=max_palavras_nuvem,
        remover_numeros=remover_numeros,
    )