# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 22:51:15 2024

@author: hw112
"""

# import os
# import yaml
import json
from openai import OpenAI
import sqlite3
import pandas as pd
import time
import sqlglot
from flask import Flask, render_template, request

from lldm import LLDM_Assistant

app = Flask(__name__)


excel_db_filename = 'DnD.xlsx'
db_name = "lldm.db"
    # with open('api_keys.yaml', 'r') as f:
    #     api_keys = yaml.safe_load(f)

OPENAI_API_KEY = 'your api key'
    
lldm_assistant = LLDM_Assistant(OPENAI_API_KEY, db_name, excel_db_filename=excel_db_filename)

# print('\n\nInitial query:',tmp[1]['content'].strip())
# print('\n\nResponse:',tmp[0]['content'])

@app.route('/', methods=['GET', 'POST'])
def index():
            
    tmp = []  # Store chat history in a list
    tmp_reversed = []
    flask_text = []

    if request.method == 'POST':
        user_input = request.form['user_input']

        tmp = lldm_assistant.narrator_chat(user_input)
        tmp_reversed = tmp[::-1]
    
        df = lldm_assistant.get_inventory_snapshot()
        flask_text = df.to_dict(orient='records')
   
    return render_template('index0720.html', chat_history=tmp_reversed, flask_text = flask_text) 

@app.route('/weapons')
def weapons():

    return render_template('weapons.html')

if __name__ == '__main__':
    app.run(debug=False)
