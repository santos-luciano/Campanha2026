import numpy as np
from wordcloud import WordCloud

from core.text_cleaner import TextCleaner
from core.text_analyzer import TextAnalyzer


def gerar_nuvem_palavras(comentarios, palavras_ignoradas=None, freq_minima=3):
    """
    Gera uma WordCloud (formato oval) a partir de uma série/lista de comentários.

    Retorna o objeto WordCloud pronto (use .to_array() para exibir em Streamlit
    ou .to_image() para salvar/baixar), ou None se não houver palavras
    suficientes após os filtros.
    """
    palavras_ignoradas = [p.lower() for p in (palavras_ignoradas or [])]

    cleaner = TextCleaner(min_len=3)
    analyzer = TextAnalyzer(cleaner)

    df_freq = analyzer.word_frequency(comentarios)
    df_freq = df_freq[df_freq['frequencia'] >= freq_minima]
    df_freq = df_freq[~df_freq['palavra'].str.lower().isin(palavras_ignoradas)]

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
        max_words=150,
        mask=mask.astype(np.uint8),
        contour_width=0,
    ).generate_from_frequencies(freq_dict)

    return wc
