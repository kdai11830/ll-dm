# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 22:51:15 2024

@author: hw112
"""

import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
# import yaml
import json
from openai import OpenAI
import sqlite3
import pandas as pd
import time
import sqlglot
from flask import Flask, render_template, request, redirect, url_for

from lldm import LLDM_Assistant

app = Flask(__name__)

view_count_file = 'view_count.txt'
excel_db_filename = 'DnD.xlsx'
db_name = "lldm.db"
    # with open('api_keys.yaml', 'r') as f:
    #     api_keys = yaml.safe_load(f)

OPENAI_API_KEY = 'your api key'
    
lldm_assistant = LLDM_Assistant(OPENAI_API_KEY, db_name, excel_db_filename=excel_db_filename)

def increment_view_count():
    with open(view_count_file, 'r') as file:
        count = int(file.read().strip())
    count += 1
    with open(view_count_file, 'w') as file:
        file.write(str(count))
    return count

def get_current_view_count():
    with open(view_count_file, 'r') as file:
        count = int(file.read().strip())
    return count

@app.route('/', methods=['GET', 'POST'])
def index():
    
    view_count = increment_view_count()
    
    tmp = []  # Store chat history in a list
    tmp_reversed = []
    flask_text = []

    if request.method == 'POST':
        user_input = request.form['user_input']

        tmp = lldm_assistant.narrator_chat(user_input)
        tmp_reversed = tmp[::-1]
    
        df = lldm_assistant.get_inventory_snapshot()
        flask_text = df.to_dict(orient='records')
   
    return render_template('index0802_final.html', chat_history=tmp_reversed, flask_text = flask_text) 

@app.route('/weapons')
def weapons():

    return render_template('weapons.html')

@app.route('/refresh_and_clear')
def refresh_and_clear():
    # Logic to create a new lldm_assistant
    current_count = get_current_view_count()
    
    db_name = f"{current_count}.db"
    global lldm_assistant
    lldm_assistant = LLDM_Assistant(OPENAI_API_KEY, db_name, excel_db_filename=excel_db_filename)

    # Logic to clear the content in tmp
    # global tmp
    # tmp = None  # Resetting tmp

    return redirect(url_for('index'))

# if __name__ == '__main__':
#     app.run(debug=False)

if __name__ == '__main__':
    # Initialize view count file if it doesn't exist
    try:
        with open(view_count_file, 'x') as file:
            file.write('0')
    except FileExistsError:
        pass
    
    app.run(debug=False)