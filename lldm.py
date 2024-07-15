import os
import yaml
import json
from openai import OpenAI
import sqlite3
import pandas as pd
import time
import sqlglot

class LLDM_Assistant:

    class ItemNotFoundException(Exception):
        pass
    class ItemNotPossessedException(Exception):
        pass

    def __init__(self, api_key, db_name, excel_db_filename=None):
        self.client = OpenAI(api_key=api_key)
        if excel_db_filename:
            self.db = self.__create_db_from_file(excel_db_filename, db_name)
        else:
            self.db = self.__connect_to_existing_db(db_name)

        get_info_func_desc = '''
        Generate a SQL query to help extract the information that the user is asking for with regards to the items in their character's inventory, such as taking out or utilizing an item the character possesses. Use the following view to help generate the query, with the description of each column in between asterisks (*):

        CREATE TABLE IF NOT EXISTS CHARACTER_INVENTORY_DETAILS (
            Weapon_Name text, 
            Weapon_Description text ,
            Total_Quantity int    
        );

        CREATE TABLE IF NOT EXISTS CHARACTER_INVENTORY_HISTORY_DETAILS (
            Weapon_Name text, 
            Weapon_Description text,
            Quantity int *A positive number represents obtained weapons, while a negative number means discarded*,
            Modify_Time datetime
        );

        Make sure to only query columns that exist from each table. Do not switch column-table identities.
        Only return the SQL query without any preamble or post text, as well as without any quotes. Do not add a semicolon at the end of the query
        Only create SELECT queries and do not create any queries that will modify the table in any way.
        '''
        
        self.narrator = self.client.beta.assistants.create(
            name="narrator",
            instructions=
                """
                You are a DnD DM. You sets the scene by describing the environment and atmosphere, brings NPCs to life through detailed character portrayals, and narrates the outcomes of player actions. They establish the game's tone, provide world-building lore, guide the overarching story while balancing player choices, and enforce game rules.

                The information of the main character is as follows: Elara Windrider, a courageous warrior with a heart of gold, is a human fighter who embodies the principles of Lawful Good. She is tall and athletic, with short brown hair, green eyes, and a determined expression. Clad in chain mail and wielding a longsword, Elara's appearance reflects her readiness for battle. Born in a small village, she was trained by her father, a retired soldier. Driven by a desire to protect the innocent and seek justice, she left home to make her mark on the world. Elara is brave and compassionate, possessing a strong sense of justice. Though she is determined and reliable, her stubbornness can sometimes get the best of her.

                The plot summary is as follows:

                    The Dragon's Flagon (Tavern)
                Description: The Dragon's Flagon is a lively tavern with a warm, welcoming atmosphere. The walls are adorned with trophies from past adventurers, and a large fireplace dominates one side of the room.
                
                    Whispering Woods (Wilderness)
                Description: Whispering Woods is a foreboding forest with a canopy so thick it blocks out most of the sunlight. The air is filled with the sounds of unseen creatures, and the ground is covered with a thick layer of leaves.
                
                Description: Blackstone Keep is a crumbling fortress with tall, dark towers and walls covered in ivy. Inside, it is dark and cold, with the air thick with the smell of decay.

                After receiving user response, you generate a narrative that moves the plot forward while maintaining a realistic continuity of events.
                """,

            tools=[
                # {"type": "file_search"},
                {
                    "type": "function",
                    "function": {
                        "name": "get_obtained_item",
                        "description": "Extract the item that the user has obtained in some manner (such as picked up, purchased, etc.)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "item_name": {
                                    "type": "string",
                                    "description": "The name of the obtained item.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "The number of said items obtained. If a number is not specified, try and infer based on the surrounding context."
                                }
                            },
                            "required": ["item_name", "quantity"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_discarded_item",
                        "description": "Extract the item that the user has discarded in some manner (such as thrown away, consumed, broken, etc.)",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "item_name": {
                                    "type": "string",
                                    "description": "The name of the discarded item.",
                                },
                                "quantity": {
                                    "type": "integer",
                                    "description": "The number of said items discarded. If a number is not specified, try and infer based on the surrounding context."
                                }
                            },
                            "required": ["item_name", "quantity"],
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_item_info",
                        "description": get_info_func_desc,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "sql_query": {
                                    "type": "string",
                                    "description": "The generated SQL query that would extract the information related to the character inventory requested by the user",
                                }
                            },
                            "required": ["sql_query"],
                        },
                    },
                }
            ],
            model="gpt-3.5-turbo",
        )

        self.thread_narrator = self.client.beta.threads.create()

    def narrator_chat(self, content):
        message = self.client.beta.threads.messages.create(
            thread_id=self.thread_narrator.id,
            role="assistant",
            content=f"""
            {content}
            """,
        )

        run = self.client.beta.threads.runs.create_and_poll(
            thread_id=self.thread_narrator.id,
            assistant_id=self.narrator.id,
        )

        counter = 0
        while run.status != 'completed':
            # print(run.status)
            if run.status == 'requires_action':
                print('Function calling...')
                required_actions = run.required_action.submit_tool_outputs.model_dump()
                tool_outputs = []
                # print(required_actions["tool_calls"])
                for action in required_actions["tool_calls"]:
                    func_name = action['function']['name']
                    arguments = json.loads(action['function']['arguments'])
                    available_functions = {
                        "get_obtained_item": self.__get_obtained_item,
                        "get_discarded_item": self.__get_discarded_item,
                        'get_item_info': self.__get_item_info
                    }
                    try:
                        function_to_call = available_functions[func_name]
                        # print(arguments)
                        # function_args = json.loads(arguments)
                        # output = function_to_call(
                        #     item_name=function_args.get("item_name"),
                        #     quantity=function_args.get("quantity"),
                        # )
                        output = function_to_call(
                            **arguments
                        )
                        output_string = json.dumps(output)
                        # print(output_string)
                        tool_outputs.append({
                            "tool_call_id": action['id'],
                            "output": output_string
                        })
                    except: # function not found
                        raise ValueError(f"Unknown function: {func_name}")
                    
                print("Submitting outputs back to the Assistant…")
                # print(run.status)
                run = self.client.beta.threads.runs.submit_tool_outputs(
                    thread_id=self.thread_narrator.id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                # time.sleep(5) 
            if run.status == "cancelled":
                print("Run cancelled.")
                break
            if run.status == "cancelling":
                print("Run cancelling.")
            if run.status == "failed":
                print("Run failed.")
                break
            if run.status == "expired":
                print("Run expired.")
                break
            else:            
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread_narrator.id,
                    run_id=run.id,
                )
                time.sleep(5)  
                # if counter % 10 == 0:
                #     # print('Waiting for assistant. Status:', run.status)
                #     counter += 1
                #     time.sleep(5)  
                
            
        
        messages_narrator = self.client.beta.threads.messages.list(
            thread_id=self.thread_narrator.id
        )
        chat_history_narrator = []
        for thread_message in messages_narrator.data:
            for content_item in thread_message.content:
                role = thread_message.role
                id = thread_message.assistant_id
                item = content_item.text.value
                chat_history_narrator.append({'content': item})

        return chat_history_narrator

    def get_inventory_snapshot(self):
        query = '''
        SELECT * FROM CHARACTER_INVENTORY_DETAILS;
        '''
        return self.__run_query(query)

    # connect to db without erasing
    # used for continuous web app
    def __connect_to_existing_db(self, db_name):
        try: 
            db = sqlite3.connect(db_name) 
            print("Database lldm.db connected.") 
        except Exception as e: 
            print("Database lldm.db not connected.")
            print(repr(e))
        
        return db

    # used to create fresh db
    def __create_db_from_file(self, excel_filename, db_name):
        try: 
            db = sqlite3.connect(db_name) 
            print("Database lldm.db formed.") 
        except: 
            print("Database lldm.db not formed.")

        # erase current db contents
        cursor = db.cursor()
        query = '''
        PRAGMA writable_schema = 1;
        DELETE FROM sqlite_master;
        PRAGMA writable_schema = 0;
        VACUUM;
        PRAGMA integrity_check;
        '''
        cursor.executescript(query)

        # create db from excel spreadsheet
        dfs = pd.read_excel(excel_filename, sheet_name=None)
        for table, df in dfs.items():
            try:
                print(table.upper().replace(' ','_').strip())
                df.columns = [x.replace(' ','_') for x in df.columns.values]
                df.to_sql(table.upper().replace(' ','_').strip(), db)
            except:
                continue

        # modify columns
        query = '''
        CREATE TABLE IF NOT EXISTS CAMPAIGN (
            Campaign_ID INTEGER NOT NULL,
            Setting TEXT NOT NULL,
            Start_Time TEXT NOT NULL,
            Current_Turns INTEGER NOT NULL DEFAULT 0
        );

        ALTER TABLE CHARACTER_SHEET
        RENAME COLUMN "index" TO Character_ID;

        ALTER TABLE CHARACTER_SHEET
        ADD COLUMN Campaign_ID INTEGER;

        ALTER TABLE INVENTORY
        RENAME COLUMN "index" TO Item_ID;

        ALTER TABLE WORLD_ITEMS
        RENAME COLUMN "index" TO Item_ID;

        ALTER TABLE SETTINGS
        RENAME COLUMN "index" TO Setting_ID;

        ALTER TABLE NPCS
        RENAME COLUMN "index" TO NPC_ID;

        ALTER TABLE TREASURES
        RENAME COLUMN "index" TO Treasure_ID;

        ALTER TABLE MONSTERS
        RENAME COLUMN "index" TO Monster_ID;

        ALTER TABLE PLOT
        RENAME COLUMN "index" TO Plot_ID;

        ALTER TABLE PLOT
        ADD COLUMN Campaign_ID INTEGER;

        ALTER TABLE LOGS
        RENAME COLUMN "index" TO Log_ID;

        ALTER TABLE LOGS
        ADD COLUMN Campaign_ID INTEGER;

        ALTER TABLE LOGS
        ADD COLUMN Character_ID INTEGER;

        CREATE TABLE IF NOT EXISTS CHARACTER_INVENTORY (
            Campaign_ID INTEGER NOT NULL,
            Character_ID INTEGER NOT NULL,
            Item_ID INTEGER NOT NULL,
            Total_Quantity FLOAT DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS CHARACTER_INVENTORY_HISTORY (
            Campaign_ID INTEGER NOT NULL,
            Character_ID INTEGER NOT NULL,
            Item_ID INTEGER NOT NULL,
            Quantity FLOAT DEFAULT 0,
            Modify_Time DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE VIEW IF NOT EXISTS CHARACTER_INVENTORY_DETAILS 
        AS
        SELECT
            a.Campaign_ID, a.Character_ID, a.Item_ID, a.Total_Quantity,
            b.Weapon_Name, b.Weapon_Description
        FROM CHARACTER_INVENTORY a
        JOIN WORLD_ITEMS b ON a.Item_ID = b.Item_ID;

        CREATE VIEW IF NOT EXISTS CHARACTER_INVENTORY_HISTORY_DETAILS 
        AS
        SELECT
            a.Campaign_ID, a.Character_ID, a.Item_ID, a.Quantity, a.Modify_Time,
            b.Weapon_Name, b.Weapon_Description
        FROM CHARACTER_INVENTORY_HISTORY a
        JOIN WORLD_ITEMS b ON a.Item_ID = b.Item_ID;
        '''
        cursor.executescript(query)
        db.commit()
        return db
        

    def __run_query(self, query):
        try:
            df = pd.read_sql_query(query, self.db)
            return df
        # not a select statement
        except TypeError:
            cursor = self.db.cursor()
            cursor.execute(query)
            return  
        
    def ___validate_item(self, item_name):
        query = f'''
        SELECT * FROM WORLD_ITEMS WHERE UPPER(Weapon_Name) LIKE "{item_name.upper()}%" 
        '''
        tmp = self.__run_query(query)
        if not tmp.empty:
            return tmp['Item_ID'].iloc[0]
        return None

    # update table if item validated, otherwise error message
    # for now, use temporary campaign and character id
    def __get_obtained_item(self, item_name, quantity, campaign_id=0, character_id=0):
        item_id = self.__validate_item(item_name)
        print(item_id, quantity)
        if item_id is not None:
            # TODO: error handling
            cursor = self.db.cursor()

            # overall character inventory tracker update
            query = f'''
            UPDATE CHARACTER_INVENTORY SET Total_Quantity = Total_Quantity + {quantity}
            WHERE Item_ID = {item_id} AND Campaign_ID = {campaign_id} AND Character_ID = {character_id}
            '''
            cursor.execute(query)

            if cursor.rowcount == 0:
                query = f'''
                INSERT INTO CHARACTER_INVENTORY (Campaign_ID, Character_ID, Item_ID, Total_Quantity) VALUES ({campaign_id}, {character_id}, {item_id}, {quantity})
                '''
                cursor.execute(query)

            # inventory history update
            query = f'''
            INSERT INTO CHARACTER_INVENTORY_HISTORY (Campaign_ID, Character_ID, Item_ID, Quantity) VALUES ({campaign_id}, {character_id}, {item_id}, {quantity})
            '''
            cursor.execute(query)

            return json.dumps({'message':'The item(s) were successfully obtained. Please continue the story.'})
        else:
            return json.dumps({'message':'Item does not exist. Please prompt user to specify further or provide another action.'})

    # check if item queried is in INVENTORY table and character has more than discard amount
    # might need a third error condition if item exists, user has item, but has less than discard amount
    def __validate_item_discard(self, item_name, quantity, campaign_id, character_id):
        query = f'''
        SELECT * FROM WORLD_ITEMS WHERE UPPER(Weapon_Name) LIKE "{item_name.upper()}%" 
        '''
        tmp = self.__run_query(query)
        if not tmp.empty: # item exists in world
            item_id = tmp['Item_ID'].iloc[0]
            # validate if character has item
            query = f'''
            SELECT * FROM CHARACTER_INVENTORY 
            WHERE Campaign_ID = {campaign_id} AND Character_ID = {character_id} AND Item_ID = {item_id} AND Total_Quantity >= {quantity}
            '''
            # there should theoretically only be one row of the item for each character with the quantity as different values
            # need to validate and put checks in place
            tmp = self.run_query(query)
            if not tmp.empty:
                return item_id
            raise self.ItemNotPossessedException("Character does not have the item in their inventory.")
        raise self.ItemNotFoundException("Item does not exist in this campaign.")

    # update table if item validated, otherwise error message
    # for now, use temporary campaign and character id
    # first update with item subtraction, then remove all entries with <=0 values
    def __get_discarded_item(self, item_name, quantity, campaign_id=0, character_id=0):
        try:
            item_id = self.__validate_item_discard(item_name, quantity, campaign_id, character_id)
            
            cursor = self.db.cursor()

            # overall inventory tracker update
            query = f'''
            UPDATE CHARACTER_INVENTORY SET Total_Quantity = Total_Quantity - {quantity}
            WHERE Item_ID = {item_id} AND Campaign_ID = {campaign_id} AND Character_ID = {character_id};
            '''
            cursor.execute(query)

            # housekeeping query, remove rows with invalid quantites (<= 0 items)
            query = 'DELETE FROM CHARACTER_INVENTORY WHERE Total_Quantity <= 0'
            cursor.execute(query)

            # inventory history tracker update
            # use negative quantity value to indicate 
            query = f'''
            INSERT INTO CHARACTER_INVENTORY_HISTORY (Campaign_ID, Character_ID, Item_ID, Quantity) VALUES ({campaign_id}, {character_id}, {item_id}, {-quantity})
            '''

            return json.dumps({'message':'The item(s) were successfully discarded. Please continue the story.'})
        except self.ItemNotPossessedException as e:
            return json.dumps({'message':"Item is not in character's possession. Please prompt user to specify further or provide another action."})
        except self.ItemNotFoundException as e:
            return json.dumps({'message':"Item does not exist. Please prompt user to specify further or provide another action."})


    def __get_item_info(self, sql_query, campaign_id=0, character_id=0):
        self.__run_query('PRAGMA QUERY_ONLY = ON;')
        try:
            
            # at some point in life, will figure out how to remove existing ID matching clauses before adding these
            # but for now this will do
            where = sqlglot.condition(f'Campaign_ID={campaign_id}').and_(f'Character_ID={character_id}')
            sql_query = sqlglot.parse_one(sql_query).where(where).sql()
            # print(sql_query)

            df_result = self.__run_query(sql_query)
            result = json.dumps(df_result.to_dict())
            # print(result)

            self.__run_query('PRAGMA QUERY_ONLY = OFF;')
            return json.dumps({'message':f"The result of the user's request in JSON format is {result}. Please use this to answer the user's question or honor the user's request."})
        except Exception as e:
            self.__run_query('PRAGMA QUERY_ONLY = OFF;')
            return json.dumps({'message':"Something went wrong, please prompt the user for another action"})
        

# Main function, testing purposes
if __name__ == '__main__':
    excel_db_filename = 'DnD.xlsx'
    db_name = "lldm.db"
    with open('api_keys.yaml', 'r') as f:
        api_keys = yaml.safe_load(f)

    OPENAI_API_KEY = api_keys['openai-key']

    lldm_assistant = LLDM_Assistant(OPENAI_API_KEY, db_name, excel_db_filename=excel_db_filename)

    tmp = lldm_assistant.narrator_chat("I pick up the Shadow Lance of Storm.")

    print('\n\nInitial query:',tmp[1]['content'].strip())
    print('\n\nResponse:',tmp[0]['content'])

    print(lldm_assistant.get_inventory_snapshot())

    tmp = lldm_assistant.narrator_chat("I pick up the Forgotten Sword of Flame.")

    print('\n\nInitial query:',tmp[1]['content'].strip())
    print('\n\nResponse:',tmp[0]['content'])

    print(lldm_assistant.get_inventory_snapshot())

    tmp = lldm_assistant.narrator_chat("How many weapons do I have?")

    print('\n\nInitial query:',tmp[1]['content'].strip())
    print('\n\nResponse:',tmp[0]['content'])