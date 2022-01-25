from flask import Flask, request
from flask_cors import CORS 
import json, requests, base64, ast
from io import StringIO
from datetime import date, datetime

#set FLASK_APP = app.py
#set FLASK_ENV = development

app = Flask(__name__)
CORS(app)

@app.route("/", methods=['POST'])
def recebendo_informacoes():
    
    #Recebendo o JSON e byte-data e transformando para dicionario python
    variaveis_recebidas = ast.literal_eval(request.data.decode('UTF-8'))

    #Variaveis para fazer requisicoes para o GED
    token         = variaveis_recebidas['token']
    url           = f"{variaveis_recebidas['url']}/registro/pesquisa"
    areas         = variaveis_recebidas['body']['listaIdArea']
    indice_target = variaveis_recebidas['body']['indiceArea']

    # tipo_grafico = variaveis_recebidas['body']['tipoGrafico']
    # datas = variaveis_recebidas['body']['datas']

    headers = {"Cookie" : f"CXSSID={token}",
               "content-type" : "application/json"
             }

    body_ged = {
        "listaIdArea": areas,
        "listaIndice": [
            f"{indice_target}"
        ],
        "inicio": 0,
        "fim": 1000
    }

    extraindo_informacoes_ged(url, body_ged, headers)

    return request.data




def extraindo_informacoes_ged(url, body, headers):

    body_ged = json.dumps(body, ensure_ascii=False)
    response_ged = requests.post(url, headers=headers, data=body_ged)
    print(response_ged.content)

if __name__ == "__main__":
    app.run()