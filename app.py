# -*- coding: utf-8 -*-
#Flask
from flask import Flask, Response, request, abort, render_template
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
import plotly
import plotly.express as px

app = Flask(__name__)
CORS(app)

@app.route("/grafico", methods=['POST'])
#Receber informacoes do WeeHealth e preparo para fazer a requisicao dos dados la no GED
def main():

    #Receber os dados como formulário do Weehealth
    try: 
        
        variaveis_recebidas = request.form.to_dict(flat=False)
        token_target  = variaveis_recebidas['token'][0]
        url_target    = "{}/registro/pesquisa".format(variaveis_recebidas['url'][0])

        json_recebido = json.loads(variaveis_recebidas['body'][0])
        area_target           = json_recebido['listaIdArea'] #Id da área que contém os dados
        indice_target         = json_recebido['indiceArea']  #Coluna no GED que o usuário quer ver no dashboard
        datas_target          = json_recebido['datas']       #Período que o usuário quer
        tipo_grafico          = json_recebido['tipoGrafico'] #Tipo do gráfico que o usuário quer
        indices_filtro_target = json_recebido['indiceValor'] #Esses índices podem vir com valor ou apenas uma lista vazia     
        
    except:

        logging.error('As informações não foram enviadas corretamente. Tente novamente! BAD REQUEST - 400')
        abort(400)   


    #Preparar os HEADERS
    headers = {"Cookie" : "CXSSID={}".format(token_target),
               "content-type" : "application/json"
             }

    #Extração dos dados do GED
    dataframe_dados_ged = preparacao_extracao_dados(url_target, area_target, headers, indice_target, datas_target, indices_filtro_target)

    #Chamar o método para criar o gráfico
    grafico = criando_dashboard(dataframe_dados_ged, indice_target, tipo_grafico)
    
    try: 

        grafico_json = json.dumps(grafico, cls=plotly.utils.PlotlyJSONEncoder)
        return grafico_json
        #return render_template('index.html', graphJSON=grafico_json)

    except:

       logging.error('Ocorreu um erro ao renderizar o grafico. Verifique o tipo do grafico que foi passado e tente novamente! BAD REQUEST - 400')
       return abort(400)

#Receber a URL, body, headers, indice recebido do weehealth e as datas recebidas do weehealth
def preparacao_extracao_dados(url, area_target, headers, indice_target, datas_target, indices_filtro_target):

    #Aplicar paginação

    inicio = 0
    fim = 5000 #Esse número foi escolhido porque o Zyad disse que é o limite do GED
    
    #Dataframe utilizado para estruturar todos os dados para criar os dashboards
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

        #Preparar o dataframe com os registros do Indice e as datas dos registros
        for registro in retorno_ged['listaRegistro']:

            chave_valor = {}
           
            for indice in registro['listaIndice']:
                
                #Buscar a data do registro no GED
                chave_valor[indice['identificador']] = indice['valor']

            dataframe = dataframe.append(chave_valor, ignore_index=True)

        #Transformações nos dados
        
        #Estruturar os dados para filtragem, recebidos pelo WeeHealth - Datas
        datas_target_dataframe                = pd.DataFrame(datas_target)
        datas_target_dataframe['dataInicial'] = pd.to_datetime(datas_target_dataframe['dataInicial'])
        datas_target_dataframe['dataFinal']   = pd.to_datetime(datas_target_dataframe['dataFinal'])
        data_target_minima = datas_target_dataframe['dataInicial'].min()
        data_target_maxima = datas_target_dataframe['dataFinal'].max()

        #Estruturar os dados para filtragem, recebidos pelo Weehealth - Outras informações
        indices_fitro_target_dataframe = pd.DataFrame(indices_filtro_target)


        dataframe['Data_do_registro'] = pd.to_datetime(dataframe['Data_do_registro'], dayfirst=True)

        #FILTROS NO DATAFRAME

        #Filtrar o período
        dataframe = dataframe[(dataframe['Data_do_registro'] >= data_target_minima) & (dataframe['Data_do_registro'] <= data_target_maxima)]

        #Verificar se o dataframe dos filtros não está vazio. Filtrar pelos indices que o Weehealth passa em indiceValor
        if not indices_fitro_target_dataframe.empty:

            for indice_valor in indices_fitro_target_dataframe[['indice', 'valor']].iterrows():

                indice = indice_valor[1]['indice']
                valor = indice_valor[1]['valor']
                
                dataframe = dataframe[dataframe[indice] == valor]

        #Filtar pelo indice target que o Weehealth envia 
        try:

            dataframe = dataframe[[indice_target, 'Data_do_registro']]

        except:

            logging.error('Não existe a coluna passada como parâmetro no GED. BAD REQUEST - 400')
            return abort(400)


        if dataframe.empty:

            logging.error('Não há registros com o filtros selecionados!')
            return abort(400)

        #Buscar a quantidade de loops dividindo a quantidade de fim pelo resultado da pesquisa e arrendondo pra cima.
        quantidade_loops = (retorno_ged['totalResultadoPesquisa'] / fim)
        quantidade_loops = math.ceil(quantidade_loops)

        #Se for maior que 1, fazer mais loops, senão já quebro o script e jogo pro dataframe
        if quantidade_loops > 1:

            inicio = fim
            fim = fim + 5000
            continue 
        
        else:

            break 
            
    #Buscar o nome da data recebido da aplicação da Weehealth para cada data do registro
    lista_nome_datas = []
    for data_registro in dataframe['Data_do_registro']:
        for datas in datas_target_dataframe.iterrows():

            #Filtro pelas datas recebidas do weehealth com as datas do GED
            if (data_registro >= datas[1]['dataInicial']) & (data_registro <= datas[1]['dataFinal']):
                lista_nome_datas.append(datas[1]['nome'])

 
    dataframe['nome_data'] = lista_nome_datas

    return dataframe

#Passar dados para construir dashboard
def criando_dashboard(dados_dashboard, indice_target, tipo_grafico):

    #Agrupar os dados para gerar a contagem de registros
    dados_agrupados_data_indice = dados_dashboard.groupby(['nome_data', indice_target]).count().reset_index().rename(columns={'Data_do_registro' : 'contagem'})

    ##Verificar qual tipo de gráfico a aplicação da weehealth quer

    #Gráfico de linhas
    if tipo_grafico == '1':
        
        #Fazer em ordem do mês
        fig = px.line(dados_agrupados_data_indice, x="nome_data", y="contagem", color=indice_target, markers=True, title='Dados referentes a {}'.format(indice_target))
        return fig

    #Gráfico de barras agrupado por nome da data
    elif tipo_grafico == '2':

        #Fazer em ordem do mês
        fig = px.bar(dados_agrupados_data_indice, x=indice_target, y='contagem', barmode="group", 
                    facet_col='nome_data', title='Dados referentes a {}'.format(indice_target))
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))

        return fig

    #Gráfico de pizza
    elif tipo_grafico == '3':

        fig = px.pie(dados_agrupados_data_indice, values='contagem', names=indice_target, title='Dados referentes a {}'.format(indice_target))
        return fig

    #Totalizador (A ideia é agrupar só pelo indice_target e ignorar a data)
    elif tipo_grafico == '4':
        
        #Contagem da quantidade total de cada registro
        dados_agrupados_indice = dados_dashboard[indice_target].value_counts().reset_index(name='contagem').rename(columns={'index' : indice_target})
        
        fig = px.bar(dados_agrupados_indice, x=indice_target, y='contagem', title='Totalizador dos dados referentes a {}'.format(indice_target))
        return fig
    
    else:
        
        return None

if __name__ == "__main__":
    #Para jogar a aplicação em produção usar serve
    serve(app, host='0.0.0.0', port=5001)    
    #app.run(host='0.0.0.0', port=5001)