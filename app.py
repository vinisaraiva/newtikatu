import streamlit as st
from streamlit_navigation_bar import st_navbar
from streamlit_extras.row import row
from PIL import Image
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static
import pandas as pd
import numpy as np
import datetime
import re
import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff
import requests
from openai import OpenAI
import json
import random
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime
from dic_parametros import dados_parametros
from estilocolunas import estilo_colunas
import base64
import pydeck as pdk
from pydeck.types import String
import textwrap
import google.auth
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fpdf import FPDF
from io import BytesIO
import plotly.io as pio
from translations import get_translation

pio.kaleido.scope.default_format = "png"

# Função para tradução
def t(key):
    return get_translation(key, st.session_state.lang)

# Inicialização do estado da linguagem
if 'lang' not in st.session_state:
    st.session_state.lang = 'pt-br'

# URLs das APIs do SheetDB
SHEETDB_DADOS_API_URL = "https://sheetdb.io/api/v1/85u4y2iziptre"
SHEETDB_RIOCHAMAGUNGA_API_URL = "https://sheetdb.io/api/v1/vlop1cs9uqewu"


# Token do Mapbox
mapbox_token = "pk.eyJ1IjoidmluaXNhcmFpdmEiLCJhIjoiY20wb25ocG9hMGF1ZTJrbzlmZm5haWFlcyJ9.XnczMEcsq_NTNTOFeCxzxA"

client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

# Configuração inicial da página
st.set_page_config(page_title=t("Water Quality Analysis"), page_icon=":bar_chart:", layout="wide")

# Definição das páginas
pages = ["Home", "Monitoring", "Registration", "Make Your Analysis"]
translated_pages = [t(page) for page in pages]

# Função para enviar email usando SendGrid
def send_email(to_email, subject, message_text):
    api_key = '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'
    message = Mail(
        from_email='alertas.tikatu@gmail.com',
        to_emails=to_email,
        subject=subject,
        plain_text_content=message_text)
    
    try:
        sg = SendGridAPIClient(api_key)
        sg.send(message)
    except Exception as e:
        raise Exception(f"{t('Error sending email')}: {str(e)}")

# Função para carregar os dados via API do SheetDB
def load_data():
    """Carrega os dados dos usuários e dos rios a partir das APIs e retorna dois DataFrames."""
    try:
        dados_response = requests.get(SHEETDB_DADOS_API_URL)
        riochamagunga_response = requests.get(SHEETDB_RIOCHAMAGUNGA_API_URL)

        if dados_response.status_code != 200:
            st.error(t("Error loading user data. Status code: {code}").format(code=dados_response.status_code))
            return None, None
    
        if riochamagunga_response.status_code != 200:
            st.error(t("Error loading river data. Status code: {code}").format(code=riochamagunga_response.status_code))
            return None, None
     
        try:
            dados_df = pd.DataFrame(dados_response.json())
            riochamagunga_df = pd.DataFrame(riochamagunga_response.json())
        except ValueError as e:
            st.error(t("Error converting data to DataFrame: {error}").format(error=str(e)))
            return None, None

        if 'RIO' not in riochamagunga_df.columns:
            st.error(t("Column 'RIO' not found in river monitoring data."))
            return None, None

        if 'EMAIL' not in dados_df.columns:
            st.error(t("Column 'EMAIL' not found in user data."))
            return None, None

        return dados_df, riochamagunga_df
    except Exception as e:
        st.error(t("Error trying to load data: {error}").format(error=str(e)))
        return None, None

# Função para verificar parâmetros e enviar alertas
def check_river_parameters_and_alert(dados_df, riochamagunga_df):
    limits = {
        'TURBIDEZ (NTU)': {'min': 0, 'max': 100},
        'CONDUTIVIDADE': {'min': 0, 'max': 300},
        'pH': {'min': 6.0, 'max': 9.0},
        'TEMPERATURA': {'min': 0, 'max': 40},
        'SALINIDADE': {'min': 0, 'max': 35}
    }
    
    data_atual = datetime.now().strftime('%d/%m/%Y')
    alertas_por_usuario = {}

    for index, row in dados_df.iterrows():
        selected_rio = row['RIOS SELECIONADOS']
        user_email = row['EMAIL']
        user_name = row['NOME']
        
        rio_data = riochamagunga_df[(riochamagunga_df['RIO'] == selected_rio.upper()) & (riochamagunga_df['DATA_COLETA'] == data_atual)]
        
        alert_body = t("Hello {name},\n\nIn the monitoring of the river {river}, on {date}, the following parameters were found outside the indices according to CONAMA:").format(name=user_name, river=selected_rio, date=data_atual) + "\n\n"
        parametros_fora = False
        alertas_por_parametro = {}
        
        for _, rio_row in rio_data.iterrows():
            ponto_coleta = rio_row['PONTOS']
            for param, limit in limits.items():
                value = rio_row[param]
                try:
                    value = float(str(value).replace(",", "."))
                except ValueError:
                    continue
                
                if not pd.isnull(value) and (value < limit['min'] or value > limit['max']):
                    parametros_fora = True
                    if param not in alertas_por_parametro:
                        alertas_por_parametro[param] = []
                    alertas_por_parametro[param].append(
                        t("Value found at collection point {point}: {value}\n"
                          "Minimum limit: {min}\n"
                          "Maximum limit: {max}\n").format(point=ponto_coleta, value=value, min=limit['min'], max=limit['max'])
                    )
        
        if parametros_fora:
            for param, alertas in alertas_por_parametro.items():
                alert_body += t("Parameter name: {param}\n").format(param=param)
                for alerta in alertas:
                    alert_body += alerta
                alert_body += "\n"
            
            if user_email not in alertas_por_usuario:
                alertas_por_usuario[user_email] = ""
            alertas_por_usuario[user_email] += alert_body

    try:
        for user_email, alert_body in alertas_por_usuario.items():
            send_email(user_email, t("TIKATU - River Monitoring Alert on {date}").format(date=data_atual), alert_body)
        st.success(t("Monitoring check completed successfully!"))
    except Exception as e:
        st.error(str(e))

# Página de cadastro e simulação
def cadastro_e_simulacao():
    st.subheader(t("User Registration"), divider='blue')
    dados_df, _ = load_data()
    if dados_df is None:
        return  # Se ocorrer erro ao carregar os dados, a função é interrompida

    col1, col2 = st.columns(2, gap="medium")
    opcoes_rios = ["CHAMAGUNGA", "RIO DOS MANGUES"]
    with col1:
        nome = st.text_input(t("Name"))
        email = st.text_input(t("Email"))
       #rios_selecionados = st.text_input(t("Selected River"))
       #Usando o st.selectbox para selecionar um dos rios
        rios_selecionados = st.selectbox(t("Selected River"), opcoes_rios)
    
        if st.button(t("Register")):
            new_data = pd.DataFrame({
                "ID": [len(dados_df) + 1],
                "NOME": [nome],
                "EMAIL": [email],
                "RIOS SELECIONADOS": [rios_selecionados],
                "DATA DE CADASTRO": [pd.Timestamp.now().strftime('%d/%m/%Y')]
            })
    
            response = requests.post(SHEETDB_DADOS_API_URL, json={"data": new_data.to_dict(orient="records")})
            if response.status_code == 201:
                st.success(t("User registered successfully!"))
            else:
                st.error(t("Error registering user: {code}").format(code=response.status_code))
    with col2:
        st.info(t("Register to receive alerts about parameters outside the ideal levels of the selected river."))
        st.image("acesso.png")
        
    st.header(t("Schedule Simulation"))
    if st.button(t("Run Monitoring Check")):
        _, riochamagunga_df = load_data()
        if dados_df is not None and riochamagunga_df is not None:
            check_river_parameters_and_alert(dados_df, riochamagunga_df)
        else:
            st.error(t("Unable to perform verification due to errors in data loading."))

# Função para criar PDF com a análise
def criar_pdf(analise_texto):
    pdf_buffer = BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    logo_path = 'logotikatu.png'
    logo_img = ImageReader(logo_path)
    c.drawImage(logo_img, 72, height - 100, width=100, preserveAspectRatio=True, mask='auto')

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2.0, height - 120, t("Water Quality Analysis Report"))

    c.setFont("Helvetica", 12)
    data_atual = datetime.now().strftime('%d/%m/%Y')
    c.drawCentredString(width / 2.0, height - 140, t("Date: {date}").format(date=data_atual))

    c.setFont("Helvetica", 12)
    text_object = c.beginText(72, height - 180)
    wrapped_text = textwrap.fill(analise_texto, 85)
    text_object.textLines(wrapped_text)
    c.drawText(text_object)

    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer

# Nova página de análise da qualidade da água
def pagina_analise_agua():
    st.subheader(t("Custom Water Analysis"), divider='green')
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container(border=True):
            st.caption(t("Parametros Observados"))
            ph = st.number_input(t("Enter pH value:"), min_value=0.0, max_value=14.0, step=0.1)
            condutividade = st.number_input(t("Enter Electrical Conductivity value (µS/cm):"), min_value=0.0, step=0.1)
            turbidez = st.number_input(t("Enter Turbidity value (NTU):"), min_value=0.0, step=0.1)
            od = st.number_input(t("Enter Dissolved Oxygen value (mg/L):"), min_value=0.0, step=0.1)
            temperatura = st.number_input(t("Enter Water Temperature (°C):"), min_value=0.0, step=0.1)
    with col2:
        with st.container(border=True):
            st.caption(t("Environmental Conditions"))
            local_coleta = st.selectbox(t("Select the collection site:"), [t("Lake"), t("River"), t("Dam"), t("Other")])
            tipo_corpo_agua = st.selectbox(t("Type of water body:"), [t("Still water"), t("Running water")])
            condicoes_climaticas = st.selectbox(t("Recent weather conditions:"), [t("Dry weather"), t("Recent rain"), t("Other")])
            atividades_humanas = st.selectbox(t("Nearby human activities:"), [t("Construction work"), t("Agriculture"), t("Nearby sewage"), t("None")])
            utilizacao = st.selectbox(t("What will be the use of the water?"), [t("Aquaculture"), t("Agriculture"), t("Human consumption"), t("Sanitation"), t("Industrial use"), t("Other")])
    with col3:
        with st.container(border=True):
            st.caption(t("Spatial and Temporal Data"))
            data_coleta = st.date_input(t("Collection date"))
            hora_coleta = st.time_input(t("Collection time"))
            localizacao = st.text_input(t("Location coordinates (latitude, longitude) (Optional)"))

    if st.button(t("Generate Analysis")):
        prompt = f"""
        {t('Analysis of water collected in a')} {local_coleta}:
        {t('Collection date')}: {data_coleta} {t('at')} {hora_coleta}.
        {t('Location')}: {localizacao}.
        
        {t('Environmental conditions')}:
        - {t('Type of water body')}: {tipo_corpo_agua}
        - {t('Recent weather conditions')}: {condicoes_climaticas}
        - {t('Nearby human activities')}: {atividades_humanas}
        - {t('What will be the use of the water')}: {utilizacao}
        
        {t('Physicochemical parameters')}:
        - pH: {ph}
        
        - {t('Electrical Conductivity')}: {condutividade} µS/cm
        - {t('Turbidity')}: {turbidez} NTU
        - {t('Dissolved Oxygen')}: {od} mg/L
        - {t('Temperature')}: {temperatura} °C
        
        {t('Act as an expert with a PhD in water parameter analysis, but you need to respond with language accessible to diverse audiences. Generate an initial analysis of water quality based on this information.')}
        """

        with st.spinner(t('Generating requested analysis...')):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                response_text = response.choices[0].message.content
            except Exception as e:
                st.error(t("Error generating analysis: {error}").format(error=str(e)))
                response_text = None

            if response_text:
                st.success(response_text)

                # Criar e permitir o download do PDF com a análise gerada
                pdf_output = criar_pdf(response_text)
                st.download_button(
                    label=t("Download Analysis"),
                    data=pdf_output,
                    file_name="relatoriotikatu.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                pdf_output.close()

# Estilos de navegação e layout
styles = {
    "nav": {
        "background-color": "#0B8DC8B3",
        "justify-content": "flex-start",
        "padding-left": "5px",
        "padding-right": "0px",
        "display": "flex",
        "width": "100%",
        "align-items": "center",
        "height": "70px",
        "box-sizing": "border-box",
    },
    "img": {
        "padding-right": "25px",
        "padding-left": "0px",
        "margin-left": "0px",
        "height": "60px",
        "object-fit": "contain",
    },
    "div": {
        "max-width": "none",
        "padding-left": "0px",
        "display": "flex",
        "align-items": "center",
        "height": "100%",
        "margin-left": "0",
    },
    "span": {
        "color": "rgb(49, 51, 63)",
        "padding": "0.4045rem 0.4045rem",
        "display": "flex",
        "align-items": "center",
        "justify-content": "center",
        "height": "100%",
        "font-size": "18px",
        "padding-right": "10px",
        "padding-left": "10px",
    },
    "active": {
        "background-color": "rgba(255, 255, 255, 0.25)",
        "height": "70px",

    },
    "hover": {
        "background-color": "rgba(255, 255, 255, 0.35)",
        "height": "70px",
    },
}

# Função para criar a barra de navegação com botões de tradução
def create_navbar_with_translation(pages, logo_path, styles):
    col1, col2, col3 = st.columns([8, 1, 1])
    with col1:
        selected_page = st_navbar(pages, logo_path=logo_path, styles=styles)
    
    # Estilos para os botões de tradução
    button_style = """
        <style>
        div.stButton > button {
            background-color: #0B8DC8B3;
            color: #31333F;
            border: 1px solid white;
            padding: 0.4045rem 0.3rem;
            font-size: 18px;
            height: 70px;
            width: 100%;
        }
        div.stButton > button:hover {
            background-color: rgba(255, 255, 255, 0.35);
        }
        </style>
    """
    st.markdown(button_style, unsafe_allow_html=True)
    
    with col2:
        if st.button('ENG', key='eng_button_navbar'):
            st.session_state.lang = 'en'
            st.rerun()
    with col3:
        if st.button('PT-BR', key='pt_button_navbar'):
            st.session_state.lang = 'pt-br'
            st.rerun()
    
    return selected_page

parent_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(parent_dir, "tikatu.svg")
page = create_navbar_with_translation(translated_pages, logo_path=logo_path, styles=styles)

mystyle = '''
    <style>
        p {
            text-align: justify;
        }
    </style>
    '''

st.markdown(mystyle, unsafe_allow_html=True)
st.markdown(
    """<style>.reportview-container {margin-top: -2em;} #MainMenu {visibility: hidden;} .stDeployButton {display:none;} footer {visibility: hidden;}  </style>""",
    unsafe_allow_html=True
)
st.set_option('deprecation.showPyplotGlobalUse', False)

# Função para traduzir o texto do parâmetro
def translate_param_info(param_info, lang):
    return {
        'o_que_e': param_info['o_que_e'][lang],
        'importancia': param_info['importancia'][lang]
    }

# Função para extrair coordenadas
def extrair_coordenadas(gps_string):
    try:
        lat, lon = map(float, gps_string.split(','))
        return lat, lon
    except:
        st.warning(t("Error extracting coordinates from: {gps}").format(gps=gps_string))
        return None, None

# Função para exibir o mapa
def exibir_mapa(dados_filtrados):
    if dados_filtrados.empty:
        st.error(t("No data to display on the map"))
        return

    # Extrair coordenadas do campo GPS
    dados_filtrados[['LATITUDE', 'LONGITUDE']] = dados_filtrados['GPS'].apply(lambda x: pd.Series(extrair_coordenadas(x)))
    
    # Remover linhas com coordenadas inválidas
    dados_validos = dados_filtrados.dropna(subset=['LATITUDE', 'LONGITUDE'])

    if dados_validos.empty:
        st.error(t("No valid coordinates to display on the map"))
        return

    # Calcular centro do mapa
    center_lat = dados_validos['LATITUDE'].mean()
    center_lon = dados_validos['LONGITUDE'].mean()

    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=12
    )
    #camada do icone
    # ScatterplotLayer para os pontos no mapa
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        dados_validos,
        get_position=['LONGITUDE', 'LATITUDE'],
        get_icon="https://github.com/google/material-design-icons/blob/master/png/maps/pin_drop/materialicons/18dp/1x/baseline_pin_drop_black_18dp.png",
        #get_color=[255, 30, 30, 160],  # Vermelho
        get_size=4,
        size_scale=10,
        get_color=[0, 119, 182],  # azul
        get_radius=150,  # Tamanho dos pontos
        pickable=True
    )

    # TextLayer para exibir o nome do rio
    text_layer = pdk.Layer(
        "TextLayer",
        dados_validos,
        get_position=['LONGITUDE', 'LATITUDE'],
       # get_text='RIO',  # Assumindo que a coluna com o nome do rio é 'RIO'
        get_color=[0, 0, 0, 200],  # Cor preta para o texto
        get_size=26,
        get_alignment_baseline='"bottom"'
    )

    # Configurando as tooltips
    tooltip = {
        "html": "<b>Rio:</b> {RIO}<br><b>Ponto:</b> {PONTOS}<br><b>Latitude:</b> {LATITUDE}<br><b>Longitude:</b> {LONGITUDE}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }

    # Criando e exibindo o Deck
    deck = pdk.Deck(
        layers=[scatter_layer, text_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/outdoors-v11",
        height=300,
        tooltip=tooltip
    )

    # Exibir o mapa
    st.pydeck_chart(deck)

# Definição das páginas e navegação
if page == t("Monitoring"):
    st.subheader(t('Analysis of physical water parameters'), divider='green')
    
    parameter_ranges = {
        'pH': (6, 9),
        'CONDUTIVIDADE': (115, 300),
        'TURBIDEZ (NTU)': (0, 100),
        'TEMPERATURA': (0, 40),
        'SALINIDADE': (0, 35)
        #'O. D': (5, 10),
        #'SOLIDOS D. T.': (0, 500)
    }

    # Carregamento dos dados
    dados_df, riochamagunga_df = load_data()
    selected_parameter = None
    if dados_df is None or riochamagunga_df is None:
        st.error(t("The data was not loaded correctly. The variables 'dados_df' and 'riochamagunga_df' will not be defined."))
    else:
        # Definir parametros_disponiveis baseado nas colunas de riochamagunga_df
        parametros_disponiveis = [col for col in riochamagunga_df.columns if col in parameter_ranges]
        
    with st.popover(t('Click to filter data'), use_container_width=True):
        cola, colb = st.columns(2)
        with cola:
            selected_cidade = st.selectbox(
            t('Select the City'),
            options=("PORTO SEGURO", "CABRALIA", "EUNAPOLIS"),
            )    

        with colb:
        
            if 'RIO' in riochamagunga_df.columns:
                rios_unicos = riochamagunga_df['RIO'].unique()
                selected_rios = st.selectbox(t('Choose the river to be consulted'), options=rios_unicos)
                filtered_df = riochamagunga_df[riochamagunga_df['RIO'] == selected_rios.upper()]
            else:
                st.error(t("Column 'RIO' not found in the data."))
                st.write(t("Available columns:"), riochamagunga_df.columns.tolist())
                st.stop()
        
        col_parametros, col_pontodecoleta = st.columns(2)
        with col_parametros: 
            
            selected_parameter = st.selectbox(
                t('Select the Parameter to be analyzed'),
                options=parametros_disponiveis
            )

        with col_pontodecoleta:
            if 'RIO' in riochamagunga_df.columns and 'PONTOS' in riochamagunga_df.columns:
                filtered_df = riochamagunga_df[riochamagunga_df['RIO'] == selected_rios.upper()]
                selected_points = st.multiselect(t('Select the Points'), options=filtered_df['PONTOS'].unique().tolist(), default=filtered_df['PONTOS'].unique().tolist())
            else:
                st.error(t("Columns 'RIO' or 'PONTOS' not found in the data."))
                st.stop()
    
        dados_filtrados = pd.DataFrame()
        tipo_selecao_data = st.radio(t('Select the date type:'), [t('Select date'), t('Select date range')])
        
        data_selecionada = None
        data_inicial = None
        data_final = None
        if tipo_selecao_data == t('Select date'):
            data_selecionada = st.date_input(t("Select the date:"))
        elif tipo_selecao_data == t('Select date range'):
            col_data_inicial, col_data_final = st.columns(2)
            with col_data_inicial:
                data_inicial = st.date_input(t("Initial date:"), key='data_inicial')
            with col_data_final:
                data_final = st.date_input(t("Final date:"), key='data_final')  
            
        # Filtrando os dados com base nos pontos selecionados
        dados_filtrados = riochamagunga_df[(riochamagunga_df['PONTOS'].isin(selected_points)) & (riochamagunga_df['RIO'] == selected_rios)]
        
        # Verificar se há dados filtrados
        if dados_filtrados.empty:
            st.error(t("No data available for the selected filters."))
            st.stop()

        # Verificar se a coluna do parâmetro selecionado existe
        if selected_parameter not in dados_filtrados.columns:
            st.error(t("The parameter '{parameter}' is not present in the data.").format(parameter=selected_parameter))
            st.stop()

        # Gerando o gráfico
        y_column = selected_parameter
        title = ''
        yaxis_title = selected_parameter.strip()
    
        fig = px.bar(dados_filtrados, x='PONTOS', y=y_column, title=title)
        fig.update_traces(marker_color='blue', width=0.6)
        fig.update_xaxes(title_text=t('Collection Points'))
        fig.update_yaxes(
            title_text=yaxis_title,
            showgrid=True,
            gridwidth=1,
            gridcolor='Lightgrey',
            tickmode='auto',
            nticks=25
        )
        
    if selected_parameter in parameter_ranges:
        min_value, max_value = parameter_ranges[selected_parameter]
        fig.add_shape(
            type='line',
            line=dict(color='green', width=3, dash='dash'),
            x0=-0.5,
            y0=min_value,
            x1=len(dados_filtrados['PONTOS']) - 0.5, 
            y1=min_value,
            xref='x',
            yref='y'
        )

        fig.add_shape(
            type='line',
            line=dict(color='orange', width=3, dash='dash'),
            x0=-0.5,
            y0=max_value,
            x1=len(dados_filtrados['PONTOS']) - 0.8,
            y1=max_value,
            xref='x',
            yref='y'
        )
    fig.update_layout(dragmode=False, hovermode=False)
        
    with st.container(border=True):
        col1, col2 = st.columns(2)

    with col1:
        col_graph = st.container(border=True)
        col_graph.markdown(
            f"""
            <h3 style='text-align: left; font-size: 15px;'>{t('Values of {parameter} of the selected point(s)').format(parameter=selected_parameter)}</h3>
            """,
            unsafe_allow_html=True
        )

        if selected_parameter in parameter_ranges:
            min_val, max_val = parameter_ranges[selected_parameter]
            col_graph.markdown(
                f"""
                <div style='display: flex; align-items: center;'>
                    <div style='width: 10px; height: 10px; background-color: green; margin-right: 5px;font-size: 8px;'></div>
                    <div style='margin-right: 10px; font-size: 12px;'>{t("Min CONAMA: {value}").format(value=str(min_val))}</div>
                    <div style='width: 10px; height: 10px; background-color: orange; margin-right: 5px;font-size: 8px;'></div>
                    <div  style='font-size: 12px;'>{t("Max CONAMA: {value}").format(value=str(max_val))}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        col_graph.plotly_chart(fig, use_container_width=True)
    with col2:
        col_map = st.container(border=True)
        with st.container(border=True):
            exibir_mapa(dados_filtrados)
        
    st.subheader(t("Learn more about the selected parameter"), divider='green')
    # Selecionando informações sobre o parâmetro de maneira randômica
    param_info = random.choice(dados_parametros[selected_parameter])
    translated_param_info = translate_param_info(param_info, st.session_state.lang)
        
    with st.container(border=True):  
        coltext1, coltext2 = st.columns([4,6])
        with coltext1:
            with st.popover(t("What is {parameter}?").format(parameter=selected_parameter), use_container_width=True):
                    st.write(translated_param_info["o_que_e"])
        with coltext2:      
            with st.popover(t("What is its Importance?"), use_container_width=True):
                    st.write(translated_param_info["importancia"])          

    
    parameter_values = dados_filtrados[y_column].tolist()
    conama_values = parameter_ranges[selected_parameter]
    
    # Preparando o prompt para a API da OpenAI
    prompt = f"""
    {t('Act as an expert with a PhD in water parameter analysis and generate an analysis of the provided data, but you need to respond with language accessible to diverse audiences. Answer in paragraphs.')}
    {t('Perform an analysis, in portuguese, of the data using the information obtained from the water collection of this river, water was collected for analysis at {num_points} different points of the {river} River. The selected parameter is {parameter}, the value found was {values}. According to CONAMA Resolution 357 for rivers classified as Class 2, the ideal values for this parameter are between {min_val} and {max_val}.').format(num_points=len(selected_points), river=selected_rios, parameter=selected_parameter, values=parameter_values, min_val=conama_values[0], max_val=conama_values[1])}
    """

    # Função para criar PDF
    def criar_pdf(analise_texto, fig):
        pdf_buffer = BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter

        # Carregar e inserir logo
        logo_path = 'logotikatu.png'
        logo_img = ImageReader(logo_path)
        c.drawImage(logo_img, 72, height - 100, width=100, preserveAspectRatio=True, mask='auto')

        # Adicionar título
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(width / 2.0, height - 120, t("Water Quality Analysis Report"))

        # Converter matplotlib figure para uma imagem PNG e inserir no PDF
        fig_buffer = BytesIO()
        fig.savefig(fig_buffer, format='png')
        fig_buffer.seek(0)
        graph_img = ImageReader(fig_buffer)
        c.drawImage(graph_img, 72, height - 390, width=450, height=250)
        fig_buffer.close()

        # Adicionar texto da análise
        c.setFont("Helvetica", 12)
        text_object = c.beginText(72, height - 420)
        wrapped_text = textwrap.fill(analise_texto, 85)
        text_object.textLines(wrapped_text)
        c.drawText(text_object)

        c.showPage()
        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer

    # Gerando o gráfico para o PDF
    fig, ax = plt.subplots(figsize=(14, 10))
    ax.bar(dados_filtrados['PONTOS'], parameter_values, color='blue')
    ax.axhline(y=conama_values[0], color='green', linestyle='--', label=t('Min CONAMA: {value:.2f}').format(value=conama_values[0]))
    ax.axhline(y=conama_values[1], color='orange', linestyle='--', label=t('Max CONAMA: {value:.2f}').format(value=conama_values[1]))
    ax.grid(True)
    ax.legend(fontsize=16, loc='upper left', bbox_to_anchor=(1, 1))
    titulo = t("Analysis of {parameter} of the river {river}").format(parameter=selected_parameter, river=selected_rios)
    ax.set_title(titulo, fontsize=14)
    ax.set_xlabel(t('Collection Points'), fontsize=14)
    ax.set_ylabel(selected_parameter, fontsize=14)
    plt.tight_layout()

    # Gerando a análise com a API da OpenAI
    if st.button(t("Generate Analysis")): 
        with st.spinner(t('Generating analysis...')):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                analise_texto = response.choices[0].message.content
            except Exception as e:
                st.error(t("Error generating analysis: {error}").format(error=str(e)))
                analise_texto = t("It was not possible to generate the analysis due to an error.")

        st.subheader(t("Analysis Generated"), divider='green')
        st.write(analise_texto)

        # Criando e oferecendo o download do PDF
        pdf_output = criar_pdf(analise_texto, fig)
        st.download_button(
            label=t("Download PDF Report"),
            data=pdf_output,
            file_name="relatorio_analise_agua.pdf",
            mime="application/pdf"
        )

elif page == t("Registration"):
    cadastro_e_simulacao()

elif page == t("Make Your Analysis"):
    pagina_analise_agua()

else:  # Home page
    st.subheader(t('Why monitor water?'), divider='green')
    col1, col2 = st.columns(2, gap="small")

    with col1:
        st.image('imagemagua.png')

    with col2:
        st.info(t('Monitoring water quality is crucial for the sustainability of the planet and for the health of all living beings, as water is a finite resource essential for all human activities and ecosystem maintenance.'))

        st.info(t('Continuous monitoring allows for rapid detection and/or prevention of contamination, ensuring that water remains safe for consumption and capable of sustaining life, as well as helping to understand the impacts of human activities on water resources and develop sustainable management strategies.'))
    
    st.subheader(t('Agenda 2030'), divider='blue')
    colimg, coltext = st.columns(2)
      
    with colimg:
        st.image('agenda2030.png')
      
    with coltext:
        st.success(t('This project is intrinsically aligned with the UN\'s Sustainable Development Goals (SDGs) for the 2030 Agenda, especially SDG 6 - Clean Water and Sanitation, and SDG 14 - Life Below Water. Our commitment to monitoring and analyzing water quality seeks to ensure the availability and sustainable management of water and sanitation for all (SDG 6), promoting actions that guarantee the conservation and sustainable use of oceans, seas, and marine resources for sustainable development (SDG 14).'))
    
    st.subheader(t('Monitored parameters'), divider='blue')
    coltextp, colparam = st.columns(2)
         
    with coltextp:
        st.warning(t('Conductivity: Reflects the water\'s ability to conduct electrical current, directly related to the amount of dissolved salts, providing a quick estimate of water quality.'))
        st.warning(t('pH: Measures the acidity or alkalinity of water, crucial for maintaining the chemical balance and health of aquatic ecosystems.'))
    
    with colparam:
        st.image('parametro.png')
    
    st.subheader(t('Preserving water is preserving life'), divider='green')
    
    colimggota, colgota = st.columns(2)
    with colimggota:
        st.image('cadagota.png')
          
    with colgota:
        st.info(t('"Keep the river healthy, every drop counts" is not just a phrase, it\'s a call to action! Our TIKATU project believes that preserving water quality is a collective responsibility, where each individual effort contributes to a significant impact. We understand that rivers are the heart of our ecosystems, vital for biodiversity and human life.'))
