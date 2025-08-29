#==================Libs=====================
import pyodbc
import pandas as pd
import geopandas as gpd
import json
from datetime import datetime
import unicodedata
import re
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from fpdf import FPDF
#===================Funções===================
from function.carta_formatar_endereço import formatar_endereco

#==================SQL Server=====================
def conectar_banco():
    secrets = st.secrets["database"]
    return pyodbc.connect(
        f"DRIVER={{SQL Server}};"
        f"SERVER={secrets.server};"
        f"DATABASE={secrets.database};"
        f"UID={secrets.user};"
        f"PWD={secrets.password};"
        f"Trusted_Connection=no;"
    )

@st.cache_data
def carregar_dados_clientes():
    conexao = conectar_banco()
    df = pd.read_sql("SELECT * FROM VW_VETEAGRO_CLIENTESMES", conexao)
    conexao.close()
    df['DATA'] = pd.to_datetime(df['DATA'], dayfirst=True)
    return df

@st.cache_data
def carregar_dados_carta():
    conexao = conectar_banco()
    df = pd.read_sql('''
        SELECT (C.CLI_CODI+CLI_CPF+CLI_NOME) AS SEARCH, OBS_CODI, OBS_DTOBS, OBS_TEXTO, C.CLI_NOME AS NOME FROM CLIENTE C
        LEFT JOIN TBCLIENTE_OBSERVACAO T ON T.CLI_CODI = C.CLI_CODI
        WHERE T.CLI_CODI IS NOT NULL
        AND T.OBS_TEXTO LIKE '%ENDERECO=%'
    ''', conexao)
    conexao.close()
    return df

@st.cache_data
def carregar_dados_conta():
    conexao = conectar_banco()
    df = pd.read_sql("""SELECT
  VEN_CODI,
  VEN_NOME,
  SALDO_ATUAL,
  ROUND(SUM(CASE
              WHEN DATEDIFF(MONTH, CCV_DATA, GETDATE()) = 2
              THEN CASE WHEN CCV_TIPO = 'C' THEN CCV_VALO ELSE -CCV_VALO END
              ELSE 0
            END), 2) AS VALOR_MES3,
  ROUND(SUM(CASE
              WHEN DATEDIFF(MONTH, CCV_DATA, GETDATE()) = 1
              THEN CASE WHEN CCV_TIPO = 'C' THEN CCV_VALO ELSE -CCV_VALO END
              ELSE 0
            END), 2) AS VALOR_MES2,
  ROUND(SUM(CASE
              WHEN DATEDIFF(MONTH, CCV_DATA, GETDATE()) = 0
              THEN CASE WHEN CCV_TIPO = 'C' THEN CCV_VALO ELSE -CCV_VALO END
              ELSE 0
            END), 2) AS VALOR_MES1
FROM
  TBCONTACORRENTEVEND
  INNER JOIN VW_VETEAGRO_CCORRENTE_ATUAL ON TBCONTACORRENTEVEND.VEN_CODI = VW_VETEAGRO_CCORRENTE_ATUAL.VEND_CODI
WHERE
  DATEDIFF(MONTH, CCV_DATA, GETDATE()) BETWEEN 0 AND 2
GROUP BY
  VEN_NOME, VEN_CODI, SALDO_ATUAL""", conexao)
    conexao.close()
    return df

@st.cache_data
def carregar_dados_producao():
    conexao = conectar_banco()
    df = pd.read_sql("SELECT * FROM VW_VETEAGRO_PRODUCAO_AUT order by CODIGO_PRODUCAO DESC", conexao)
    conexao.close()
    return df

@st.cache_data
def carregar_giro(ano_inicio, mes_inicio, ano_fim, mes_fim):
    coenxao = pd.read_sql()
    df = pd.read_sql("""
    
    """)

@st.cache_data
def carregar_mapa_equipe():
    conexao = conectar_banco()
    df = pd.read_sql('''select VW_LISTA_BASE_CLIENTES.VEN_NOME, CIDADE, BAIRRO from VW_LISTA_BASE_CLIENTES
		RIGHT JOIN VENDEDOR ON VENDEDOR.VEN_CODI = VW_LISTA_BASE_CLIENTES.VEN_CODI
        where CIDADE = 'FORTALEZA'
		AND NOT VW_LISTA_BASE_CLIENTES.VEN_NOME IS NULL
		AND VEN_OBSE LIKE '%SIM%'
        GROUP BY VW_LISTA_BASE_CLIENTES.VEN_NOME, CIDADE, BAIRRO''', conexao)
    conexao.close()
    return df

#==================Tratamento=====================
def normalizar_texto(texto, case='upper', substituir_especiais=False):
    if isinstance(texto, str):
        # Remove acentuação
        nfkd_form = unicodedata.normalize('NFKD', texto)
        texto_sem_acento = nfkd_form.encode('ASCII', 'ignore').decode('utf-8')

        #Remove os espaços extras
        texto_sem_acento = texto_sem_acento.strip()

        #Substituir caracteres especiais (se solicitado)
        if substituir_especiais:
            texto_sem_acento = re.sub(r'[^A-Za-z0-9\s]', '', texto_sem_acento)

        #Ajustar case
        if case == 'upper':
            texto_sem_acento = texto_sem_acento.upper()
        elif case == 'lower':
            texto_sem_acento = texto_sem_acento.lower()
        
        return texto_sem_acento
    return texto

def normalizar_colunas_dataframe(df, colunas=None, case='upper', substituir_especiais=False):
    if colunas is None:
        colunas = df.select_dtypes(include='object').columns.tolist()

    for coluna in colunas:
        if coluna in df.columns:
            df[coluna] = df[coluna].apply(lambda x: normalizar_texto(x, case, substituir_especiais))
        else:
            return None
    return df

def data_hoje_formalizada():

    data_hoje = datetime.today()

    meses_pt = {
        1: "janeiro", 2: "fevereiro", 3: "março", 4: "abril",
        5: "maio", 6: "junho", 7: "julho", 8: "agosto",
        9: "setembro", 10: "outubro", 11: "novembro", 12: "dezembro"
    }

    dia = data_hoje.day
    mes = meses_pt[data_hoje.month]
    ano = data_hoje.year

    data_formatada = f"{dia} de {mes} de {ano}"
    return data_formatada

#==================Configuração da Página=====================
st.set_page_config(page_title="Vet Agro", layout="wide")

#==================Controle de Tela=====================
if "tela" not in st.session_state:
    st.session_state["tela"] = "inicio"
#==================Tela Inicial=====================
if st.session_state["tela"] == "inicio":
    st.title("🔷 Dashboard Vet&Agro")
    st.subheader("Selecione uma opção")

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📋 Clientes Cadastrados", use_container_width=True):
                st.session_state["tela"] = "cadastro"
                st.rerun()
        with col2:
            if st.button("📋 Carta de Endereço", use_container_width=True):
                st.session_state["tela"] = "carta"
                st.rerun()
        with col3:
            if st.button("💳 Conta Corrente", use_container_width=True):
                st.session_state["tela"] = "conta"
                st.rerun()

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🧂 Auditoria da Produção", use_container_width=True):
                st.session_state["tela"] = "producao"
                st.rerun()
        with col2:
            if st.button("🌍 Mapa da Equipe - Capital", use_container_width=True):
                st.session_state["tela"] = "mapa_equipe"
                st.rerun()
#==================Tela de Cadastro=====================
elif st.session_state["tela"] == "cadastro":
    col_esq, col_dir = st.columns([9, 2])
    with col_dir:
        if st.button("🔙 Voltar ao Início"):
            st.session_state["tela"] = "inicio"
            st.rerun()

    st.title("Cadastro de Clientes - Vet&Agro")
    st.subheader("🔎 Visualização de Clientes - Mês Atual")

    # Botão para recarregar dados
    if st.button("🔄 Recarregar dados"):
        st.cache_data.clear()
        st.rerun()

    df_clientes_raw = carregar_dados_clientes()

    df_clientes_raw.columns = [normalizar_texto(col, case='upper') for col in df_clientes_raw.columns]
    df_clientes_raw = normalizar_colunas_dataframe(df_clientes_raw, case='upper')

    # Sidebar - Filtros
    st.sidebar.header("FILTROS")
    anos_disponiveis = df_clientes_raw['DATA'].dt.year.sort_values().unique()
    ano_selecionado = st.sidebar.selectbox("Ano", anos_disponiveis)

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

    equipes_disponiveis = df_clientes_raw['EQUIPE'].dropna().unique()
    equipe_selecionada = st.sidebar.multiselect("Equipe", equipes_disponiveis, default=equipes_disponiveis)

    # Aplicar filtros
    df_filtrado = df_clientes_raw[
        (df_clientes_raw['DATA'].dt.year == ano_selecionado) &
        (df_clientes_raw['DATA'].dt.month == mes_selecionado) &
        (df_clientes_raw['EQUIPE'].isin(equipe_selecionada))
    ]

    # Exibir dados
    df_visualizacao = df_filtrado.drop(columns=['EQUIPE'])
    df_visualizacao['DATA'] = df_visualizacao['DATA'].dt.strftime("%d/%m/%Y")
    df_visualizacao = df_visualizacao.sort_values(by="DATA", ascending=False)
    st.dataframe(df_visualizacao, use_container_width=True, hide_index=True)

    # Graficos e sessões
    st.subheader("📊 Distribuição")
    col_vend, col_eqp = st.tabs(["Por Vendedor", "Por Equipe"])

    # Gráfico por Vendedor
    with col_vend:
        clientes_por_vendedor = df_filtrado.groupby("VENDEDOR").size().reset_index(name="Quantidade de Clientes")
        fig_vendedor = px.bar(clientes_por_vendedor, x="VENDEDOR", y="Quantidade de Clientes", color="VENDEDOR")
        st.plotly_chart(fig_vendedor, use_container_width=True)

    # Gráfico por Equipe
    with col_eqp:
        clientes_por_equipe = df_filtrado.groupby("EQUIPE").size().reset_index(name="Quantidade de Clientes")
        fig_equipe = px.bar(clientes_por_equipe, x="EQUIPE", y="Quantidade de Clientes", color="EQUIPE")
        st.plotly_chart(fig_equipe, use_container_width=True)
#=======================Tela de Carta de Endereço=========================
elif st.session_state["tela"] == "carta":
    
    df_carta_raw = carregar_dados_carta()
    df_carta_raw = normalizar_colunas_dataframe(
        df_carta_raw,
        case="upper",
        substituir_especiais=False
    )
    df_carta_raw.columns = [normalizar_texto(col, case='upper') for col in df_carta_raw.columns]

    st.title("Cartas de Endereço - Vet&Agro")

    col1, col2, col3 = st.columns([4, 5, 20.5])

    with col1:
        if st.button("🔙 Voltar ao Início"):
            st.session_state["tela"] = "inicio"
            st.rerun()

    with col2:
        if st.button("🔄 Recarregar dados"):
            st.cache_data.clear()
            st.rerun()

    with col3:
        @st.dialog("Cadastro de Carta:")
        def cadastro_dialog():
            Codigo = st.text_input("Cód. do Cliente", placeholder="Ex: 0010106575", max_chars=10)
            col1, col2 = st.columns([1, 1])
            with col1: 
                Rua = st.text_input("Endereço")
            with col2:
                Num = st.text_input("Nº")
            Bairro = st.text_input("Bairro")
            col3, col4= st.columns([1, 1])
            with col3: 
                Cidade = st.text_input("Cidade")
            with col4:
                Uf = st.text_input("UF")
            Cep = st.text_input("CEP")
            Observacao = st.text_input("Observação")
            if st.button("Salvar"):
                text = f'ENDERECO={Rua};{Num};{Bairro};{Cidade};{Uf};{Cep};{Observacao}'
                conexao = conectar_banco()
                cursor = conexao.cursor()
                sql = f"EXECUTE OBSERVACAO_CLIENTE ?, ?"
                cursor.execute(sql, (Codigo, text))
                conexao.commit()
                cursor.close()
                conexao.close()
                st.rerun()
                
                
        if "Cadastro_dialog" not in st.session_state:
            if st.button("Cadastrar"):
                cadastro_dialog()


    st.markdown("<h4>🔎 Pesquisar Clientes</h4>", unsafe_allow_html=True)

    text = st.text_input("", placeholder="CPF, Código ou Nome")

    df_resumo = df_carta_raw.drop_duplicates(subset=["NOME"])

    if text:
        df_filtrado = df_resumo[df_resumo["SEARCH"].str.contains(text, case=False, na=False)]
    else:
        df_filtrado = df_resumo

    # Configura a tabela apenas com a coluna que quer mostrar (ex.: NOME)
    gb = GridOptionsBuilder.from_dataframe(df_filtrado[["NOME"]])
    gb.configure_selection(selection_mode='single', use_checkbox=True)
    grid_options = gb.build()

    # Mostra o AgGrid filtrado
    grid_response = AgGrid(
        df_filtrado[["NOME"]],
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme="streamlit",
        height=200,
        allow_unsafe_jscode=True
    )

    linha_selecionada = grid_response["selected_rows"]

    if linha_selecionada is not None and not linha_selecionada.empty:

        nome_selecionado = linha_selecionada.iloc[0]["NOME"]

        # Filtra no df_carta_raw pela coluna CLI_NOME
        dados_cliente = df_carta_raw[df_carta_raw["NOME"] == nome_selecionado][
            ["OBS_CODI", "OBS_DTOBS", "OBS_TEXTO"]
        ]

        st.markdown("<h5>📋 Endereços</h5>", unsafe_allow_html=True)

        for idx, row in dados_cliente.iterrows():
            texto_formatado = formatar_endereco(row.OBS_TEXTO)

            @st.dialog("Informações complementares:")
            def dialog(item):
                st.write(f"Endereço {int(item)} selecionado.")

                nota = st.text_input("Nota fiscal:", placeholder="Apenas números...")

                linha = dados_cliente.loc[dados_cliente["OBS_CODI"] == item].iloc[0]
                endereco = linha["OBS_TEXTO"]

                if st.button("Gerar Carta"):
                    # --- Gera o PDF ---
                    pdf = FPDF()
                    pdf.add_page()
                    pdf.set_font("Times", "B",size=12)
                    pdf.image(r".\public\logovetagro.png", x=(pdf.w - 40) / 2, y=30, w=40)
                    pdf.ln(65)
                    pdf.multi_cell(0, 10, txt=f"OBS.: As mercadorias constantes na NF ({nota}) que estão sendo enviadas para o cliente {nome_selecionado}, terá o seu local de ENTREGA sediado no endereço a seguir:", align="J")
                    pdf.ln(20)
                    pdf.multi_cell(0, 10, txt=f"{formatar_endereco(endereco)}", align="C")
                    pdf.multi_cell(0, 10, txt=f"Observações:", align="J")
                    pdf.ln(40)
                    pdf.multi_cell(0, 10, txt=f"Fortaleza, {data_hoje_formalizada()}", align="C")
                    pdf.set_font("Times", "B",size=15)
                    pdf.ln(10)
                    pdf.multi_cell(0, 10, txt=f"Vet&Agro", align="C")
                    pdf.set_font("Times", "B",size=10)
                    pdf.multi_cell(0, 5, txt=f"Veterinaria e Agricola", align="C")

                    # Pega o conteúdo do PDF em bytes
                    pdf_bytes = pdf.output(dest='S').encode('latin1')

                    # Botão de download no Streamlit
                    st.download_button(
                        label="📥 Baixar Carta PDF",
                        data=pdf_bytes,
                        file_name="documento.pdf",
                        mime="application/pdf"
                    )
                    
            # Lista endereços e abre o diálogo
            if "dialog" not in st.session_state:
                st.text(f"Endereço {int(row.OBS_CODI)} - Última atualização: {row.OBS_DTOBS}")
                st.text(texto_formatado)

                if st.button("Selecionar endereço", key=row.OBS_CODI):
                    dialog(row.OBS_CODI)
#==================Tela Conta Corrente=====================
elif st.session_state["tela"] == "conta":

    df_conta_raw = carregar_dados_conta()

    st.title("Conta Corrente - Vendedor")

    col1, col2, col3 = st.columns([1.2, 1.2, 5.5])

    with col1:
        if st.button("🔙 Voltar ao Início"):
            st.session_state["tela"] = "inicio"
            st.rerun()

    with col2:
        if st.button("🔄 Recarregar dados"):
            st.cache_data.clear()
            st.rerun()

    with col3:
        if "DATA_PRODUCAO" in df_conta_raw.columns and not df_conta_raw.empty:
            ultima_data = df_conta_raw.iloc[0]["DATA_PRODUCAO"]
            st.markdown(
                f"<div style='margin-top: 15px;'>Última atualização: <b>{ultima_data}</b></div>",
                unsafe_allow_html=True
            )
    st.subheader("🔎 Visualização de Vendedores - Saldo Atual")

    # Sidebar - Filtros
    st.sidebar.header("FILTROS")

    filtro_saldo = st.sidebar.radio(
        "Situação",
        options=["Todos", "Positivados", "Negativados"],
        index=0
        )

    # Aplicar filtro de saldo
    if filtro_saldo == "Positivados":
        df_conta_raw = df_conta_raw[df_conta_raw['SALDO_ATUAL'] > 0]
    elif filtro_saldo == "Negativados":
        df_conta_raw = df_conta_raw[df_conta_raw['SALDO_ATUAL'] < 0]

    st.dataframe(df_conta_raw.drop(columns=['VALOR_MES3','VALOR_MES2', 'VALOR_MES1']), use_container_width=True, hide_index=True)

    st.subheader("📊 Distribuição")
    col_espelho, col_3meses = st.tabs(["Em Espelho", "Em 3 Meses"])

    with col_espelho:
        df_conta_raw = df_conta_raw.sort_values(by="SALDO_ATUAL")
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x = df_conta_raw['SALDO_ATUAL'],
            y = df_conta_raw['VEN_NOME'],
            orientation = "h",
            marker_color = df_conta_raw['SALDO_ATUAL'].apply(lambda x: 'crimson' if x < 0 else 'seagreen'),
            text = df_conta_raw['SALDO_ATUAL'],
            textposition = "auto" 
        ))

        fig.update_layout(
            title="Espelho do Conta Corrente",
            xaxis_title="Saldo Atual (em R$)",
            yaxis_title="Vendedor",
            xaxis=dict(zeroline=True, zerolinewidth=2, zerolinecolor='gray'),
            plot_bgcolor='rgba(0,0,0,0)',
            height=1000
        )

        st.plotly_chart(fig, use_container_width=True)
    
    with col_3meses:
        df_conta_raw = df_conta_raw.rename(columns={
            'VALOR_MES3': 'Ultimos 60 dias',
            'VALOR_MES2': 'Ultimos 30 dias',
            'VALOR_MES1': 'Mês atual',
            'VEN_NOME': 'Vendedores'
        })

        df_conta_raw = df_conta_raw.melt(id_vars='Vendedores', value_vars=['Ultimos 60 dias', 'Ultimos 30 dias', 'Mês atual'], var_name='Período', value_name='Valores (Em R$)')

        fig = px.bar(df_conta_raw, x='Vendedores', y='Valores (Em R$)', color='Período', barmode='group', title='Movimentação dos Últimos 3 Meses por Vendedor')

        st.plotly_chart(fig, use_container_width=True)
#==================Tela Producao Industria=====================
elif st.session_state["tela"] == "producao":

    st.title("Auditoria de Produção - Indústria")

    df_raw = carregar_dados_producao()

    col1, col2, col3 = st.columns([1.2, 1.2, 5.5])

    st.subheader("🔎 Listagem de Ordens")
    with col1:
        if st.button("🔙 Voltar ao Início"):
            st.session_state["tela"] = "inicio"
            st.rerun()

    with col2:
        if st.button("🔄 Recarregar dados"):
            st.cache_data.clear()
            st.rerun()

    with col3:
        if "DATA_PRODUCAO" in df_raw.columns and not df_raw.empty:
            ultima_data = df_raw.iloc[0]["DATA_PRODUCAO"]
            st.markdown(
                f"<div style='margin-top: 15px;'>Última atualização: <b>{ultima_data}</b></div>",
                unsafe_allow_html=True
            )

    # Normaliza colunas que participam da comparação
    df_raw = normalizar_colunas_dataframe(
        df_raw,
        case="upper",
        substituir_especiais=False
    )
    df_raw.columns = [normalizar_texto(col, case='upper') for col in df_raw.columns]

    # Cria um dataframe de resumo (tabela de cima)
    df_resumo = df_raw[[
        "DATA_PRODUCAO", "DESC_PRODUTO_FINAL",
        "PRD_QTPEDI", "PRD_QTPROD", "LOTE_FINAL", "FABRICACAO_FINAL", "VALIDADE_FINAL",
        "CODIGO_PRODUCAO"
    ]].drop_duplicates()

    # Construção da AgGrid apenas com colunas visíveis (ocultando CODIGO_PRODUCAO, se quiser)
    gb = GridOptionsBuilder.from_dataframe(df_resumo)
    gb.configure_column("DATA_PRODUCAO", header_name="DATA PRODUÇÃO")
    gb.configure_column("DESC_PRODUTO_FINAL", header_name="PRODUTO PRODUZIDO")
    gb.configure_column("PRD_QTPEDI", header_name="QTDE. PEDIDA")
    gb.configure_column("PRD_QTPROD", header_name="QTDE. PRODUZIDA")
    gb.configure_column("LOTE_FINAL", header_name="LOTE")
    gb.configure_column("FABRICACAO_FINAL", header_name="DATA FABRICAÇÃO")
    gb.configure_column("VALIDADE_FINAL", header_name="DATA VALIDADE")
    gb.configure_column("CODIGO_PRODUCAO", hide=True)
    
    gb.configure_selection(selection_mode='single', use_checkbox=True)
    grid_options = gb.build()

    grid_response = AgGrid(
        df_resumo,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme="streamlit",
        height=300,
        allow_unsafe_jscode=True
    )
                          
    linha_selecionada = grid_response["selected_rows"]

    # Se linha_selecionada for DataFrame:
    if linha_selecionada is not None and not linha_selecionada.empty:
        batidas = int(linha_selecionada.iloc[0]['PRD_QTPEDI']/500) if linha_selecionada.iloc[0]['PRD_QTPEDI'] else 0
        # pega a primeira linha como dict
        primeira_linha = linha_selecionada.iloc[0].to_dict()

        if isinstance(primeira_linha, dict):
            cod_producao = normalizar_texto(primeira_linha.get("CODIGO_PRODUCAO", ""), case="upper")

            st.subheader("🧪 Ingredientes / Matéria-prima Utilizada")
            st.text(f"Quantidade de batida: {batidas}")

            df_detalhe = df_raw[df_raw["CODIGO_PRODUCAO"] == cod_producao]

            if batidas > 0:
                df_detalhe["QT_USADA_MP"] = df_detalhe["QT_USADA_MP"] / batidas
            else:
                df_detalhe["QT_USADA_MP"] = 0

            # Verifica quais matérias-primas se repetem
            repetidos = df_detalhe["COD_MATERIA_PRIMA"].duplicated(keep=False)

            # Divide em duplicados e únicos
            df_duplicados = df_detalhe[repetidos]
            df_unicos = df_detalhe[~repetidos]

            # Primeiro agrupa duplicados por COD + DESC + LOTE (para somar lotes iguais)
            df_dup_sum = df_duplicados.groupby(
                ["COD_MATERIA_PRIMA", "DESC_MATERIA_PRIMA", "LOTE_MATERIA_PRIMA"],
                as_index=False
            ).agg({"QT_USADA_MP": "sum"})

            # Depois agrupa por COD + DESC e junta os lotes somados em string
            df_grouped = df_dup_sum.groupby(
                ["COD_MATERIA_PRIMA", "DESC_MATERIA_PRIMA"], as_index=False
            ).agg({
                "QT_USADA_MP": "sum",
                "LOTE_MATERIA_PRIMA": lambda x: " / ".join(
                    f"{lote} = {qtde:.2f}" 
                    for lote, qtde in zip(
                        df_dup_sum.loc[x.index, "LOTE_MATERIA_PRIMA"], 
                        df_dup_sum.loc[x.index, "QT_USADA_MP"]
                    )
                )
            })

            # Padroniza colunas dos únicos
            df_unicos = df_unicos[[
                "COD_MATERIA_PRIMA", "DESC_MATERIA_PRIMA", "QT_USADA_MP", "LOTE_MATERIA_PRIMA"
            ]]

            # Junta tudo
            df_final = pd.concat([df_grouped, df_unicos], ignore_index=True)

            # Renomeia para exibição
            df_final = df_final.rename(columns={
                "COD_MATERIA_PRIMA": "CÓDIGO",
                "DESC_MATERIA_PRIMA": "PRODUTO",
                "QT_USADA_MP": "QTDE. USADA P/ BATIDA",
                "LOTE_MATERIA_PRIMA": "LOTES"
            })

            st.dataframe(
                df_final,
                use_container_width=True,
                hide_index=True
            )
    else:
        st.subheader("🧪 Ingredientes / Matéria-prima Utilizada")
        st.write("Nenhuma linha selecionada.")
#==================Tela Mapa da Equipe=====================
elif st.session_state["tela"] == "mapa_equipe":

    df = carregar_mapa_equipe()

    with open(r".\public\Bairros_de_Fortaleza.geojson", "r", encoding="utf-8") as f:
        geojson_data = json.load(f)

    st.title("Mapa dos Bairros de Fortaleza - Vendedores")

    # ========================
    # Padronizar nomes (maiúsculas e sem espaços extras)
    # ========================
    df["BAIRRO"] = df["BAIRRO"].str.strip().str.upper()
    for feature in geojson_data["features"]:
        feature["properties"]["Nome"] = feature["properties"]["Nome"].strip().upper()

    # ========================
    # Criar um dicionário Bairro -> Lista de Vendedores
    # ========================
    bairro_vendedor = (
        df.groupby("BAIRRO")["VEN_NOME"]
        .apply(lambda x: list(set(x)))
        .to_dict()
    )

    # ========================
    # Selectbox de vendedores
    # ========================
    vendedores = sorted(df["VEN_NOME"].unique())
    vendedor_selecionado = st.selectbox("Selecione o vendedor", ["Todos"] + vendedores)

    # ========================
    # Criar mapa
    # ========================
    m = folium.Map(location=[-3.73, -38.54], zoom_start=11)

    # Cor para os bairros do vendedor selecionado
    cor_vendedor = "#5BD1D7"
    cor_outros = "lightgray"

    def get_color_filter(bairro):
        if vendedor_selecionado == "Todos":
            return cor_vendedor if bairro in bairro_vendedor else cor_outros
        elif bairro in bairro_vendedor and vendedor_selecionado in bairro_vendedor[bairro]:
            return cor_vendedor
        else:
            return cor_outros

    # ========================
    # Adicionar GeoJSON com estilo
    # ========================
    folium.GeoJson(
        geojson_data,
        name="Bairros",
        tooltip=folium.GeoJsonTooltip(
            fields=["Nome"],
            aliases=["Bairro:"],
            localize=True
        ),
        style_function=lambda feature: {
            "fillColor": get_color_filter(feature["properties"]["Nome"]),
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.6,
        }
    ).add_to(m)

    # ========================
    # Mostrar no Streamlit
    # ========================
    st_folium(m, width=800, height=600)
