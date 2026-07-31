import streamlit as st
import pandas as pd
from config.schema import schema_classifier
from config.schema_classifier import schema_classifier_consolidado
from core.classificar_sentimentos import SentimentAnalysisPipeline
from core.classifier_legend import CaptionClassifier

import random



import os
from dotenv import load_dotenv
from core.comment_classifier import CommentClassifier

# -------------------------------------------------
# Configuração
# -------------------------------------------------
load_dotenv()

st.set_page_config("LabCaos", layout="wide")
st.title("Análise de Comentários - LabCaos")

# -------------------------------------------------
# Estado
# -------------------------------------------------
if "wc" not in st.session_state:
    st.session_state.wc = None

if "df_classificado" not in st.session_state:
    st.session_state.df_classificado = None

# -------------------------------------------------
# Upload
# -------------------------------------------------
files = st.file_uploader(
    "Carregue arquivos Excel",
    type=["xlsx", "xls"],
    accept_multiple_files=True
)

if not files:
    st.stop()

dfs = []


for f in files:
    # extrair o ID do nome do arquivo
#    match = re.search(r'ig-comments_(.*?)_', f.name)
#    post_id = match.group(1) if match else None
    if 'exportcomments' in f.name:
        df = pd.read_excel(f)
        df = df.rename(columns={'Username': 'Name',
                                "Display Name":"ProfileId"})
        if 'Likes' not in df.columns:
            df['Likes'] = None
        df = df[['Name', 'ProfileId', "Comment","Date","Likes"]]
    elif 'list' in f.name:
        df = pd.read_excel(f)
        if 'Likes' not in df.columns:
            df['Likes'] = None
        df = df[['Name', 'ProfileId', "Comment","Date","Likes"]]
    elif 'jaques_wagner' in f.name:
        df = pd.read_excel(f)
        if 'Likes' not in df.columns:
            df['Likes'] = None
        df = df.rename(columns={'mes_ano': 'Date',
                                "id":"ProfileId"})
        df['Name'] = df['ProfileId']
    elif 'tweet' in f.name:
        df = pd.read_excel(f, skiprows=6)
        df = df.dropna(subset = ['Unnamed: 0'])
        df = df.rename(columns={'Username': 'ProfileId',
                                "Tweet Text": "Comment"})
        if 'Likes' not in df.columns:
            df['Likes'] = None
        df = df[['Name', 'ProfileId', "Comment","Date","Likes"]]
    else:
        df = pd.read_excel(f, skiprows=6)
        df = df.dropna(subset = ['Unnamed: 0'])
        df = df.rename(columns={'Profile ID': 'ProfileId'})
        if 'Likes' not in df.columns:
            df['Likes'] = None
        df = df[['Name', 'ProfileId', "Comment","Date","Likes"]]

        
    
    # adicionar coluna com ID
#    df["post_id"] = post_id
    
    dfs.append(df)


df = pd.concat(dfs, ignore_index=True)

#df = pd.read_excel("C:/Users/luciano.santana/OneDrive - FGV/Documentos/LabCaos/Ronda JW/Semana 6 (04_05 - 08_05)/Dia 06_05/Comments/ruicostaoficial_comment_list_20260506.xlsx")
    
#df = df.drop_duplicates(subset = ['Name','Comment','Date'])

df['Comment'] = df['Comment'].str.replace('\n', '', regex=False)

if 'Likes' not in df.columns:
    df['Likes'] = None

#L = instaloader.Instaloader()

#shortcode = "DXu-sB8jcFD"

#post = instaloader.Post.from_shortcode(L.context, shortcode)

#n_comentarios = post.comments
#n_curtidas = post.likes

#st.write(f"Número de comentários: {n_comentarios}")
#st.write(f"Número de curtidas: {post.likes}")

# ── INDICADORES (antes do tratamento) ────────────────────────────────
total_comentarios = df["Comment"].dropna().shape[0]



#nome_arquivo = file.name
#rede_id = nome_arquivo.split("comment_")[1].replace(".xlsx", "")

#st.write("Nome do arquivo:", nome_arquivo)

# -------------------------------------------------
# Abas
# -------------------------------------------------
tab_wc, tab_cls = st.tabs(
    ["Classificador de legendas", "🤖 Classificação"]
)





# =================================================
# ABA 1 — NUVEM DE PALAVRAS
# =================================================
with tab_wc:
    st.subheader("Classificador de Legendas")

    legenda = st.text_area(
        "Cole a legenda",
        height=200
    )
    
    classifier = CaptionClassifier(api_key = os.getenv("OPENAI_API_KEY"))
    
    if st.button("Classificar"):
    
        if legenda.strip():
    
            resultado = classifier.classify(legenda)
    
            st.success(f"**Categoria:** {resultado['categoria']}")
# =================================================
# ABA 2 — CLASSIFICAÇÃO
# =================================================
with tab_cls:
    st.subheader("Classificação dos Comentários")
    
    contexto = st.text_area(
       "Contexto da classificação",
       placeholder="Ex: Comentários sobre investimentos em saúde na Bahia feitos por políticos"
   )
    
    opcao = st.radio(
    "Escolha a classificação:",
    ["Jaques Wagner", "Camaçari"]
)
    if opcao=="Jaques Wagner":
        # ── Menção ao PL 2531 ────────────────────────────────────────────────
#        df['menciona_projeto'] = df["Comment"].str.contains(
#            r'\b(PL|PEC)[\s\.\-]?\d+', case=False, na=False
#        )
        df['menciona_projeto'] = df["Comment"].str.contains(
            r'\b(?:PL|PEC)[\s\.\-]?\d+', case=False, na=False
)


        # Comentários duplicados: mesmo Name/ProfileId com o mesmo texto
        duplicados = (
            df[['Name', 'ProfileId', "Comment"]]
            .dropna(subset=["Comment"])
            .duplicated(subset=['Name', 'ProfileId', "Comment"])
            .sum()
        )


        comentarios_df = df[~df['menciona_projeto']].copy()
        
        # 🔹 remove NA
        comentarios_df = comentarios_df.dropna(subset=["Comment"])
        
        # 🔹 conta duplicados (antes de resolver)
#        duplicados = comentarios_df.duplicated(
#            subset=['Name', 'ProfileId', "Comment"]
#        ).sum()
        
        # 🔹 mantém o comentário com MAIS likes
        comentarios_df = (
            comentarios_df
            .sort_values(by="Likes", ascending=False)  # 🔥 chave
            .drop_duplicates(subset=['Name', 'ProfileId', "Comment"])
        )

#            mencoes_pl = df['menciona_projeto'].sum()
    else:
        comentarios_df = df

            
    comentarios = (
        comentarios_df["Comment"]
        .dropna()
        .astype(str)
        .tolist()
    )
    
    if len(comentarios) > 1000:
        comentarios1 = random.sample(comentarios, 1000)
    else:
        comentarios1 = comentarios
        
    
    if st.button("Classificar comentários"):
        

        classifier = CommentClassifier(
            api_key=os.getenv("OPENAI_API_KEY"),
            schema=schema_classifier,
            contexto = contexto
        )

        with st.spinner("Classificando comentários..."):
            resultado = classifier.classify(comentarios1)

        df_classificado_1 = pd.DataFrame(resultado["respostas"])
        
        # 🔹 cria a máscara (PL ou PEC)
        mask_projeto = df_classificado_1["motivo"].str.contains(
            r'\b(PL|PEC|Projeto de Lei)([\s\.\-]?\d+)?',
            case=False,
            na=False
        )        
        # 🔹 conta quantos têm PL/PEC
        n_projetos = mask_projeto.sum()
        
        
        # 🔹 mantém apenas os que NÃO têm
        st.session_state.df_classificado = df_classificado_1[~mask_projeto]

        st.success("Classificação concluída!")
        

    if st.session_state.df_classificado is not None:
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
        
        
        pipeline = SentimentAnalysisPipeline(
        api_key=os.getenv("OPENAI_API_KEY"),
        schema=schema_classifier_consolidado,
        contexto=contexto
        )
        
        df_base = st.session_state.df_classificado
        
        if "df_resultado" not in st.session_state:
            pipeline = SentimentAnalysisPipeline(
                api_key=os.getenv("OPENAI_API_KEY"),
                schema=schema_classifier_consolidado,
                contexto=contexto
            )

            st.session_state.df_resultado = pipeline.run(df_base)
 
        df_resultado = pipeline.run(df_base)
    
        resultado = df_resultado.iloc[0]
        
        n_pos = (df_base['classificacao'] == 'positivo').sum()
        n_neu = (df_base['classificacao'] == 'neutro').sum()
        n_neg = (df_base['classificacao'] == 'negativo').sum()
        
        total = len(df_base)

        p_pos = (n_pos / total) if total > 0 else 0
        p_neu = (n_neu / total) if total > 0 else 0
        p_neg = (n_neg / total) if total > 0 else 0
        
        est_pos = round(p_pos * len(comentarios))
        est_neu = round(p_neu * len(comentarios))
        est_neg = round(p_neg * len(comentarios))
        
        total_validos = est_pos+est_neu+est_neg

        st.subheader("📊 Análise Geral")
        
        
        
        st.markdown("---")
        
        if opcao == "Jaques Wagner":
            
            mencoes_pl = df['menciona_projeto'].sum() + n_projetos
            
            st.markdown(
                f"**💬 Total de comentários:** {total_comentarios}"
            )
            
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


#        st.write(resultado["review_comments"])
        
        topicos = resultado["main_topics"]
        
        st.markdown(
            f"🧠 **Temas principais:** {' | '.join(t.capitalize() for t in topicos)}"
        )
        
        st.markdown(
            f"🟢 **Comentários Positivos:** {est_pos} ({p_pos:.2%})"
        )
        if resultado["review_comments_positives"]:
            st.markdown(resultado["review_comments_positives"])
        else:
            st.markdown("_Sem comentários positivos_")
        
        st.markdown(
            f"🟡 **Comentários Neutros:** {est_neu} ({p_neu:.2%})"
        )
        if resultado["review_comments_neutral"]:
            st.markdown(resultado["review_comments_neutral"])
        else:
            st.markdown("_Sem comentários neutros_")
        
        st.markdown(
            f"🔴 **Comentários Negativos:** {est_neg} ({p_neg:.2%})"
        )
        if resultado["review_comments_negative"]:
            st.markdown(resultado["review_comments_negative"])
        else:
            st.markdown("_Sem comentários negativos_")

#            st.markdown(f"- {t}")
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
