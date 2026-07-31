import streamlit as st

# =========================================================
# USUÁRIOS CADASTRADOS (fixos)
# Adicione/edite os usuários e senhas aqui.
# =========================================================
USUARIOS = {
    "admin": "admin123",
    "usuario1": "senha1",
    "usuario2": "senha2",
}


def inicializar_sessao():
    """Garante que as chaves de sessão usadas pela aplicação existam."""
    if "autenticado" not in st.session_state:
        st.session_state.autenticado = False
        st.session_state.usuario = None

    if "df_classificado" not in st.session_state:
        st.session_state.df_classificado = None


def esta_autenticado():
    return st.session_state.get("autenticado", False)


def tela_login():
    st.title("🔒 Login")
    st.write("Entre com seu usuário e senha para continuar.")

    with st.form("form_login"):
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        if usuario in USUARIOS and USUARIOS[usuario] == senha:
            st.session_state.autenticado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
