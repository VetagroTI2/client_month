#==================Libs Matriz=====================
import pyodbc
import pandas as pd
from datetime import datetime
#==================Libs do Streamlit=====================
import streamlit as st
import plotly.express as px

# Configurações iniciais
st.set_page_config(page_title="Vet Agro - Clientes", layout="wide")

# Título e botão de recarga
st.title("Cadastro de Clientes - Vet&Agro")
st.subheader("Visualização de Clientes - Mês Atual")

# Botão para forçar atualização dos dados
if st.button("🔄 Recarregar dados"):
    st.cache_data.clear()
    st.rerun()

# Função para conectar ao SQL Server
@st.cache_data
def carregar_dados():
    secrets = st.secrets["database"]

    conexao = pyodbc.connect(
        f"DRIVER={{SQL Server}};"
        f"SERVER={secrets.server};"
        f"DATABASE={secrets.database};"
        f"UID={secrets.user};"
        f"PWD={secrets.password};"
        f"Trusted_Connection=no;"
    )

    query = """SELECT * FROM VW_VETEAGRO_CLIENTESMES"""
    
    df = pd.read_sql(query, conexao)
    conexao.close()
    
    df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True)
    return df

# Carregar dados
df_clientes_raw = carregar_dados()

# Sidebar - Filtros
st.sidebar.header("FILTROS")

# Filtro por Ano
anos_disponiveis = df_clientes_raw['DATA'].dt.year.sort_values().unique()
ano_selecionado = st.sidebar.selectbox("Ano", anos_disponiveis)

# Filtro por Mês
meses_dict = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
meses_keys = list(meses_dict.keys())
mes_atual = datetime.now().month
mes_selecionado = st.sidebar.selectbox(
    "Mês",
    meses_keys,
    index=meses_keys.index(mes_atual),
    format_func=lambda x: meses_dict[x]
)

# Filtro por Equipe (usar todos disponíveis)
equipes_disponiveis = df_clientes_raw['EQUIPE'].dropna().unique()
equipe_selecionada = st.sidebar.multiselect("Equipe", equipes_disponiveis, default=equipes_disponiveis)

# Aplicar filtros
df_filtrado = df_clientes_raw[
    (df_clientes_raw['DATA'].dt.year == ano_selecionado) &
    (df_clientes_raw['DATA'].dt.month == mes_selecionado) &
    (df_clientes_raw['EQUIPE'].isin(equipe_selecionada))
]

# Exibir tabela sem coluna EQUIPE e sem índice
df_visualizacao = df_filtrado.drop(columns=['EQUIPE'])
df_visualizacao = df_visualizacao.sort_values(by="DATA", ascending=False)
st.dataframe(df_visualizacao, use_container_width=True, hide_index=True)

# Gráfico de clientes por VENDEDOR
st.markdown("### Distribuição por Vendedor")
clientes_por_vendedor = df_filtrado.groupby("VENDEDOR").size().reset_index(name="Quantidade de Clientes")

fig_vendedor = px.bar(
    clientes_por_vendedor,
    x="VENDEDOR",
    y="Quantidade de Clientes",
    title="Clientes por Vendedor",
    labels={"VENDEDOR": "Vendedor", "Quantidade de Clientes": "Clientes"},
    color="VENDEDOR"
)
st.plotly_chart(fig_vendedor, use_container_width=True)

# Novo gráfico: Clientes por Equipe
st.markdown("### Distribuição por Equipe")
clientes_por_equipe = df_filtrado.groupby("EQUIPE").size().reset_index(name="Quantidade de Clientes")

fig_equipe = px.bar(
    clientes_por_equipe,
    x="EQUIPE",
    y="Quantidade de Clientes",
    title="Clientes por Equipe",
    labels={"EQUIPE": "Equipe", "Quantidade de Clientes": "Clientes"},
    color="EQUIPE"
)
st.plotly_chart(fig_equipe, use_container_width=True)
