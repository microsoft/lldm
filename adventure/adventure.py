import random
import requests
import json
import d20
import argparse
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient


def get_api_key():
    # Set the key vault name and secret name
    key_vault_name = "aoaikeys"
    secret_name = "AOAIKey"
    #secret_name = "AOAIKeySCUS"

    # Create the Key Vault URL
    key_vault_url = f"https://{key_vault_name}.vault.azure.net/"

    # Authenticate to Azure and get the secret
    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault_url, credential=credential)
    return client.get_secret(secret_name)


ENDPOINT = "https://dasommer-oai-ncus.openai.azure.com/openai/deployments/gpt4o/chat/completions?api-version=2024-02-15-preview"
#ENDPOINT = "https://dasommer-oai-cmk.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview"
api_key = ''

player = {}
player_text = ''

ability_schema = {
    "type": "object",
    "properties": {
        "Strength": {
            "type": "integer"
        },
        "Dexterity": {
            "type": "integer"
        },
        "Constitution": {
            "type": "integer"
        },
        "Intelligence": {
            "type": "integer"
        },
        "Wisdom": {
            "type": "integer"
        },
        "Charisma": {
            "type": "integer"
        }
    },
    "required": ["Strength", "Dexterity", "Constitution", "Intelligence", "Wisdom", "Charisma"],
    "additionalProperties": False
}

# Character schema.  This defines the player character and all abilities
character_schema = {
    "type": "object",
    "properties": {
        "Name": {
            "type": "string"
        },
        "Class": {
            "type": "string"
        },
        "Level": {
            "type": "integer"
        },
        "Health": {
            "type": "integer"
        },
        "Abilities": ability_schema,
        "Proficiencies": {
            "type": "object",
            "properties": {
                "Skills": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "Weapons": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "Saving Throws": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "required": ["Skills", "Weapons", "Saving Throws"],
            "additionalProperties": False
        }
    },
    "required": ["Name", "Class", "Level", "Health", "Abilities", "Proficiencies"],
    "additionalProperties": False
}

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
        },
        "monster_damage_dice": {
            "type": "string"
        }
    },
    "required": ["in_combat", "surprise", "monster_AC", "monster_attack_bonus", "monster_health", "monster_dexterity", "monster_damage_dice"],
    "additionalProperties": False
}

monster_schema = {
    "type": "object",
    "properties": {
        "identifier": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "abilities": ability_schema,
        "AC": {
            "type": "integer"
        },
        "health": {
            "type": "integer"
        },
        "status": {
            "type": "string"
        }
    },
    "required": ["identifier", "description", "abilities", "AC", "health", "status"],
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
        "location": {
            "type": "string"
        },
        "time_of_day": {
            "type": "string"
        },
        "date": {
            "type": "string"
        },
        "monsters": {
            "type": "array",
            "items": monster_schema
        },
        "allies": {
            "type": "array",
            "items": character_schema
        }
    },
    "required": ["health", "gold", "inventory", "location", "time_of_day", "date", "monsters", "allies"],
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
        "action_type": {
            "type": "string"
        },
        "how_to_resolve": {
            "type": "string"
        },
        "advantage": {
            "type": "boolean"
        },
        "disadvantage": {
            "type": "boolean"
        },
        "dice_to_roll": {
            "type": "string"
        },
        "number_to_beat": {
            "type": "integer"
        },
        "result_if_successful": {
            "type": "string"
        },
        "result_if_failed": {
            "type": "string"
        }
    },
    "required": ["action_type", "how_to_resolve", "advantage", "disadvantage", "dice_to_roll", "number_to_beat", "result_if_successful", "result_if_failed"],
    "additionalProperties": False
}

round_schema = {
    "type": "object",
    "properties": {
        "actions": {
            "type": "array",
            "items": action_schema
        }
    },
    "required": ["actions"],
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
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens
    }

    if schema:
        payload['response_format'] = {
            "type": "json_schema",
            "json_schema": {
                "name": "game_response",
                "schema": schema,
                "strict": True
            }
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
        print(json.dumps(payload, indent=4))
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
The player may not spend more gold then they have.  If the player attempts to offer more gold than they have while bargaining, their offer will be rejected.
After the user's turn, give a text response explaining in detail what happened.
'''

state_change_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
The user is a player in the game.
Examine the given action description and determine how the game state has changed, generating the new game state in JSON.  Only include the JSON response.
Game State includes the following:
Health is an integer value representing the player's hit points, according to D&D 5th Edition.
Gold is an integer that represents the number of gold pieces the player carries.  Do not let the player spend more gold then they have!
Inventory is a list of items that the player carries.  When the player picks up an item add it to the inventory.  When a player uses up an item or drop it then remove it from the inventory.
Time of Day tracks the current time of day, in HH:MM format using 24-hour time.  Actions take time and the time of day should be updated accordingly.
Date tracks the current month and day and should be in a form like "July 1".  This is used to determine sunset and sunrise times as well as to determine seasons.
If any monsters are present in the room, they should each be listed.
Each monster should have an identifier which can be used to differentiate them from other monsters also present, typically constructed by adding an adjective to the monster type.
For example "Fierce Goblin" or "Sneaky Lizard".  Monsters should also have Health, a Description, AC, ability scores, and a status indicator.
The status indicator determines if the monster has some unusual status that might affect how it behaves in combat.
If any allies are traveling with the player and can help the player in combat, they should also be listed.
Allies have statistics very similar to those of a player character, and each ally has a name.
'''

action_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
This game uses D&D 5th Edition rules.
The player is about to execute their turn and there may be other characters and monsters present who will act as well.
Using the supplied characer sheet, game state, and the rules of the game, determine all the actions that will occur during this turn, outputting everything in JSON and only JSON.
The first action will always be based on the command entered by the player.
This will be followed by actions from any monsters and allies present.
Finally any environmental actions will occur including sprung traps.
For each action, first determine if a die roll is necessary.
If a die roll is necessary, describe what rules
to use and how to determine whether this action will succeed or fail using the die roll, expressed as the dice to roll (in a form like "3d20") and a number to beat.
If a die roll is not necessary, leave dice_to_roll blank (empty string)
Set advantage if the die roll is to be made with Advantage
Set disadvantage if the die roll is to be made with Disadvantage
Also generate two descriptions: one that details what will happen if the action succeeds and another that details what will happen
if the action fails.  The descriptions should be in third-person, from the perspective of the Dungeon Master, and they should be in future tense.
These descriptions may optinoally include die rolls for damage or similar effect.
Examples of descriptions:
The player's longsword will strike the Goblin for 1d8 points of damage
The player will attempt to pick the lock but will fail
The Orc will miss the player on the next round
The player's attempt to search for treasure will trigger a poison needle trap
'''


death_rules = '''
The user is playing a fantasy role-playing game set in a typical medieval sword-and-sorcery RPG setting and you are the Dungeon Master.
The player has just died.  Display an appropriate game over message and summarize the player's achievements.
'''

character_rules = '''
What follows is a description of a character in a fantasy role-playing game using D&D 5th Edition rules.
Generate the character's statistics using a structured JSON format.
'''

game_state = {
    "health": 20,
    "gold": 20,
    "inventory": [
        "Short sword"
        "Leather armor",
        "Simple shield"
    ],
    "location": "Outside the Dragon's lair",
    "exits": {
        "north": "Dragon's lair",
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

def read_player_file(player_file: str):
    global player
    global player_text

    file_content = None
    try:
        with open(player_file, 'r') as file:
            file_content = file.read()
    except FileNotFoundError:
        print(f"The player file at {player_file} was not found.")
        exit(0)
    
    player_response = make_structured_request(character_rules, file_content, None, character_schema, 2000, [])
    player = json.loads(player_response['message']['content'])
    player_text = file_content

def read_scenario_file(scenario_file: str):
    global context
    global game_state

    file_content = None
    try:
        with open(scenario_file, 'r') as file:
            file_content = file.read()
    except FileNotFoundError:
        print(f"The scenario file at {scenario_file} was not found.")
        exit(0)
    
    # Make an LLM call to determine the initial game state from the text in the scenario file
    initial_state_response = make_structured_request(state_change_rules + '\n' + json.dumps(player, indent=4), file_content + '\n' + player_text, None, game_state_schema, 5000, [])
    #initial_state_response = make_structured_request(state_change_rules + '\n' + json.dumps(player, indent=4), file_content + '\n' + player_text, None, None, 5000, [])
    game_state = json.loads(initial_state_response['message']['content'])
    context.append(('Game World', file_content))
    context.append(('Player', player_text))


def compute_action_response(command:str, debug: bool) -> str:
    global game_state
    global context

    # First determine what sort of checks (if any) need to be made on the coming action
    action_response = make_structured_request(action_rules + json.dumps(player, indent=4) + json.dumps(game_state, indent=4), command, None, action_schema, 5000, context)
    action = json.loads(action_response['message']['content'])
    success_message = ''

    # Handle attack rolls specially, treating DC as the monster armor class.
    if action['skill'] == 'Attack Roll':
        die_roll = random.randint(1, 20)
        damage_roll = d20.roll(game_state['damage_dice']).total
        modifier = game_state['attack_bonus']
        if die_roll == 1:
            success_message = f'Make sure the upcoming player attack fails catastrophically'
            damage_roll = 0
        elif die_roll == 20:
            success_message = f'Make sure the upcoming player attack is a resounding success, doing {damage_roll} damage'
        elif die_roll + modifier >= action['DC']:
            success_message = f'Make sure the upcoming player attack succeeds, doing {damage_roll} damage'
        else:
            success_message = f'Make sure the upcoming player attack fails'
            damage_roll = 0
        monster_death = False
        if game_state['combat']['monster_health'] - damage_roll <= 0:
            monster_death = True
        if monster_death:
            success_message += ' and killing the monsters'

        # Now let the monsters attack.  (TODO: support dexterity bonus and swapping order due to initiative)
        if not game_state['combat']['surprise'] and not monster_death:
            die_roll = random.randint(1, 20)
            damage_roll = d20.roll(game_state['combat']['monster_damage_dice']).total
            modifier = game_state['combat']['monster_attack_bonus']
            if die_roll + modifier >= game_state['AC']:
                monster_message = f'Make sure the monsters attack succeeds, doing {damage_roll} damage'
            else:
                monster_message = f'Make sure the monsters attack fails'
                damage_roll = 0
            if damage_roll >= game_state['health']:
                death = True
            else:
                death = False
            if death:
                monster_message += ' and killing the player'
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

    if success_message:
        success_messsage += '\nIf this action resulted in the player health dropping to 0 or lower, make sure the player gets killed.'
    
    if debug:
        print(action)
        print(success_message)
    return success_message


# Roll dice, taking into account advantage and disadvantage 
def roll_dice(dice_to_roll: str, advantage: bool, disadvantage: bool) -> int:
    result = d20.roll(dice_to_roll).total
    if advantage:
        result2 = d20.roll(dice_to_roll).total
        if result2 > result:
            result = result2
    if disadvantage:
        result2 = d20.roll(dice_to_roll).total
        if result2 < result:
            result = result2
    return result

# Determine whether the next action will succeeed or fail, using the LLM to do most of the work
def llm_action_response(command: str, debug: bool) -> str:
    # Determine what die roll to make
    result = make_structured_request(action_rules + json.dumps(player, indent=4) + json.dumps(game_state, indent=4), command, None, round_schema, 5000, context)
    actions = json.loads(result['message']['content'])
    if debug:
        print(json.dumps(actions, indent=4))

    # Perform the die roll and see if we beat the target
    message = ''
    for action in actions['actions']:
        if action['dice_to_roll']:
            roll = roll_dice(action['dice_to_roll'], action['advantage'], action['disadvantage'])
            if roll >= action['number_to_beat']:
                message += action['result_if_successful'] + "\n"
            else:
                message += action['result_if_failed'] + "\n"
    return message


def turn(command: str, debug: bool) -> str:
    global game_state
    global context

    # Determine success or failure of all actions on the upcoming turn
    success_message = llm_action_response(command, debug)

    # Perform the action
    if debug:
        print(success_message)
    result = make_structured_request(game_rules + json.dumps(player, indent=4) + json.dumps(game_state, indent=4), command, success_message, None, 5000, context)
    response = result['message']['content']
    print(response)
    new_state_response = make_structured_request(state_change_rules + json.dumps(game_state, indent=4), response, None, game_state_schema, 2000, [])
    new_state = json.loads(new_state_response['message']['content'])
    context.append((command, response))
    game_state = new_state
    if debug:
        print(json.dumps(game_state, indent=4))
    if game_state['health'] <= 0:
        death_response = make_structured_request(death_rules + json.dumps(game_state, indent=4), '', None, None, 2000, context)
        print(death_response['message']['content'])
        exit(0)


def main():
    # Retrieve API Key from Keyvault
    global api_key
    api_key = get_api_key().value

    # Create the argument parser
    parser = argparse.ArgumentParser(description="Game World Setup")

    # Add arguments
    parser.add_argument('--scenario', type=str, required=True,
                        help='Path to the scenario file describing the world for the game.')
    parser.add_argument('--player', type=str, required=True,
                        help='Path to the player file describing attributes of the player.')
    parser.add_argument('--debug', type=bool, default=False, nargs='?',
                        const=True, help='Enable or disable debug mode (default: False).')

    # Parse arguments
    args = parser.parse_args()

    # Access the arguments
    scenario_file = args.scenario
    player_file = args.player
    debug_mode = args.debug

    read_player_file(player_file)
    if debug_mode:
        print(json.dumps(player, indent=4))
    read_scenario_file(scenario_file)
    if debug_mode:
        print(json.dumps(game_state, indent=4))

    turn('begin the game', debug_mode)
    while True:
        command = input('>')
        turn(command, debug_mode)

if __name__=="__main__":
    main()
