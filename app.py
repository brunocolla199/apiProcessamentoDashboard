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
    token_target         = variaveis_recebidas['token']
    url_target           = f"{variaveis_recebidas['url']}/registro/pesquisa"
    area_target         = variaveis_recebidas['body']['listaIdArea']
    indice_target = variaveis_recebidas['body']['indiceArea']
    datas_target = variaveis_recebidas['body']['datas']
    # tipo_grafico = variaveis_recebidas['body']['tipoGrafico']
    

    headers = {"Cookie" : f"CXSSID={token_target}",
               "content-type" : "application/json"
             }

    body_ged = {
        "listaIdArea": area_target,
        "listaIndice": [],
        "inicio": 0,
        "fim": 1000
    }

    dados_ged = extraindo_informacoes_ged(url_target, body_ged, headers, indice_target, datas_target)

    return dados_ged


    #criando_dashboard

    # data_canada = px.data.gapminder().query("country == 'Canada'")
    # fig = px.bar(data_canada, x='year', y='pop')

    # return render_template('index.html', iframe=fig.show())


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



    print(dataframe)
    print(datas_target_dataframe)

    return response_ged.content

def criando_dashboard():
    pass
    #return render_template('index.html', iframe=fig.show())


if __name__ == "__main__":
    app.run()