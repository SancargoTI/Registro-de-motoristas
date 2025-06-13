import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import re
from io import BytesIO
from PIL import Image

logo = Image.open("logo.png")

with st.sidebar:
    st.image(logo, width=400)

# Conectar ao banco de dados
conn = sqlite3.connect("controle_veiculos.db", check_same_thread=False)
cursor = conn.cursor()

# Criar tabelas se não existirem
cursor.execute("""
CREATE TABLE IF NOT EXISTS movimentacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    data TEXT NOT NULL,
    placa TEXT NOT NULL,
    motorista TEXT NOT NULL,
    observacoes TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS horarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movimentacao_id INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    horario TEXT NOT NULL,
    data_hora_registro TEXT NOT NULL,
    UNIQUE(movimentacao_id, tipo),
    FOREIGN KEY (movimentacao_id) REFERENCES movimentacoes(id)
)
""")
conn.commit()

# Função para validar e formatar horário
def formatar_horario(h):
    h = re.sub(r"[^0-9]", "", h)
    if len(h) == 4:
        return h[:2] + ":" + h[2:]
    elif len(h) == 5 and h[2] == ":":
        return h
    return ""

# Página de registro
import streamlit as st
from datetime import date
import locale

def pagina_registro():
    st.title("🚗 Registro de Movimentação de Veículos")

    # Tenta definir o locale para português do Brasil
    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')  # Linux/Mac
    except:
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR')    # Windows
        except:
            st.warning("Não foi possível aplicar locale em pt_BR. Datas podem aparecer em inglês.")

    # Campo de data
    data = st.date_input("Data da movimentação", value=date.today())

    # Exibe a data formatada: "13 de junho de 2025"
    st.write("Data selecionada:", data.strftime("%d/%m/%Y"))


    placa = st.selectbox("Placa do veículo", ["EXX-8377", "CUC-4484", "FFE-3621", "GCJ-5593", "CLJ-7430", "FVK-2208", "GFN-0103", "GHG-2987", "EWU-0343", "GGH-7498", "GEB-8J29", "GJT-2922", "GBR-3051", "GJI-7304", "FOR-5443", "FYJ-4112", "EWU-1697", "GGH-9299", "GIZ-3259", "GHA-2G03", "GHX-7868", "EWU-1695", "EWU-0342", "EWU-1696", "EWU-4093", "EWU-4A94", "EOE-8590", "EWU-1698", "EWU-1085", "EWU-4092", "EOE-9893"])  # lista mantida igual
    motorista = st.selectbox("Nome do motorista", ["ALAN SANTOS MATOS", "ALISSON ALVES MARTINS SILVA", "ALTAMIRO PEREIRA DE ALMEIDA", "ANDERSON MARCELO GALDINO", "ANDRE PEREIRA FONSECA", "ANTONIO LISBOA FARIAS JUNIOR", "CARLOS HENRIQUE NASCIMENTO NICOLUCCI", "CARLOS ROBERTO GLACIANO", "DANIEL LUIS DA SILVA", "DANIEL JOSE RIBEIRO", "EDSON RODRIGUES DOS SANTOS", "ELIAS GOMES BARBOSA", "EUCLIDES LOURENCO DE OLIVEIRA", "EVERALDO GABRIEL DA SILVA", "GIVALDO BARBOSA DE JESUS", "LUIS FERNANDO DOS SANTOS", "JHONY DE SOUZA", "NILTON SANTOS DA SILVA", "TIAGO DE JESUS SANTANA", "WUELLISON TIAGO DE SIQUEIRA VAZ"])  # lista mantida igual
    observacoes = st.text_area("Observações (opcional)")
    if st.button("Registrar movimentação"):
        cursor.execute("INSERT INTO movimentacoes (data, placa, motorista, observacoes) VALUES (?, ?, ?, ?)",
                       (data.strftime("%d-%m-%Y"), placa, motorista, observacoes))
        conn.commit()
        st.success("Movimentação registrada com sucesso!")

# Página de preenchimento de horários
def pagina_preencher_horarios():
    st.title("🕒 Preencher Horários")
    data_selecionada = st.date_input("Selecionar data", value=date.today())
    data_str = data_selecionada.strftime("%d-%m-%Y")
    df = pd.read_sql_query("SELECT * FROM movimentacoes WHERE data = ? ORDER BY motorista", conn, params=(data_str,))
    if df.empty:
        st.info("Nenhuma movimentação registrada para esta data.")
        return

    tipos = ["Entrada na empresa", "Saída com veículo", "Retorno com veículo", "Saída da empresa"]
    ordem_tipos = {tipo: i for i, tipo in enumerate(tipos)}

    for _, row in df.iterrows():
        st.markdown(f"**{row['motorista']} - {row['placa']}**")
        cols = st.columns(len(tipos))
        horarios_input = {}

        for i, tipo in enumerate(tipos):
            key = f"{tipo}_{row['id']}"
            valor_inicial = pd.read_sql_query(
                "SELECT horario FROM horarios WHERE movimentacao_id = ? AND tipo = ?",
                conn, params=(row['id'], tipo)
            )
            valor = valor_inicial["horario"].iloc[0] if not valor_inicial.empty else ""
            entrada = cols[i].text_input(tipo, value=valor, max_chars=5, key=key)
            horario_formatado = formatar_horario(entrada)
            horarios_input[tipo] = horario_formatado

        if st.button(f"Salvar horários de {row['motorista']}", key=f"btn_{row['id']}"):
            agora = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
            for tipo, horario in horarios_input.items():
                if re.match(r"^\d{2}:\d{2}$", horario):
                    cursor.execute("""
                        INSERT INTO horarios (movimentacao_id, tipo, horario, data_hora_registro)
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT(movimentacao_id, tipo) DO UPDATE SET
                        horario=excluded.horario, data_hora_registro=excluded.data_hora_registro
                    """, (row['id'], tipo, horario, agora))
            conn.commit()
            st.success("Horários salvos com sucesso!")

    # Exibir tabela consolidada com uma linha por motorista
    st.markdown("### Horários registrados")
    query = """
    SELECT m.motorista, m.placa, h.tipo, h.horario
    FROM movimentacoes m
    JOIN horarios h ON m.id = h.movimentacao_id
    WHERE m.data = ?
    """
    df_horarios = pd.read_sql_query(query, conn, params=(data_str,))
    if not df_horarios.empty:
        tipos = ["Entrada na empresa", "Saída com veículo", "Retorno com veículo", "Saída da empresa"]
        ordem_tipos = {tipo: i for i, tipo in enumerate(tipos)}
        df_horarios["ordem"] = df_horarios["tipo"].map(ordem_tipos)
        df_horarios = df_horarios.sort_values(by=["motorista", "placa", "ordem"])
        tabela = df_horarios.pivot_table(
            index=["motorista", "placa"],
            columns="tipo",
            values="horario",
            aggfunc="first"
        ).reset_index()
        # Reordena as colunas conforme solicitado
        colunas = ["motorista", "placa"] + tipos
        tabela = tabela.reindex(columns=colunas)
        st.dataframe(tabela)

# Página de relatório
def pagina_relatorio():
    st.title("📊 Relatório de Movimentações")
    tipo_filtro = st.radio("Filtrar por:", ["Motorista", "Placa"])
    if tipo_filtro == "Motorista":
        valor = st.selectbox("Selecione o motorista", ["ALAN SANTOS MATOS", "ALISSON ALVES MARTINS SILVA", "ALTAMIRO PEREIRA DE ALMEIDA", "ANDERSON MARCELO GALDINO", "ANDRE PEREIRA FONSECA", "ANTONIO LISBOA FARIAS JUNIOR", "CARLOS HENRIQUE NASCIMENTO NICOLUCCI", "CARLOS ROBERTO GLACIANO", "DANIEL LUIS DA SILVA", "DANIEL JOSE RIBEIRO", "EDSON RODRIGUES DOS SANTOS", "ELIAS GOMES BARBOSA", "EUCLIDES LOURENCO DE OLIVEIRA", "EVERALDO GABRIEL DA SILVA", "GIVALDO BARBOSA DE JESUS", "LUIS FERNANDO DOS SANTOS", "JHONY DE SOUZA", "NILTON SANTOS DA SILVA", "TIAGO DE JESUS SANTANA", "WUELLISON TIAGO DE SIQUEIRA VAZ"])  # lista mantida igual
        campo = "motorista"
    else:
        valor = st.selectbox("Selecione a placa", ["EXX-8377", "CUC-4484", "FFE-3621", "GCJ-5593", "CLJ-7430", "FVK-2208", "GFN-0103", "GHG-2987", "EWU-0343", "GGH-7498", "GEB-8J29", "GJT-2922", "GBR-3051", "GJI-7304", "FOR-5443", "FYJ-4112", "EWU-1697", "GGH-9299", "GIZ-3259", "GHA-2G03", "GHX-7868", "EWU-1695", "EWU-0342", "EWU-1696", "EWU-4093", "EWU-4A94", "EOE-8590", "EWU-1698", "EWU-1085", "EWU-4092", "EOE-9893"]) # lista mantida igual
        campo = "placa"

    data_inicio = st.date_input("Data inicial", value=date.today())
    data_fim = st.date_input("Data final", value=date.today())

    if st.button("Gerar relatório"):
        query = f"""
        SELECT m.data, m.motorista, m.placa, h.tipo, h.horario
        FROM movimentacoes m
        JOIN horarios h ON m.id = h.movimentacao_id
        WHERE m.{campo} = ? AND m.data BETWEEN ? AND ?
        """
        df = pd.read_sql_query(query, conn, params=(valor, data_inicio.strftime("%d-%m-%Y"), data_fim.strftime("%d-%m-%Y")))
        if df.empty:
            st.warning("Nenhum registro encontrado para o filtro selecionado.")
        else:
            tipos = ["Entrada na empresa", "Saída com veículo", "Retorno com veículo", "Saída da empresa"]
            ordem_tipos = {tipo: i for i, tipo in enumerate(tipos)}
            df["ordem"] = df["tipo"].map(ordem_tipos)
            df = df.sort_values(by=["data", "ordem"])
            df = df.drop(columns="ordem")
            tabela = df.pivot_table(
                index=["data", "motorista", "placa"],
                columns="tipo",
                values="horario",
                aggfunc="first"
            ).reset_index()
            st.dataframe(tabela)

            output = BytesIO()
            tabela.to_excel(output, index=False, engine='openpyxl')
            output.seek(0)
            st.download_button(
                label="📥 Baixar Excel",
                data=output,
                file_name="relatorio_movimentacoes.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# Menu lateral moderno com botões estilizados

st.sidebar.markdown("## Navegação")
pagina = None
b1 = st.sidebar.button("🚗 Registro de Movimentação", use_container_width=True)
b2 = st.sidebar.button("🕒 Preencher Horários", use_container_width=True)
b3 = st.sidebar.button("📊 Relatório de Movimentações", use_container_width=True)

# Efeito visual: destaque o botão selecionado
if 'pagina' not in st.session_state:
    st.session_state.pagina = "Registro de Movimentação"
if b1:
    st.session_state.pagina = "Registro de Movimentação"
if b2:
    st.session_state.pagina = "Preencher Horários"
if b3:
    st.session_state.pagina = "Relatório de Movimentações"

pagina = st.session_state.pagina

# CSS para botões cinza com borda grossa
st.markdown("""
    <style>
    .stButton > button {
        background: #e0e0e0;
        color: #222;
        border: 3px solid #b0b0b0;
        border-radius: 8px;
        padding: 0.5em 0;
        margin-bottom: 0.5em;
        font-weight: 600;
        font-size: 1.05em;
        box-shadow: 0 2px 8px rgba(160,160,160,0.08);
        transition: 0.2s;
    }
    .stButton > button:hover {
        background: #cccccc;
        color: #111;
        transform: scale(1.03);
        box-shadow: 0 4px 16px rgba(160,160,160,0.15);
        border-color: #888;
    }
    </style>
""", unsafe_allow_html=True)

if pagina == "Registro de Movimentação":
    pagina_registro()
elif pagina == "Preencher Horários":
    pagina_preencher_horarios()
elif pagina == "Relatório de Movimentações":
    pagina_relatorio()
