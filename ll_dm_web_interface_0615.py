# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 22:51:15 2024

@author: hw112
"""

from flask import Flask, render_template, request

# from pathlib import Path

from openai import OpenAI


app = Flask(__name__)

API_KEY = 'your API key'
client = OpenAI(api_key=API_KEY)

assistant = client.beta.assistants.create(
    name="DnD_DM",
    instructions=
    """
    You are a DnD DM.
    
    The plot summary is as follows:
    
        The Dragon's Flagon (Tavern)
    Description: The Dragon's Flagon is a lively tavern with a warm, welcoming atmosphere. The walls are adorned with trophies from past adventurers, and a large fireplace dominates one side of the room.
    Events: Elara listens to stories and rumors from the locals. An old traveler tells her about an enchanted sword hidden in the Whispering Woods, said to be the key to defeating a monster terrorizing the region. Inspired, Elara gathers her gear and sets off on her quest.
        Whispering Woods (Wilderness)
    Description: Whispering Woods is a foreboding forest with a canopy so thick it blocks out most of the sunlight. The air is filled with the sounds of unseen creatures, and the ground is covered with a thick layer of leaves.
    Events: Elara encounters several obstacles, including treacherous terrain, hostile wildlife, and ancient traps. With her determination and combat skills, she overcomes these challenges and discovers the enchanted sword, which is hidden in a small, overgrown shrine deep within the woods.
        Blackstone Keep (Castle)
    Description: Blackstone Keep is a crumbling fortress with tall, dark towers and walls covered in ivy. Inside, it is dark and cold, with the air thick with the smell of decay.
    Events: Elara enters the keep, navigating its eerie halls and chambers, all of which are eerily quiet. She finally reaches the grand hall where she confronts the monster: a fearsome dragon named Shadowflame. Using the enchanted sword, she engages in an epic battle with the dragon. After a fierce and climactic combat, Elara successfully slays the dragon, lifting the curse over the region and bringing peace to the land. 
        
    After receiving user response, you generate a narrative that moves the plot forward while maintaining a realistic continuity of events.""",
    
    model="gpt-4-turbo",
    # tools=[{"type": "retrieval"}], #"file_search"
    )


    
    
thread = client.beta.threads.create()


@app.route('/', methods=['GET', 'POST'])
def index():
    
    chat_history = []  # Store chat history in a list
    chat_history_reversed = []

    if request.method == 'POST':
        user_input = request.form['user_input']

        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input,
        )

        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread.id,
            assistant_id=assistant.id,
        )

        if run.status == 'completed':
            messages = client.beta.threads.messages.list(
                thread_id=thread.id
            )
            for thread_message in messages.data:
                role = thread_message.role
                for content_item in thread_message.content:
                    item = content_item.text.value
                    chat_history.append({'role': role, 'content': item})
            chat_history_reversed = chat_history[::-1]
    
   
    return render_template('index0615_v1.html', chat_history=chat_history_reversed)  # Pass only the first element of chat_history

if __name__ == '__main__':
    app.run(debug=False)
