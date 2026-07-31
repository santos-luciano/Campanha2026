import streamlit as st
from dotenv import load_dotenv

from auth import tela_login, esta_autenticado, inicializar_sessao
from pages_app.analise import tela_principal

load_dotenv()

st.set_page_config(page_title="LabCaos", page_icon="🔒", layout="wide")

inicializar_sessao()

if esta_autenticado():
    tela_principal()
else:
    tela_login()
