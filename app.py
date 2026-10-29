"""Interface web: streamlit run app.py"""

import pandas as pd
import streamlit as st

from assistente import Assistente
from assistente.llm import ClienteOpenAICompativel

st.set_page_config(page_title="Assistente de Chamados", page_icon="💬", layout="centered")
st.title("Assistente de Chamados Públicos")
st.caption("Pergunte em português. O modelo gera o SQL, o código executa em modo somente leitura e o modelo explica só o que os dados mostram.")


@st.cache_resource
def carregar() -> Assistente:
    return Assistente(ClienteOpenAICompativel())


EXEMPLOS = [
    "Qual categoria tem o maior tempo médio de resolução?",
    "Qual cidade tem o pior percentual de chamados dentro do SLA?",
    "Quantos chamados ainda estão abertos por cidade?",
    "Qual canal tem a melhor nota média dos cidadãos?",
]

if "historico" not in st.session_state:
    st.session_state.historico = []

with st.sidebar:
    st.subheader("Exemplos")
    for exemplo in EXEMPLOS:
        if st.button(exemplo, use_container_width=True):
            st.session_state.pendente = exemplo

pergunta = st.chat_input("Ex.: Quantos chamados de iluminação foram resolvidos em março?")
pergunta = pergunta or st.session_state.pop("pendente", None)

if pergunta:
    with st.spinner("Consultando a base..."):
        try:
            st.session_state.historico.append(carregar().perguntar(pergunta))
        except Exception as e:
            st.error(f"Não consegui falar com o modelo de linguagem. Confira LLM_BASE_URL e LLM_MODEL. Detalhe: {e}")

for r in reversed(st.session_state.historico):
    with st.chat_message("user"):
        st.write(r.pergunta)
    with st.chat_message("assistant"):
        st.write(r.texto)
        if r.erro:
            st.warning(r.erro)
        if r.sql:
            with st.expander("SQL e dados usados"):
                st.code(r.sql, language="sql")
                if r.colunas:
                    st.dataframe(pd.DataFrame(r.linhas, columns=r.colunas), hide_index=True)
