# -*- coding: utf-8 -*-
#Flask
from flask import Flask, request, render_template, abort
from flask_cors import CORS 

#Outros
import json, requests, math

#Pegar diretório atual
from pathlib import Path


#Servir aplicação
from waitress import serve

#Logs
import logging
logging.basicConfig(filename='{}/logs_dashboards.log'.format(Path().absolute()), format='%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S')

#Warnings
import warnings
warnings.filterwarnings("ignore")

#Manipulação de dados
import pandas as pd 

#Dashboard
import plotly.express as px

app = Flask(__name__)
CORS(app)

@app.route("/", methods=['POST'])

#Nesta função eu apenas recebo informacoes do WeeHealth e preparo para fazer a requisicao dos dados la no GED
def main():
    
    #Recebendo o JSON POST
    variaveis_recebidas = request.form.to_dict(flat=False)

    #Variaveis para fazer requisicoes para o GED
    try: 

        token_target  = variaveis_recebidas['token'][0]
        url_target    = "{}/registro/pesquisa".format(variaveis_recebidas['url'][0])

        json_recebido = json.loads(variaveis_recebidas['body'][0])

        area_target   = json_recebido['listaIdArea']
        indice_target = json_recebido['indiceArea']
        datas_target  = json_recebido['datas']
        tipo_grafico  = json_recebido['tipoGrafico']

    except:
        logging.error('As informações não foram enviadas corretamente. Tente novamente! BAD REQUEST - 400')
        abort(400)
    
    headers = {"Cookie" : "CXSSID={}".format(token_target),
               "content-type" : "application/json"
             }


    #Extração dos dados do GED
    dataframe_dados_ged = extraindo_informacoes_ged(url_target, area_target, headers, indice_target, datas_target)

    #Chamo o método pra criar o gráfico
    grafico = criando_dashboard(dataframe_dados_ged, indice_target, tipo_grafico)
    
    #Caso o script não consiga renderizar o gráfico, retorno um erro
    try: 
        #Provavelmente ao lugar de index.html, será o caminho do html da aplicação
        return render_template('index.html', iframe=grafico.show())
    except:
        logging.error('Ocorreu um erro ao renderizar o grafico. Verifique o tipo do grafico que foi passado e tente novamente! BAD REQUEST - 400')
        return abort(400)

#Recebo a URL, body, headers, indice recebido do weehealth e as datas recebidas do weehealth
def extraindo_informacoes_ged(url, area_target, headers, indice_target, datas_target):

    #Aplicando paginação

    inicio = 0
    fim = 5000 #Escolhi esse número porque o Zyad disse que é o limite do GED
    

    dataframe = pd.DataFrame()

    #Início dos loops para adicionar dados ao dataframe
    while True: 

        body = {
        "listaIdArea": area_target,
        "listaIndice": [],
        "inicio": inicio,
        "fim": fim 
        }

        #Enviar requisição para o GED
        body_ged = json.dumps(body, ensure_ascii=False)
        response_ged = requests.post(url, headers=headers, data=body_ged)
        retorno_ged = json.loads(response_ged.content.decode('utf-8'))

        #Preparo o dataframe com os registros do Indice e as datas dos registros
        for registro in retorno_ged['listaRegistro']:

            chave_valor = {}
            
            for indice in registro['listaIndice']:
                
                
                #Buscando a data do registro no GED
                chave_valor[indice['identificador']] = indice['valor']
  
            
            #Pode ser que a coluna não exista na área especificada no GED
            try: 

                dataframe = dataframe.append({
                    indice_target : chave_valor[indice_target],
                    'data_registro' : pd.to_datetime(chave_valor['Data_do_registro'])
                }, ignore_index=True)

            except:

                logging.error('Nao existe a coluna {} nessa area do GED. Tente novamente!'.format(indice_target))
                return abort(400)

        #Busco a quantidade de loops dividindo a quantidade de fim pelo resultado da pesquisa e arrendondo pra cima.
        quantidade_loops = (retorno_ged['totalResultadoPesquisa'] / fim)
        quantidade_loops = math.ceil(quantidade_loops)

        #Se for maior que 1, fazer mais loops, senão já quebro o script e jogo pro dataframe
        if quantidade_loops > 1:

            inicio = fim
            fim = fim + 5000
            continue 
        
        else:

            break 
        
    datas_target_dataframe                = pd.DataFrame(datas_target)
    datas_target_dataframe['dataInicial'] = pd.to_datetime(datas_target_dataframe['dataInicial'])
    datas_target_dataframe['dataFinal']   = pd.to_datetime(datas_target_dataframe['dataFinal'])

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

    #Agrupando os dados para gerar a contagem de registros
    dados_agrupados_data_indice = dados_dashboard.groupby(['nome_data', indice_target]).count().reset_index().rename(columns={'data_registro' : 'contagem'})

    ##Verificando qual tipo de gráfico a aplicação da weehealth quer

    #Gráfico de linhas
    if tipo_grafico == '1':
        
        fig = px.line(dados_agrupados_data_indice, x="nome_data", y="contagem", color=indice_target, markers=True, title='Dados referentes a {}'.format(indice_target))
        return fig

    #Gráfico de barras
    elif tipo_grafico == '2':

        fig = px.bar(dados_agrupados_data_indice, x=indice_target, y='contagem', barmode="group", facet_col='nome_data', title='Dados referentes a {}'.format(indice_target))
        return fig

    #Gráfico de pizza
    elif tipo_grafico == '3':

        fig = px.pie(dados_agrupados_data_indice, values='contagem', names=indice_target, title='Dados referentes a {}'.format(indice_target))
        return fig

    #Totalizador (A ideia é agrupar só pelo indice_target e ignorar a data)
    elif tipo_grafico == '4':
        
        #Conto a quantidade total de cada registro
        dados_agrupados_indice = dados_dashboard[indice_target].value_counts().reset_index(name='contagem').rename(columns={'index' : indice_target})
        
        fig = px.bar(dados_agrupados_indice, x=indice_target, y='contagem', title='Totalizador dos dados referentes a {}'.format(indice_target))
        return fig
    
    else:
        
        return None

if __name__ == "__main__":
    #Para jogar a aplicação em produção usar serve
    serve(app, host='0.0.0.0', port=5001)    
    #app.run(host='0.0.0.0', port=5001)