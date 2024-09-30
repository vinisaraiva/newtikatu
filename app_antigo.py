import streamlit as st
from streamlit_navigation_bar import st_navbar
from PIL import Image
import pandas as pd
import datetime
import plotly.graph_objects as go
import plotly.express as px
import plotly.figure_factory as ff
import requests
from openai import OpenAI
import json
import random
import os
import datetime
from dic_parametros import dados_parametros
from estilocolunas import estilo_colunas
import base64
import pydeck as pdk
import textwrap
import datetime
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator, MultipleLocator
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from fpdf import FPDF
from io import BytesIO
import plotly.io as pio
pio.kaleido.scope.default_format = "png"

# Configuração inicial da página
st.set_page_config(page_title="Análise da Qualidade da Água", page_icon=":bar_chart:", layout="wide")

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

pages = ["Home", "Monitoramento"]

styles = {
    "nav": {
        "background-color": "#0B8DC8B3",
         "justify-content": "left",
         "padding-left": "0px",
    },
    "img": {
       "padding-right": "10px",
        "padding-left": "0px",
        "margin-left": "0px",
    
      
    },
    "div": {
        "max-width": "40rem",
        "padding-left": "0px",
     
    },
    "span": {
        "color": "rgb(49, 51, 63)",
        "border-radius": "0.5rem",
        "padding": "0.4045rem 0.605rem",
        "margin": "0 0.125rem",
        "padding": "5px"
    },
    "active": {
        "background-color": "rgba(255, 255, 255, 0.25)",
        "padding": "5px",
    },
    "hover": {
        "background-color": "rgba(255, 255, 255, 0.35)",
    },
}

parent_dir = os.path.dirname(os.path.abspath(__file__))
logo_path = os.path.join(parent_dir, "tikatu.svg")
options={"use_padding": False}
page = st_navbar(pages, logo_path=logo_path, styles=styles)
mystyle = '''
    <style>
        p {
            text-align: justify;
        }
    </style>
    '''

st.markdown(mystyle, unsafe_allow_html=True)
st.markdown("""<style>.reportview-container {margin-top: -2em;} #MainMenu {visibility: hidden;} .stDeployButton {display:none;} footer {visibility: hidden;}  </style>""", unsafe_allow_html=True)
st.set_option('deprecation.showPyplotGlobalUse', False)


#estilos


#estilos-fim

if page == "Monitoramento":
    st.subheader('Analise de parâmetros físicos da água', divider='green')
    data = pd.read_csv("riochamagunga.csv", encoding="ISO-8859-1", sep=';')
    
    #apresentacao do popup
    with st.popover('CLIQUE PARA FILTRAR OS DADOS', use_container_width=True):
        selected_rios = st.selectbox('Escolha o rio a ser consultado', options=['RIO DOS MANGUES', 'RIO BURANHÉM', 'RIO CHAMAGUNGA', 'RIO UTINGA'])
        selected_parameter = st.selectbox(
            'Selecione o Parâmetro a ser analisado',
            options=['TURBIDEZ (NTU)', 'CONDUTIVIDADE', 'pH']  # Garanta que estas opções correspondam às chaves do seu dicionário
        )
    #'TEMPERATURA'
        # Criação das colunas para os filtros e informações na página principal
        col_pontodecoleta = st.columns(1)[0]
        
        with col_pontodecoleta:
            # Multi-select checkbox para escolher pontos a serem exibidos
            selected_points = st.multiselect('Selecione os Pontos', options=data['PONTOS'].unique().tolist(), default=data['PONTOS'].unique().tolist())  
    
        parameter_ranges = {
            'pH': (6, 9),
            'CONDUTIVIDADE': (115, 300),
            'TURBIDEZ (NTU)': (0, 100)
        }
        
        # Utiliza um único radio button para a escolha do tipo de data.
        tipo_selecao_data = st.radio('Selecione o tipo de data:', ['Selecione data', 'Selecione intervalo de datas'])
        
        # Inicializa as variáveis para armazenar as datas.
        data_selecionada = None
        data_inicial = None
        data_final = None
        # Componente para escolher entre selecionar uma única data ou um intervalo de datas 
        st.write(" ")
        if tipo_selecao_data == 'Selecione data':
             data_selecionada = st.date_input("Selecione a data:")
        # Se a escolha for para selecionar um intervalo de datas, organiza os date_inputs lado a lado.
        elif tipo_selecao_data == 'Selecione intervalo de datas':
             col_data_inicial, col_data_final = st.columns(2)
             with col_data_inicial:
                  data_inicial = st.date_input("Data inicial:", key='data_inicial')
             with col_data_final:
                  data_final = st.date_input("Data final:", key='data_final')  
    
    # Filtrando os dados com base nos pontos selecionados
    filtered_data = data[data['PONTOS'].isin(selected_points)]
    #filtered_data = data[data['PONTOS'].isin(selected_points) & (data['RIO'] == selected_rios)]
    
    
    # Inicialização do estado da aplicação
    if 'init' not in st.session_state:
        st.session_state['init'] = True
        st.session_state['filtered_data'] = filtered_data
    
    # Gerando o gráfico
    y_column = selected_parameter
    title = ''
    yaxis_title = selected_parameter.strip()
    
    # Create the bar chart using Plotly Express
    fig = px.bar(filtered_data, x='PONTOS', y=y_column, title=title)
       
    # Modify bar properties
    fig.update_traces(marker_color='blue', width=0.6)
        
    # Update x-axis and y-axis titles
    fig.update_xaxes(title_text='Pontos de Coleta')
    fig.update_yaxes(
        title_text=yaxis_title,
        showgrid=True,
        gridwidth=1,
        gridcolor='Lightgrey',
        tickmode='auto',
        nticks=25  # Aumentar o número de ticks para mostrar mais linhas intermediárias
    
    )
        
    # Add shapes for the ideal range (minimum and maximum values)
    min_value, max_value = parameter_ranges[selected_parameter]
    fig.add_shape(
        type='line',
        line=dict(color='green', width=2, dash='dash'),
        x0=-0.5,
        y0=min_value,
        x1=len(data['PONTOS']) - 0.5,  # Ajuste conforme a quantidade de pontos
        y1=min_value,
        xref='x',
        yref='y'
    )
        
    fig.add_shape(
        type='line',
        line=dict(color='orange', width=2, dash='dash'),
        x0=-0.5,
        y0=max_value,
        x1=len(data['PONTOS']) - 0.8,  # Ajuste conforme a quantidade de pontos
        y1=max_value,
        xref='x',
        yref='y'
    )
    # Configurações para desativar interatividade
    fig.update_layout(
        dragmode=False,  # Desativa o modo de arrastar para pan/zoom
        hovermode=False,  # Desativa os hovers
    )
    
    #gera mapa
    center_lat = filtered_data['LATITUDE'].mean() if not filtered_data.empty else 0
    center_lon = filtered_data['LONGITUDE'].mean() if not filtered_data.empty else 0
    
    view_state = pdk.ViewState(
        latitude=st.session_state['filtered_data']['LATITUDE'].mean(),
        longitude=st.session_state['filtered_data']['LONGITUDE'].mean(),
        zoom=10
    )
    config = {
    'displayModeBar': False  # Desativa a barra de modo (toolbar)
    }
    
    
    col_map = st.container(border=True)
    # ScatterplotLayer para os pontos no mapa
    scatter_layer = pdk.Layer(
        "ScatterplotLayer",
        filtered_data,
        get_position=['LONGITUDE', 'LATITUDE'],
        get_color=[255, 30, 30, 160],  # Vermelho
        get_radius=350,  # Tamanho dos pontos
        pickable=True
                )
    
    # Configurando as tooltips
    tooltip = {
        "html": "<b>Rio:</b> Chamagunga<br><b>Ponto:</b> {PONTOS}<br><b>Latitude:</b> {LATITUDE}<br><b>Longitude:</b> {LONGITUDE}",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }
    
    
    # TextLayer para exibir o nome do rio
    text_layer = pdk.Layer(
        "TextLayer",
        filtered_data,
        get_position=['LONGITUDE', 'LATITUDE'],
        get_text=str(selected_rios),
        get_color=[0, 0, 0, 200],  # Cor preta para o texto
        get_size=26,
        get_alignment_baseline='"bottom"'
    )
    
    # Criando e exibindo o Deck
    deck = pdk.Deck(
        layers=[scatter_layer, text_layer],
        initial_view_state=view_state,
        map_style="mapbox://styles/mapbox/outdoors-v11",  # Usando estilo 'outdoors' que é bom para rios e natureza
        height=300,
        tooltip=tooltip
    )
    
    tab1, tab2 = st.tabs(["Gráfico", "Veja os pontos no Mapa"])
    
    with tab1:
        # Container para o gráfico e índices CONAMA
        col_graph = st.container(border=True)
        col_graph.markdown(
            f"""
            <h3 style='text-align: left; font-size: 15px;'>Valores de {selected_parameter} do(s) ponto(s) selecionado(s)</h3>
            """,
            unsafe_allow_html=True
            )
            
            # Exibindo valores de mínimo e máximo do CONAMA diretamente abaixo do título do gráfico
        min_val, max_val = parameter_ranges[selected_parameter]
        col_graph.markdown(
                f"""
                <div style='display: flex; align-items: center;'>
                    <div style='width: 10px; height: 10px; background-color: green; margin-right: 5px;font-size: 8px;'></div>
                    <div style='margin-right: 10px; font-size: 12px;'>{"Min CONAMA: " + str(min_val)}</div>
                    <div style='width: 10px; height: 10px; background-color: orange; margin-right: 5px;font-size: 8px;'></div>
                    <div  style='font-size: 12px;'>{"Max CONAMA: " + str(max_val)}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
       
        col_graph.plotly_chart(fig, use_container_width=True, config=config)
        
    with tab2:
        # Renderizando o mapa no Streamlit
        col_map = st.container(border=True)
        col_map.pydeck_chart(deck, use_container_width=True)
    
    st.subheader('Saiba mais do parâmetro selecionado', divider='green')
    # Selecionando informações sobre o parâmetro de maneira randômica
    param_info = random.choice(dados_parametros[selected_parameter])
    
    with st.container(border=True):  
        coltext1, coltext2 = st.columns([2,8])
        with coltext1:
            with st.popover(f"O que é {selected_parameter}?", use_container_width=True):
                 st.write(param_info["o_que_e"])
        with coltext2:      
            with st.popover(f"Qual sua Importância ?", use_container_width=True):
                 st.write(param_info["importancia"])
    
    # Carrega a chave API dos secrets do Streamlit
    parameter_values = filtered_data[y_column].tolist()
    conama_values = parameter_ranges[selected_parameter]
    
    # Preparando o prompt para a API da OpenAI
    prompt = f"""
    Atue como um especialista com Doutorado em análise de parâmetros da água e gere uma análise dos dados informados, porém precisa responder com uma linguagem acessível a públicos diversos. Responda separando por parágrafos.
    Faça uma análise dos dados utilizando as informações obtidas com a coleta da água desse rio, foi coletada água para análise em {len(selected_points)} pontos diferentes do Rio {selected_rios}. O parâmetro selecionado é {selected_parameter}, o valor encontrado foi {parameter_values}. De acordo com a resolução 357 do CONAMA para rio classificado como Classe 2, os valores ideais para esse parâmetro, fica entre {conama_values[0]} e {conama_values[1]}.
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
        c.drawCentredString(width / 2.0, height - 120, "Relatório de Análise de Qualidade da Água")
    
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
        wrapped_text = textwrap.fill(analise_texto, 85)  # Quebra de linha para ajustar ao PDF
        text_object.textLines(wrapped_text)
        c.drawText(text_object)
    
        c.showPage()
        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer
    
    # Gerando o gráfico
    fig, ax = plt.subplots(figsize=(14, 10))  # Ajustando o tamanho aqui
    ax.bar(filtered_data['PONTOS'], parameter_values, color='blue')
    ax.axhline(y=conama_values[0], color='green', linestyle='--', label='Min CONAMA: {:.2f}'.format(conama_values[0]))
    ax.axhline(y=conama_values[1], color='orange', linestyle='--', label='Max CONAMA: {:.2f}'.format(conama_values[1]))
    ax.grid(True)
    ax.legend(fontsize=16, loc='upper left', bbox_to_anchor=(1, 1))
    titulo = f"Análise de {selected_parameter} do rio {selected_rios}"
    ax.set_title(titulo, fontsize=14)  # Ajuste o tamanho da fonte do título conforme necessário
    ax.set_xlabel('Pontos de Coleta', fontsize=14)  # Ajuste o tamanho da fonte conforme necessário
    ax.set_ylabel(selected_parameter, fontsize=14)  # Ajuste o tamanho da fonte conforme necessário
    # Adicionando linhas de grade menores
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.grid(which='major', color='grey', linestyle='-', linewidth=0.5)
    ax.grid(which='minor', color='grey', linestyle=':', linewidth=0.5)
    
    
    # Configurações para uma melhor exibição
    plt.tight_layout()
    plt.show()
    
    if st.button('Gerar Análise', use_container_width=True, type="primary"):
        with st.spinner('Gerando análise...'):
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                analise_texto = response.choices[0].message.content
                st.info(analise_texto)  # Mostra a análise gerada
    
                pdf_output = criar_pdf(analise_texto, fig)
                st.download_button(
                    "Download da Análise",
                    data=pdf_output,
                    file_name="relatoriotikatu.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                pdf_output.close()
            except Exception as e:
                st.error(f"Erro ao gerar análise: {str(e)}")

elif page == "Home":
      st.subheader('Por que monitorar a água ?', divider='green')
      col1, col2 = st.columns(2, gap="small")

      with col1:
          st.image('imagemagua.png')

      with col2:
          st.info(
              """
              Monitorar a qualidade da água é crucial para a sustentabilidade do
              planeta e para a saúde de todos os seres vivos, visto que a água é 
              um recurso finito e essencial para todas as atividades humanas e 
              manutenção dos ecossistemas.
              """
            )

          st.info(
              """
              O monitoramento contínuo permite a detecção rápida e/ou prevenção de 
              contaminações, assegurando que a água se mantenha segura para consumo
              e capaz de sustentar a vida, além de ajudar a entender os impactos das
              atividades humanas sobre os recursos hídricos e desenvolver estratégias
              de gestão sustentável. 
              """
            )
    
      st.subheader('Agenda 2030', divider='blue')
      colimg, coltext = st.columns(2)
      
      with colimg:
          st.image('agenda2030.png')
      
      with coltext:
          st.success(
              """
              Esse projeto está intrinsecamente alinhado com os Objetivos de Desenvolvimento
              Sustentável (ODS) da Agenda 2030 da ONU, especialmente com os ODS 6 - Água Potável
              e Saneamento, e ODS 14 - Vida na Água. Nosso compromisso com a monitoração e análise
              da qualidade da água busca assegurar a disponibilidade e gestão sustentável da água
              e saneamento para todos (ODS 6), promovendo ações que garantam a conservação e uso 
              sustentável dos oceanos, mares e recursos marinhos para o desenvolvimento sustentável
              (ODS 14).
              """
            )
      st.subheader('Parâmetros monitorados', divider='blue')
      coltextp, colparam = st.columns(2)
         
      with coltextp:
          st.warning(
              """
              Condutividade: Reflete a capacidade da água de conduzir corrente elétrica, diretamente relacionada
              à quantidade de sais dissolvidos, fornecendo uma estimativa rápida da qualidade da água.
              """
            )
          st.warning(
              """
              pH: Mede a acidez ou alcalinidade da água, crucial para manter o equilíbrio químico e a saúde dos
              ecossistemas aquáticos.
              """
            )
          st.warning(
              """
              pH: Mede a acidez ou alcalinidade da água, crucial para manter o equilíbrio químico e a saúde dos
              ecossistemas aquáticos.
              """
            )
      with colparam:
          st.image('parametro.png')
    
      st.subheader('Preservar água é preservar a vida', divider='green')
      
      colimggota, colgota = st.columns(2)
      with colimggota:
          st.image('cadagota.png')
          
      with colgota:
          st.info(
              """
              "Mantenha o rio saudável, cada gota conta" não é apenas uma frase, é um chamado à ação!
              Nosso projeto TIKATU acredita que a preservação da qualidade da água é uma responsabilidade
              coletiva, onde cada esforço individual contribui para um impacto significativo. 
              Compreendemos que os rios são o coração dos nossos ecossistemas, vitais para a biodiversidade
              e para a vida humana.  
              """
            )
      
    
