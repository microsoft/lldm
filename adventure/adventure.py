import os
import requests
import json
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def get_api_key():
    # Set the key vault name and secret name
    key_vault_name = "aoaikeys"
    secret_name = "AOAIKey"

    # Create the Key Vault URL
    key_vault_url = f"https://{key_vault_name}.vault.azure.net/"

    # Authenticate to Azure and get the secret
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    return client.get_secret(secret_name)


ENDPOINT = "https://dasommer-oai-ncus.openai.azure.com/openai/deployments/gpt4o/chat/completions?api-version=2024-02-15-preview"
api_key = ''

# Define the game schema (JSON Schema).  This defines the structured state of the game.
game_state = {
    "type": "object",
    "properties": {
        "health": {
            "type": "integer"
        },
        "gold": {
            "type": "integer"
        },
        "inventory": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "location": {
            "type": "string"
        },
        "exits": {
            "type": "object",
            "properties": {
                "north": {
                    "type": "string"
                },
                "south": {
                    "type": "string"
                },
                "east": {
                    "type": "string"
                },
                "west": {
                    "type": "string"
                }
            },
            "required": ["north", "south", "east", "west"],
            "additionalProperties": False
        }
    },
    "required": ["health", "gold", "inventory", "location", "exits"],
    "additionalProperties": False
}

# Schema for state changes
state_change = {
    "type": "object",
    "properties": {
        "add_gold": {
            "type": "integer"
        },
        "add_inventory": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "remove_inventory": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "set_location": {
            "type": "string"
        }
    },
    "required": ["add_gold", "add_inventory", "remove_inventory", "set_location"],
    "additionalProperties": False
}

game_schema = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string"
        },
        "game_state": game_state,
        "state_change": state_change
    },
    "required": ["response", "game_state", "state_change"],
    "additionalProperties": False
}

def make_structured_request(system_prompt: str, prompt: str, max_tokens: int, conversation_context: list = [], temperature: float=0.7, top_p: float=0.95) -> dict:
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key,
    }

    # Payload for the request
    payload = {
        "messages": [
            {
            "role": "system",
            "content": [
                {
                "type": "text",
                "text": system_prompt
                }
            ]
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "game_response",
                "schema": game_schema,
                "strict": True
            }
        },
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens
    }

    for context_entry in conversation_context:
        payload['messages'].append({
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': context_entry[0]
                }
            ]
        })
        payload['messages'].append({
            'role': 'assistant',
            'content': [
                {
                    'type': 'text',
                    'text': context_entry[1]
                }
            ]
        })
    payload['messages'].append({
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": prompt
            }
        ]
    })

    # Send request
    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        if response.status_code == 400:
            print(f"Error 400: Bad Request - {response.text}")
        response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
    except requests.RequestException as e:
        raise SystemExit(f"Failed to make the request. Error: {e}")

    # Handle the response as needed (e.g., print or process)
    return response.json()['choices'][0]


# Apply the defined state change to the game state
def apply_state_change(state: dict, change: dict):
    state['gold'] += change['add_gold']
    new_inventory = []
    for item in state['inventory']:
        if item not in change['remove_inventory']:
            new_inventory.append(item)
    for item in change['add_inventory']:
        new_inventory.append(item)
    state['inventory'] = new_inventory
    if change['set_location']:
        state['location'] = change['set_location']


game_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
The user is a player in the game.  When the user types a request you are to return a text response explaining what happened and describing
where the player ends up.  You are to stay in character as the DM and not reveal any hidden information about the game world.
The player may move around by going in one of the four cardinal directions or by specifying a visible location.
The player may interact with objects and characters, enter combat, pick up and manipulate items, check their inventory, and check their health.
The player may ask basic questions about the game but you must only reveal what they know or can see.

Also update the following game state as needed.
Health is an integer value from 0 (death) to 10 (full health)
Gold is an integer that represents the number of gold pieces the player carries.  Do not let the player spend more gold then they have!
Inventory is a list of items that the player carries.  When the player picks up an item add it to the inventory.  When a player uses up an item or drop it then remove it from the inventory.
Do not change the inventory without notifying the player in your response.
Location is the current location of the player
Direction specifiers like North, South, Up, etc specify the locations the player may reach by moving in a direction

After the user's turn, give a text response explaining what happened output the new game state, and describe how the game state changed.
'''

game_state = {
    "health": 10,
    "gold": 20,
    "inventory": [
        "Wooden sword"
    ],
    "location": "Outside the town of Eldoria",
    "exits": {
        "north": "Dark Forest",
        "west": "Town Square",
        "south": "Bakery",
        "east": "Dark Forest"
    }
}


context = []


def turn(command: str) -> str:
    global game_state
    global context
    result = make_structured_request(game_rules + json.dumps(game_state, indent=4), command, 5000, context)
    content = result['message']['content']
    structured_content = json.loads(content)
    response = structured_content['response']
    new_state = structured_content['game_state']
    state_change = structured_content['state_change']
    context.append((command, response))
    apply_state_change(game_state, state_change)
    print(response)
    print(state_change)
    print(game_state)


def main():
    global api_key
    api_key = get_api_key().value

    turn('begin the game')
    while True:
        command = input('>')
        turn(command)

if __name__=="__main__":
    main()
