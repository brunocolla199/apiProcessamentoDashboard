# -*- coding: utf-8 -*-
#Flask
from flask import Flask, Response, request, abort, render_template
from flask_cors import CORS 

#Outros
import json, requests, math

#Logs
import logging
logging.basicConfig(filename='./logs_dashboards.log',  format='%(asctime)s %(levelname)s --- %(message)s')

#Servir aplicação
from waitress import serve

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
        
        variaveis_recebidas   = request.form.to_dict(flat=False)
        
        token_target            = variaveis_recebidas['token'][0] #Token para receber dados do GED
        url_target              = "{}/registro/pesquisa".format(variaveis_recebidas['url'][0]) #Endpoint da API do GED para extrair os dados

        json_recebido           = json.loads(variaveis_recebidas['body'][0]) #Carregar o JSON que é passado como parâmetro do Weehealth
        area_target             = json_recebido['listaIdArea'] #Id da área que contém os dados
        indice_target           = json_recebido['indiceArea']  #Coluna no GED que o usuário quer ver no dashboard
        descricao_indice_target = json_recebido['descricaoIndiceArea'] # Descrição do indice target
        datas_target            = json_recebido['datas']       #Período que o usuário quer
        tipo_grafico            = json_recebido['tipoGrafico'] #Tipo do gráfico que o usuário quer
        indices_filtro_target   = json_recebido['indiceValor'] #Esses índices podem vir com valor ou apenas uma lista vazia     
        titulo_grafico          = json_recebido['tituloGrafico'].split('-')[0] # Título que vai no dashboard

    except:
        
        app.logger.error('As informacoes nao foram enviadas corretamente. Tente novamente!')
        abort(400)   


    #Preparar os HEADERS
    headers = {"Cookie" : "CXSSID={}".format(token_target),
               "content-type" : "application/json"
             }

    #Extração dos dados do GED e preparação dos mesmos
    dataframe_dados_ged = preparacao_extracao_dados(url_target, area_target, headers, indice_target, datas_target, indices_filtro_target, descricao_indice_target)


    #Chamar o método para criar o gráfico
    grafico = criando_dashboard(dataframe_dados_ged, tipo_grafico, titulo_grafico, descricao_indice_target)
    
    try: 

        grafico_json = json.dumps(grafico, cls=plotly.utils.PlotlyJSONEncoder)
        return grafico_json
        #return render_template('index.html', graphJSON=grafico_json)

    except:

       app.logger.error('Ocorreu um erro ao renderizar o grafico. Verifique o tipo do grafico que foi passado e tente novamente')
       return abort(400)

#Receber a URL, body, headers, indice recebido do weehealth e as datas recebidas do weehealth
def preparacao_extracao_dados(url, area_target, headers, indice_target, datas_target, indices_filtro_target, descricao_indice_target):

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

            dataframe = pd.concat([dataframe, pd.DataFrame([chave_valor])], ignore_index=True)
    
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

            app.logger.error('Nao existe a coluna passada como parametro no GED.')
            return abort(400)


        if dataframe.empty:

            app.logger.info('Nao ha registros com o filtros selecionados!')
            abort(404)

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

 
    dataframe['Período'] = lista_nome_datas
    dataframe.rename(columns={indice_target : descricao_indice_target}, inplace=True)

    return dataframe

#Passar dados para construir dashboard
def criando_dashboard(dados_dashboard, tipo_grafico, titulo_grafico, descricao_indice_target):

    #Agrupar os dados para gerar a contagem de registros
    dados_agrupados_data_indice = dados_dashboard.groupby(['Período', descricao_indice_target]).count().reset_index().rename(columns={'Data_do_registro' : 'Contagem'})

    ##Verificar qual tipo de gráfico a aplicação da weehealth quer

    #Gráfico de linhas
    if tipo_grafico == '1':
        
        #Fazer em ordem do mês
        fig = px.line(dados_agrupados_data_indice, x="Período", y="Contagem", color=descricao_indice_target, markers=True, title=titulo_grafico)
        return fig

    #Gráfico de barras agrupado por nome da data
    elif tipo_grafico == '2':

        #Fazer em ordem do mês
        fig = px.bar(dados_agrupados_data_indice, x=descricao_indice_target, y='Contagem', barmode="group", 
                    facet_col='Período', title=titulo_grafico)

        return fig

    #Gráfico de pizza
    elif tipo_grafico == '3':

        fig = px.pie(dados_agrupados_data_indice, values='Contagem', names=descricao_indice_target, title=titulo_grafico)
        return fig

    #Totalizador (A ideia é agrupar só pelo descricao_indice_target e ignorar a data)
    elif tipo_grafico == '4':
        
        #Contagem da quantidade total de cada registro
        dados_agrupados_indice = dados_dashboard[descricao_indice_target].value_counts().reset_index(name='Contagem').rename(columns={'index' : descricao_indice_target})
        
        fig = px.bar(dados_agrupados_indice, x=descricao_indice_target, y='Contagem', title=titulo_grafico)
        return fig
    
    else:
        
        return None

if __name__ == "__main__":
    #Para jogar a aplicação em produção usar serve
    serve(app, host='0.0.0.0', port=5001)    
    #app.run(host='0.0.0.0', port=5001)