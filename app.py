from textwrap import indent
from unicodedata import name
from unittest import TestResult
from flask import Flask, request, render_template
from flask_cors import CORS 
import json, requests, base64, ast
from datetime import datetime
import pandas as pd 

#Dashboard
import plotly.express as px


#set FLASK_APP = app.py
#set FLASK_ENV = development

app = Flask(__name__)
CORS(app)

@app.route("/", methods=['POST'])
#Nesta funcao eu apenas recebo informacoes do WeeHealth e preparo para fazer a requisicao dos dados la no GED
def recebendo_informacoes():
    
    #Recebendo o JSON e byte-data e transformando para dicionario python
    variaveis_recebidas = ast.literal_eval(request.data.decode('UTF-8'))

    #Variaveis para fazer requisicoes para o GED
    token_target  = variaveis_recebidas['token']
    url_target    = f"{variaveis_recebidas['url']}/registro/pesquisa"
    area_target   = variaveis_recebidas['body']['listaIdArea']
    indice_target = variaveis_recebidas['body']['indiceArea']
    datas_target  = variaveis_recebidas['body']['datas']
    tipo_grafico  = variaveis_recebidas['body']['tipoGrafico']
    

    headers = {"Cookie" : f"CXSSID={token_target}",
               "content-type" : "application/json"
             }

    body_ged = {
        "listaIdArea": area_target,
        "listaIndice": [],
        "inicio": 0,
        "fim": 1000
    }

    dataframe_dados_ged = extraindo_informacoes_ged(url_target, body_ged, headers, indice_target, datas_target)

    dashboard = criando_dashboard(dataframe_dados_ged, indice_target, tipo_grafico)

    return render_template('index.html', iframe=dashboard.show())

#Recebo a URL, body, headers, indice recebido do weehealth e as datas recebidas do weehealth
def extraindo_informacoes_ged(url, body, headers, indice_target, datas_target):

    body_ged = json.dumps(body, ensure_ascii=False)
    response_ged = requests.post(url, headers=headers, data=body_ged)

    retorno_ged = json.loads(response_ged.content.decode('utf-8'))
    
    dataframe = pd.DataFrame()
    
    #Preparo o dataframe com os registros do Indice e as datas dos registros
    for registro in retorno_ged['listaRegistro']:

        chave_valor = {}
        
        for indice in registro['listaIndice']:
            
            #Buscando a data do registro no GED
            chave_valor[indice['identificador']] = indice['valor']

        dataframe = dataframe.append({
            indice_target : chave_valor[indice_target],
            'data_registro' : pd.to_datetime(chave_valor['Data_do_registro'])
        }, ignore_index=True)

    datas_target_dataframe = pd.DataFrame(datas_target)
    datas_target_dataframe['dataInicial'] = pd.to_datetime(datas_target_dataframe['dataInicial'])
    datas_target_dataframe['dataFinal'] = pd.to_datetime(datas_target_dataframe['dataFinal'])

    #Busco o nome da data recebido da aplicação da Weehealth para cada data do registro
    lista_nome_datas = []
    for data_registro in dataframe['data_registro']:
        for datas in datas_target_dataframe.iterrows():
            
            #Filtro pelas datas recebidas do weehealth com as datas do GED
            if (data_registro >= datas[1]['dataInicial']) & (data_registro <= datas[1]['dataFinal']):
                lista_nome_datas.append(datas[1]['nome'])

    
    dataframe['nome_data'] = lista_nome_datas

    return dataframe

#Passar dados para construir dashboard
def criando_dashboard(dados_dashboard, indice_target, tipo_grafico):

    dados_agrupados = dados_dashboard.groupby(['nome_data', indice_target]).count().reset_index().rename(columns={'data_registro' : 'contagem'})

    #Verificando qual tipo de gráfico a aplicação da weehealth quer

    #Gráfico de linhas
    if tipo_grafico == '1':
        
        fig = px.line(dados_agrupados, x="nome_data", y="contagem", color=indice_target, markers=True)
        return fig

    #Gráfico de barras
    elif tipo_grafico == '2':

        fig = px.bar(dados_agrupados, x=indice_target, y='contagem', barmode="group", facet_col='nome_data', title=f'Dados referentes a {indice_target}')
        return fig

    #Gráfico de pizza
    elif tipo_grafico == '3':

        fig = px.pie(dados_agrupados, values='contagem', names=indice_target)
        return fig

if __name__ == "__main__":
    app.run()