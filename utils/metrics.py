def marcar_mencao_projeto(df, coluna="Comment"):
    """Adiciona a coluna 'menciona_projeto' indicando se o comentário
    cita um PL ou PEC."""
    df = df.copy()
    df['menciona_projeto'] = df[coluna].str.contains(
        r'\b(?:PL|PEC)[\s\.\-]?\d+', case=False, na=False
    )
    return df


def contar_duplicados(df):
    """Conta comentários duplicados (mesmo Name/ProfileId/Comment)."""
    return (
        df[['Name', 'ProfileId', "Comment"]]
        .dropna(subset=["Comment"])
        .duplicated(subset=['Name', 'ProfileId', "Comment"])
        .sum()
    )


def filtrar_comentarios_validos(df):
    """Remove comentários que mencionam PL/PEC e duplicados,
    mantendo o de maior número de likes em cada grupo."""
#    comentarios_df = df[~df['menciona_projeto']].copy()
    comentarios_df = df.dropna(subset=["Comment"])
    comentarios_df = (
        comentarios_df
        .sort_values(by="Likes", ascending=False)
        .drop_duplicates(subset=['Name', 'ProfileId', "Comment"])
    )
    return comentarios_df


def marcar_mencao_pl_no_motivo(df_classificado, coluna="motivo"):
    """Retorna a máscara booleana das linhas cujo motivo cita
    PL, PEC ou 'Projeto de Lei'."""
    return df_classificado[coluna].str.contains(
        r'\b(PL|PEC|Projeto de Lei)([\s\.\-]?\d+)?',
        case=False,
        na=False
    )


def calcular_percentuais(df_base):
    """Calcula quantidade e percentual de comentários classificados
    como positivo/neutro/negativo na amostra."""
    total = len(df_base)

    n_pos = (df_base['classificacao'] == 'positivo').sum()
    n_neu = (df_base['classificacao'] == 'neutro').sum()
    n_neg = (df_base['classificacao'] == 'negativo').sum()

    p_pos = (n_pos / total) if total > 0 else 0
    p_neu = (n_neu / total) if total > 0 else 0
    p_neg = (n_neg / total) if total > 0 else 0

    return {
        "n_pos": n_pos, "n_neu": n_neu, "n_neg": n_neg,
        "p_pos": p_pos, "p_neu": p_neu, "p_neg": p_neg,
    }


def estimar_totais(percentuais, total_comentarios):
    """Projeta os percentuais da amostra classificada para o total
    de comentários carregados."""
    est_pos = round(percentuais["p_pos"] * total_comentarios)
    est_neu = round(percentuais["p_neu"] * total_comentarios)
    est_neg = round(percentuais["p_neg"] * total_comentarios)
    return est_pos, est_neu, est_neg

def calcular_distribuicao_geral(df, coluna="classificacao"):
    contagem = df[coluna].value_counts()
    percentual = df[coluna].value_counts(normalize=True) * 100
    resumo = pd.DataFrame({
        "quantidade": contagem,
        "percentual": percentual.round(2)
    })
    return resumo

def extrair_rede_e_data(nome_arquivo):
    nome = nome_arquivo.lower()
    if "facebook" in nome:
        rede = "Facebook"
    elif "instagram" in nome:
        rede = "Instagram"
    else:
        rede = "Outro"

    match = re.search(r"(\d{2})_(\d{2})_(\d{4})", nome_arquivo)
    if match:
        dia, mes, ano = match.groups()
        data = pd.to_datetime(f"{ano}-{mes}-{dia}", errors="coerce")
    else:
        data = pd.NaT

    return pd.Series({"rede_social": rede, "data": data})

def normalizar_para_exibicao(df):
    df_norm = df.copy()
    for col in df_norm.columns:
        # força tudo que não é numérico puro a virar string, evitando mistura de tipos
        if df_norm[col].dtype == "object":
            df_norm[col] = df_norm[col].apply(
                lambda x: str(x) if not isinstance(x, (int, float, type(None))) else x
            )
    return df_norm