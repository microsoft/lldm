import random
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

# Combat schema.  Includes all information needed to manage combat
combat_schema = {
    "type": "object",
    "properties": {
        "in_combat": {
            "type": "boolean"
        },
        "surprise": {
            "type": "boolean"
        },
        "monster_AC": {
            "type": "integer"
        },
        "monster_attack_bonus": {
            "type": "integer"
        },
        "monster_health": {
            "type": "integer"
        },
        "monster_dexterity": {
            "type": "integer"
        }
    },
    "required": ["in_combat", "surprise", "monster_AC", "monster_attack_bonus", "monster_health", "monster_dexterity"],
    "additionalProperties": False
}

# Define the game schema (JSON Schema).  This defines the structured state of the game.
game_state_schema = {
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
        "AC": {
            "type": "integer"
        },
        "attack_bonus": {
            "type": "integer"
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
        },
        "combat": combat_schema
    },
    "required": ["health", "gold", "AC", "attack_bonus", "inventory", "location", "exits", "combat"],
    "additionalProperties": False
}

game_schema = {
    "type": "object",
    "properties": {
        "response": {
            "type": "string"
        },
        "game_state": game_state_schema,
    },
    "required": ["response", "game_state"],
    "additionalProperties": False
}

action_schema = {
    "type": "object",
    "properties": {
        "DC": {
            "type": "integer"
        },
        "skill": {
            "type": "string"
        },
        "ability": {
            "type": "string"
        },
        "why_needed": {
            "type": "string"
        },
        "how_much_needed": {
            "type": "integer"
        },
        "repeats_previous_action": {
            "type": "boolean"
        },
        "previous_action_result": {
            "type": "string"
        }
    },
    "required": ["DC", "skill", "ability", "why_needed", "how_much_needed", "repeats_previous_action", "previous_action_result"],
    "additionalProperties": False
}

def make_structured_request(system_prompt: str, user_prompt: str, second_system_prompt: str, schema: dict, max_tokens: int, conversation_context: list = [], temperature: float=0.7, top_p: float=0.95) -> dict:
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
                "schema": schema,
                "strict": True
            }
        },
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens
    }

    # Add conversation context
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

    # Add a second system prompt if provided
    if second_system_prompt:
        payload['messages'].append({
            'role': 'system',
            'content': [
                {
                    'type': 'text',
                    'text': second_system_prompt
                }
            ]
        })

    # Finally the user's prompt
    payload['messages'].append({
        "role": "user",
        "content": [
            {
            "type": "text",
            "text": user_prompt
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
After the user's turn, give a text response explaining in detail what happened.
'''

state_change_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
The user is a player in the game.
Examine the given action description and determine how the game state has changed, generating the new game state.
Game State includes the following:
Health is an integer value from 0 (death) to 10 (full health)
Gold is an integer that represents the number of gold pieces the player carries.  Do not let the player spend more gold then they have!
Inventory is a list of items that the player carries.  When the player picks up an item add it to the inventory.  When a player uses up an item or drop it then remove it from the inventory.
AC is the player's armor class, based on their best equipped armor and following D&D 5th Edition rules.
Attack Bonus is the bonus modifier of the player's best equipped weapon following D&D 5th Edition rules.
Combat provides information about whether or not the player is in combat and the state of the combat if one is in progress.  It includes:
in_combat should be True if the player is engaged in active combat or there are monsters close enough to attack.
surprise should be True if the monsters are unaware of the player's presence, or False if the player is out in the open or the monsters have been alerted.
monster_AC is the overall averaged Armor Class of the monsters, following D&D 5th Edition rules.
monster_attack_bonus is the overall monster attack modifier, following D&D 5th Edition rules and taking into account the general level of the monsters.
monster_health represents the health of the monsters, on a scale of 0 (death) to 10 (full health).
monster_dexterity represents the monster dexterity ability score from D&D 5th Edition, on a scale of 3 (lowest) through 18 (highest).  This includes how fast the monsters can move and react.
Do not change the inventory without notifying the player in your response.
Location is the current location of the player
Direction specifiers like North, South, Up, etc specify the locations the player may reach by moving in a direction
'''

action_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
When the user types a requrest you are to determine what type of action it is, determine the skill that should be checked when executing the action,
the ability that skill is based on, and compute a Difficulty Class, which is a numerical score indicating the task's difficulty.
Also describe why this skill is needed for this particular action and give a rating for how much the skill is needed, on a scale of 1 (barely needed) to 5 (essential).

Skills, Ability, and Difficulty Class should be computed following the rules of D&D 5th Edition.  If the action is a combat Attack Roll then the Difficulty Class should be set to the
averaged Armor Class of the monsters the player faces.
'''

game_state = {
    "health": 10,
    "gold": 20,
    "inventory": [
        "Longsword",
        "Chainmail",
        "Sturdy shield"
    ],
    "location": "Outside the Goblin camp",
    "exits": {
        "north": "Goblin Camp",
        "west": "Dark Forest",
        "south": "Dark Forest",
        "east": "Dark Forest"
    }
}


character = {
    "Strength": (16,3),
    "Dexterity": (14,2),
    "Constitution": (15,2),
    "Intelligence": (9,-1),
    "Wisdom": (11,0),
    "Charisma": (13,1),
    "skills": {
        "Athletics": 5,
        "Acrobatics": 4,
        "Sleight of Hand": 2,
        "Stealth": 2,
        "Arcana": -1,
        "History": -1,
        "Investigation": -1,
        "Nature": -1,
        "Religion": -1,
        "Animal Handling": 0,
        "Insight": 0,
        "Medicine": 0,
        "Perception": 2,
        "Survival": 0,
        "Deception": 1,
        "Intimidation": 3,
        "Performance": 1,
        "Persuasion": 3
    }
}


context = []


def turn(command: str) -> str:
    global game_state
    global context

    # First determine what sort of checks (if any) need to be made on the coming action
    action_response = make_structured_request(action_rules + json.dumps(game_state, indent=4), command, None, action_schema, 5000, context)
    action = json.loads(action_response['message']['content'])
    success_message = ''

    # Handle attack rolls specially, treating DC as the monster armor class.
    if action['skill'] == 'Attack Roll':
        die_roll = random.randint(1, 20)
        modifier = game_state['attack_bonus']
        if die_roll == 1:
            success_message = f'Make sure the upcoming player attack fails catastrophically'
        elif die_roll == 20:
            success_message = f'Make sure the upcoming player attack is a resounding success'
        elif die_roll + modifier >= action['DC']:
            success_message = f'Make sure the upcoming player attack succeeds'
        else:
            success_message = f'Make sure the upcoming player attack fails'

        # Now let the monsters attack.  (TODO: support dexterity bonus and swapping order due to initiative)
        if not game_state['combat']['surprise']:
            die_roll = random.randint(1, 20)
            modifier = game_state['combat']['monster_attack_bonus']
            if die_roll + modifier >= game_state['AC']:
                monster_message = f'If the monsters survive then make sure the monsters attack succeeds'
            else:
                monster_message = f'If the monsters survive then make sure the monsters attack fails'
            success_message += '\n' + monster_message

    # All other skills
    elif action['DC'] > 0 and action['how_much_needed'] > 2:
        die_roll = random.randint(1, 20)
        skill = action['skill']
        modifier = character['skills'].get(skill, 0)
        modifier_text = ''
        if action['how_much_needed'] == 3:
            modifier_text = 'though it should only matter a bit'
        elif action['how_much_needed'] == 5:
            modifier_text = 'and it should matter a lot'
        if die_roll + modifier >= action['DC']:
            success_message = f'The upcoming action requires {skill} because {action["why_needed"]}.  Make sure it succeeds {modifier_text}'
        else:
            success_message = f'The upcoming action requires {skill} because {action["why_needed"]}.  Make sure it fails {modifier_text}.'
    print(action)
    print(success_message)

    # Perform the action
    result = make_structured_request(game_rules + json.dumps(game_state, indent=4), command, success_message, game_schema, 5000, context)
    content = result['message']['content']
    structured_content = json.loads(content)
    response = structured_content['response']
    new_state_response = make_structured_request(state_change_rules + json.dumps(game_state, indent=4), response, None, game_state_schema, 2000, [])
    new_state = json.loads(new_state_response['message']['content'])
    context.append((success_message + '\n' + command, response))
    game_state = new_state
    print(response)
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
