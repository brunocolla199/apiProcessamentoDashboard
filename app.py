from flask import Flask, request
from flask_cors import CORS 
import json, requests, base64
from io import StringIO
from datetime import date, datetime


app = Flask(__name__)
CORS(app)

@app.route("/", methods=['POST'])
def dashboard():
    
    print(request.data)
    return request.data


if __name__ == "__main__":
    app.run()